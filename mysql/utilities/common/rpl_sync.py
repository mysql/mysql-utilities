#
# Copyright (c) 2014, 2016, Oracle and/or its affiliates. All rights reserved.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301 USA
#

"""
This file contains features to check the data consistency in a replication
topology (i.e., between the master and its slaves, or only slaves), providing
synchronization features to perform the check over the (supposed) same data of
a system with replication active (running).
"""
import re
import sys

from multiprocessing.pool import ThreadPool

from mysql.utilities.command.dbcompare import diff_objects, get_common_objects
from mysql.utilities.common.database import Database
from mysql.utilities.common.gtid import (get_last_server_gtid,
                                         gtid_set_cardinality,
                                         gtid_set_union)
from mysql.utilities.common.messages import (ERROR_USER_WITHOUT_PRIVILEGES,
                                             ERROR_ANSI_QUOTES_MIX_SQL_MODE)
from mysql.utilities.common.pattern_matching import convertSQL_LIKE2REGEXP
from mysql.utilities.common.sql_transform import quote_with_backticks
from mysql.utilities.common.topology import Topology
from mysql.utilities.common.user import User
from mysql.utilities.exception import UtilError

# Regular expression to handle the server version format.
_RE_VERSION_FORMAT = r'^(\d+\.\d+(\.\d+)*).*$'


class RPLSynchronizer(object):
    """Class to manage the features of the replication synchronization checker.

    The RPLSynchronizer class is used to manage synchronization check between
    servers of a replication topology, namely between the master and its
    slaves or only between slaves. It provides functions to determine the
    slaves missing transactions (i.e., missing GTIDs) and check data
    consistency.
    """

    def __init__(self, master_cnx_dic, slaves_cnx_dic_lst, options):
        """Constructor.

        options[in]       dictionary of options (e.g., discover, timeouts,
                          verbosity).
        """
        self._verbosity = options.get('verbosity')
        self._rpl_timeout = options.get('rpl_timeout')
        self._checksum_timeout = options.get('checksum_timeout')
        self._interval = options.get('interval')

        self._rpl_topology = Topology(master_cnx_dic, slaves_cnx_dic_lst,
                                      options)
        self._slaves = self._rpl_topology.get_slaves_dict()

        # Verify all the servers in the topology has or does not sql_mode set
        # to 'ANSI_QUOTES'.
        match_group, unmatch_group = \
            self._rpl_topology.get_servers_with_different_sql_mode(
                'ANSI_QUOTES'
            )
        # List and Raise an error if just some of the server has sql_mode set
        # to 'ANSI_QUOTES' instead of all or none.
        if match_group and unmatch_group:
            sql_mode = match_group[0].select_variable("SQL_MODE")
            if sql_mode == '':
                sql_mode = '""'
            sql_mode = sql_mode.replace(',', ', ')
            print("# The SQL mode in the following servers is set to "
                  "ANSI_QUOTES: {0}".format(sql_mode))
            for server in match_group:
                sql_mode = server.select_variable("SQL_MODE")
                if sql_mode == '':
                    sql_mode = '""'
                sql_mode = sql_mode.replace(',', ', ')
                print("# {0}:{1} sql_mode={2}"
                      "".format(server.host, server.port, sql_mode))
            print("# The SQL mode in the following servers is not set to "
                  "ANSI_QUOTES:")
            for server in unmatch_group:
                sql_mode = server.select_variable("SQL_MODE")
                if sql_mode == '':
                    sql_mode = '""'
                print("# {0}:{1} sql_mode={2}"
                      "".format(server.host, server.port, sql_mode))

            raise UtilError(ERROR_ANSI_QUOTES_MIX_SQL_MODE.format(
                utility='mysqlrplsync'
            ))

        # Set base server used as reference for comparisons.
        self._base_server = None
        self._base_server_key = None
        self._set_base_server()

        # Check user permissions to perform the consistency check.
        self._check_privileges()

        # Check usage of replication filters.
        self._master_rpl_filters = {}
        self._slaves_rpl_filters = {}
        self._check_rpl_filters()

    def _set_base_server(self):
        """Set the base server used for comparison in the internal state.

        Set the master if used or the first slave from the topology as the
        base server. The base server is the one used as a reference for
        comparison with the others. This method sets two instance variables:
        _base_server with the Server instance, and _base_server_key with the
        string identifying the server (format: 'host@port').

        Note: base server might need to be changed (set again) if it is
        removed from the topology for some reason (e.g. GTID disabled).
        """
        master = self._get_master()
        self._base_server = master if master \
            else self._rpl_topology.slaves[0]['instance']
        self._base_server_key = "{0}@{1}".format(self._base_server.host,
                                                 self._base_server.port)

    def _get_slave(self, slave_key):
        """Get the slave server instance for the specified key 'host@port'.

        This function retrieves the Server instance of for a slave from the
        internal state by specifying the key that uniquely identifies it,
        i.e. 'host@port'.

        slave_key[in]   String with the format 'host@port' that uniquely
                        identifies a server.

        Returns a Server instance of the slave with the specified key value
        (i.e., 'host@port').
        """
        slave_dict = self._slaves[slave_key]
        return slave_dict['instance']

    def _get_master(self):
        """Get the master server instance.

        This function retrieves the Server instance of the master (in the
        replication topology).

        Returns a Server instance of the master.
        """
        return self._rpl_topology.master

    def _check_privileges(self):
        """Check required privileges to perform the synchronization check.

        This method check if the used users for the master and slaves possess
        the required privileges to perform the synchronization check. More
        specifically, the following privileges are required:
            - on the master: SUPER or REPLICATION CLIENT, LOCK TABLES and
                             SELECT;
            - on slaves: SUPER and SELECT.
        An exception is thrown if users doesn't have enough privileges.
        """
        if self._verbosity:
            print("# Checking users permission to perform consistency check.\n"
                  "#")

        # Check privileges for master.
        master_priv = [('SUPER', 'REPLICATION CLIENT'), ('LOCK TABLES',),
                       ('SELECT',)]
        master_priv_str = "SUPER or REPLICATION CLIENT, LOCK TABLES and SELECT"
        if self._get_master():
            server = self._get_master()
            user_obj = User(server, "{0}@{1}".format(server.user, server.host))
            for any_priv_tuple in master_priv:
                has_privilege = any(
                    [user_obj.has_privilege('*', '*', priv)
                     for priv in any_priv_tuple]
                )
                if not has_privilege:
                    raise UtilError(ERROR_USER_WITHOUT_PRIVILEGES.format(
                        user=server.user, host=server.host, port=server.port,
                        operation='perform the synchronization check',
                        req_privileges=master_priv_str
                    ))

        # Check privileges for slaves.
        slave_priv = [('SUPER',), ('SELECT',)]
        slave_priv_str = "SUPER and SELECT"
        for slave_key in self._slaves:
            server = self._get_slave(slave_key)
            user_obj = User(server, "{0}@{1}".format(server.user, server.host))
            for any_priv_tuple in slave_priv:
                has_privilege = any(
                    [user_obj.has_privilege('*', '*', priv)
                     for priv in any_priv_tuple]
                )
                if not has_privilege:
                    raise UtilError(
                        "User '{0}' on '{1}@{2}' does not have sufficient "
                        "privileges to perform the synchronization check "
                        "(required: {3}).".format(server.user, server.host,
                                                  server.port, slave_priv_str)
                    )

    def _check_rpl_filters(self):
        """Check usage of replication filters.

        Check the usage of replication filtering option on the master (if
        defined) and slaves, and set the internal state with the found options
        (to check later).
        """
        # Get binlog filtering option for the master.
        if self._get_master():
            m_filters = self._get_master().get_binlog_exceptions()
            if m_filters:
                # Set filtering option for master.
                self._master_rpl_filters['binlog_do_db'] = \
                    m_filters[0][1].split(',') if m_filters[0][1] else None
                self._master_rpl_filters['binlog_ignore_db'] = \
                    m_filters[0][2].split(',') if m_filters[0][2] else None

        # Get replication filtering options for each slave.
        for slave_key in self._slaves:
            slave = self._get_slave(slave_key)
            s_filters = slave.get_slave_rpl_filters()
            if s_filters:
                # Handle known server issues with some replication filters,
                # leading to inconsistent GTID sets. Sync not supported for
                # server with those issues.
                issues = [(0, 'replicate_do_db'), (1, 'replicate_ignore_db'),
                          (4, 'replicate_wild_do_table')]
                for index, rpl_opt in issues:
                    if s_filters[index]:
                        raise UtilError(
                            "Use of {0} option is not supported. There is a "
                            "known issue with the use this replication filter "
                            "and GTID for some server versions. Issue "
                            "detected for '{1}'.".format(rpl_opt, slave_key))
                # Set map (dictionary) with the slave filtering options.
                filters_map = {
                    'replicate_do_db':
                    s_filters[0].split(',') if s_filters[0] else None,
                    'replicate_ignore_db':
                    s_filters[1].split(',') if s_filters[1] else None,
                    'replicate_do_table':
                    s_filters[2].split(',') if s_filters[2] else None,
                    'replicate_ignore_table':
                    s_filters[3].split(',') if s_filters[3] else None,
                }
                # Handle wild-*-table filters differently to create
                # corresponding regexp.
                if s_filters[4]:
                    wild_list = s_filters[4].split(',')
                    filters_map['replicate_wild_do_table'] = wild_list
                    # Create auxiliary list with compiled regexp to match.
                    regexp_list = []
                    for wild in wild_list:
                        regexp = re.compile(convertSQL_LIKE2REGEXP(wild))
                        regexp_list.append(regexp)
                    filters_map['regexp_do_table'] = regexp_list
                else:
                    filters_map['replicate_wild_do_table'] = None
                    filters_map['regexp_do_table'] = None
                if s_filters[5]:
                    wild_list = s_filters[5].split(',')
                    filters_map['replicate_wild_ignore_table'] = wild_list
                    # Create auxiliary list with compiled regexp to match.
                    regexp_list = []
                    for wild in wild_list:
                        regexp = re.compile(convertSQL_LIKE2REGEXP(wild))
                        regexp_list.append(regexp)
                    filters_map['regexp_ignore_table'] = regexp_list
                else:
                    filters_map['replicate_wild_ignore_table'] = None
                    filters_map['regexp_ignore_table'] = None
                # Set filtering options for the slave.
                self._slaves_rpl_filters[slave_key] = filters_map

        # Print warning if filters are found.
        if self._master_rpl_filters or self._slaves_rpl_filters:
            print("# WARNING: Replication filters found on checked "
                  "servers. This can lead data consistency issues "
                  "depending on how statements are evaluated.\n"
                  "# More information: "
                  "http://dev.mysql.com/doc/en/replication-rules.html")
            if self._verbosity:
                # Print filter options in verbose mode.
                if self._master_rpl_filters:
                    print("# Master '{0}@{1}':".format(
                        self._get_master().host, self._get_master().port
                    ))
                    for rpl_filter in self._master_rpl_filters:
                        if self._master_rpl_filters[rpl_filter]:
                            print("#   - {0}: {1}".format(
                                rpl_filter,
                                ', '.join(
                                    self._master_rpl_filters[rpl_filter]
                                )
                            ))
                if self._slaves_rpl_filters:
                    for slave_key in self._slaves_rpl_filters:
                        print("# Slave '{0}':".format(slave_key))
                        filters_map = self._slaves_rpl_filters[slave_key]
                        for rpl_filter in filters_map:
                            if (rpl_filter.startswith('replicate') and
                                    filters_map[rpl_filter]):
                                print("#   - {0}: {1}".format(
                                    rpl_filter,
                                    ', '.join(filters_map[rpl_filter])
                                ))

    def _is_rpl_filtered(self, db_name, tbl_name=None, slave=None):
        """ Check if the given object is to be filtered by replication.

        This method checks if the given database or table name is
        supposed to be filtered by replication (i.e., not replicated),
        according to the defined replication filters for the master or
        the specified slave.

        db_name[in]     Name of the database to check (not backtick quoted) or
                        associated to the table to check..
        tbl_name[in]    Name of the table to check (not backtick quoted).
                        Table level filtering rules are only checked if this
                        value is not None. By default None, meaning that only
                        the database level rules are checked.
        slave[in]       Identification of the slave in the format 'host@port'
                        to check, determining which filtering rules will be
                        checked. If None only the master filtering rules are
                        checked, otherwise the rule of the specified slaves
                        are used. By default: None.

        Returns a boolean value indicating if the given database or table is
        supposed to be filtered by the replication  or not. More precisely,
        if True then updates associated to the object are (supposedly) not
        replicated, otherwise they are replicated.
        """
        def match_regexp(name, regex_list):
            """ Check if 'name' matches one of the regex in the given list.
            """
            for regex in regex_list:
                if regex.match(name):
                    return True
            return False

        # Determine object to check and set full qualified name.
        is_db = tbl_name is None
        obj_name = db_name if is_db else '{0}.{1}'.format(db_name, tbl_name)

        # Match replication filter for Master.
        if not slave and is_db and self._master_rpl_filters:
            if self._master_rpl_filters['binlog_do_db']:
                if obj_name in self._master_rpl_filters['binlog_do_db']:
                    return False
                else:
                    return True
            elif self._master_rpl_filters['binlog_ignore_db']:
                if obj_name in self._master_rpl_filters['binlog_ignore_db']:
                    return True

        # Match replication filters for the specified slave.
        if slave and slave in self._slaves_rpl_filters:
            rpl_filter = self._slaves_rpl_filters[slave]
            if is_db:
                if rpl_filter['replicate_do_db']:
                    if obj_name in rpl_filter['replicate_do_db']:
                        return False
                    else:
                        return True
                elif (rpl_filter['replicate_ignore_db'] and
                      obj_name in rpl_filter['replicate_ignore_db']):
                    return True
            else:
                if (rpl_filter['replicate_do_table'] and
                        obj_name in rpl_filter['replicate_do_table']):
                    return False
                if (rpl_filter['replicate_ignore_table'] and
                        obj_name in rpl_filter['replicate_ignore_table']):
                    return True
                if (rpl_filter['replicate_wild_do_table'] and
                        match_regexp(obj_name,
                                     rpl_filter['regexp_do_table'])):
                    return False
                if (rpl_filter['replicate_wild_ignore_table'] and
                        match_regexp(obj_name,
                                     rpl_filter['regexp_ignore_table'])):
                    return True
                if (rpl_filter['replicate_do_table'] or
                        rpl_filter['replicate_wild_do_table']):
                    return True

        # Do not filter replication for object (if no filter rule matched).
        return False

    def _apply_for_all_slaves(self, slaves, function, args=(), kwargs=None,
                              multithreading=False):
        """Apply specified function to all given slaves.

        This function allow the execution (concurrently or not) of the
        specified function with the given arguments on all the specified
        slaves.

        slaves[in]          List of slaves to apply the function. It is assumed
                            that the list is composed by strings with the
                            format 'host@port', identifying each slave.
        function[in]        Name of the function (string) to apply on all
                            slaves.
        args[in]            Tuple with all the function arguments (except
                            keyword arguments).
        kwargs[in]          Dictionary with all the function keyword arguments.
        multithreading[in]  Boolean value indicating if the function will be
                            applied concurrently on all slaves. By default
                            False, no concurrency.

        Return a list of tuples composed by two elements: a string identifying
        the slave ('host@port') and the result of the execution of the target
        function for the corresponding slave.
        """
        if kwargs is None:
            kwargs = {}
        if multithreading:
            # Create a pool of threads to execute the method for each slave.
            pool = ThreadPool(processes=len(slaves))
            thread_res_lst = []
            for slave_key in slaves:
                slave = self._get_slave(slave_key)
                thread_res = pool.apply_async(getattr(slave, function), args,
                                              kwargs)
                thread_res_lst.append((slave_key, thread_res))
            pool.close()
            # Wait for all threads to finish here to avoid RuntimeErrors when
            # waiting for the result of a thread that is already dead.
            pool.join()
            # Get the result from each slave and return the results.
            res = []
            for slave_key, thread_res in thread_res_lst:
                res.append((slave_key, thread_res.get()))
            return res
        else:
            res = []
            for slave_key in slaves:
                slave = self._get_slave(slave_key)
                slave_res = getattr(slave, function)(*args, **kwargs)
                res.append((slave_key, slave_res))
            return res

    def check_server_versions(self):
        """Check server versions.

        Check all server versions and report version differences.
        """
        srv_versions = {}
        # Get the server version of the master if used.
        master = self._get_master()
        if master:
            master_version = master.get_version()
            match = re.match(_RE_VERSION_FORMAT, master_version.strip())
            if match:
                # Add .0 as release version if not provided.
                if not match.group(2):
                    master_version = "{0}.0".format(match.group(1))
                else:
                    master_version = match.group(1)
            master_id = '{0}@{1}'.format(master.host, master.port)
            # Store the master version.
            srv_versions[master_version] = [master_id]

        # Get the server version for all slaves.
        for slave_key in self._slaves:
            slave = self._get_slave(slave_key)
            version = slave.get_version()
            match = re.match(_RE_VERSION_FORMAT, version.strip())
            if match:
                # Add .0 as release version if not provided.
                if not match.group(2):
                    version = "{0}.0".format(match.group(1))
                else:
                    version = match.group(1)
            # Store the slave version.
            if version in srv_versions:
                srv_versions[version].append(slave_key)
            else:
                srv_versions[version] = [slave_key]

        # Check the servers versions and issue a warning if different.
        if len(srv_versions) > 1:
            print("# WARNING: Servers using different versions:")
            for version in srv_versions:
                servers_str = ",".join(srv_versions[version])
                print("# - {0} for {1}.".format(version, servers_str))
            print("#")

    def check_gtid_sync(self):
        """Check GTIDs synchronization.

        Perform several GTID checks (enabled and errant transactions). If the
        master is available (was specified) then it also checks if GTIDs are
        in sync between master and its slaves and report the amount of
        transaction (i.e., GTIDs) behind the master for each slave.

        GTID differences might be an indicator of the existence of data
        consistency issues.

        Note: The master may not be specified, its use is not mandatory.
        """
        # Check if GTIDs are enabled on the topology.
        if self._get_master():  # Use of Master is not mandatory.
            # GTIDs must be enabled on the master.
            if self._get_master().supports_gtid().upper() != 'ON':
                raise UtilError(
                    "Master must support GTIDs and have GTID_MODE=ON."
                )
        # Skip slaves without GTID enabled and warn user.
        reset_base_srv = False
        for slave_key, slave_dict in self._slaves.items():
            slave = slave_dict['instance']
            support_gtid = slave.supports_gtid().upper()
            if support_gtid != 'ON':
                reason = "GTID_MODE=OFF" if support_gtid == 'OFF' \
                    else "not support GTIDs"
                print("# WARNING: Slave '{0}' will be skipped - "
                      "{1}.".format(slave_key, reason))
                print("#")
                del self._slaves[slave_key]
                self._rpl_topology.remove_slave(slave_dict)
                if slave_key == self._base_server_key:
                    reset_base_srv = True
        # At least on slave must have GTIDs enabled.
        if len(self._slaves) == 0:
            raise UtilError("No slaves found with GTID support and "
                            "GTID_MODE=ON.")
        # Reset base server if needed (it must have GTID_MODE=ON).
        if reset_base_srv:
            self._set_base_server()

        # Check the set of executed GTIDs and report differences, only if the
        # master is specified.
        if self._get_master():
            master_gtids = self._get_master().get_gtid_executed()
            slaves_gtids_data = \
                self._rpl_topology.slaves_gtid_subtract_executed(
                    master_gtids, multithreading=True
                )
            print("#\n# GTID differences between Master and Slaves:")
            for host, port, gtids_missing in slaves_gtids_data:
                slave_key = '{0}@{1}'.format(host, port)
                gtid_size = gtid_set_cardinality(gtids_missing)
                if gtid_size:
                    plural = 's' if gtid_size > 1 else ''
                    print("# - Slave '{0}' is {1} transaction{2} behind "
                          "Master.".format(slave_key, gtid_size, plural))
                    if self._verbosity:
                        print("#       Missing GTIDs: "
                              "{0}".format(gtids_missing))
                else:
                    print("# - Slave '{0}' is up-to-date.".format(slave_key))

        print("#")

    @staticmethod
    def _exist_in_obj_list(obj_name, obj_type, obj_list):
        """Check if object (name and type) exists in the given list.

        This function checks if the database object for the specified name and
        type exists in the specified list of database objects.

        obj_name[in]    Name of the object to check.
        obj_type[in]    Type of the object to check.
        obj_list[in]    List of objects to check. It is assumed that the list
                        has the format of the ones returned by the function
                        mysql.utilities.command.dbcompare.get_common_objects().
                        More precisely with the format:
                        [(obj_type1, (obj_name1,))..(obj_typeN, (obj_nameN,))]

        Returns a boolean value indicating if object with the specified name
        and type exists in the specified list of objects.
        """
        for obj_row in obj_list:
            if obj_row[0] == obj_type and obj_row[1][0] == obj_name:
                return True
        return False

    def _split_active_slaves(self, slaves):
        """Get the list of slaves with replication running and not.

        This method separates the list of given slaves into active (with the
        IO and SQL thread running) and non active slaves (with one of the
        threads stopped).

        slaves[in]      List of target slaves to separate.

        Returns a tuple with two elements, first with the list of active slaves
        and the second with the list of not active ones.
        """
        # Get slaves status.
        slaves_state = self._apply_for_all_slaves(slaves, 'get_slaves_errors',
                                                  multithreading=True)

        # Store IO and SQL thread status.
        active_slaves = []
        not_active_slaves = []
        for slave_key, state in slaves_state:
            # Locally store IO and SQL threads status.
            io_running = state[3].upper() == 'YES'
            self._slaves[slave_key]['IO_Running'] = io_running
            sql_running = state[4].upper() == 'YES'
            self._slaves[slave_key]['SQL_Running'] = sql_running
            if io_running and sql_running:
                active_slaves.append(slave_key)
            else:
                not_active_slaves.append(slave_key)
                print("#   WARNING: Slave not active '{0}' - "
                      "Sync skipped.".format(slave_key))
                if self._verbosity:
                    # Print warning if slave is stopped due to an error.
                    if not io_running and state[2]:
                        print("#    - IO thread stopped: ERROR {0} - "
                              "{1}".format(state[1], state[2]))
                    if not sql_running and state[6]:
                        print("#    - SQL thread stopped: ERROR {0} - "
                              "{1}".format(state[5], state[6]))

        # Return separated list of active and non active replication slaves.
        return active_slaves, not_active_slaves

    def _compute_sync_point(self, active_slaves=None, master_uuid=None):
        """Compute the GTID synchronization point.

        This method computes the GTID synchronization point based based on the
        GTID_EXECUTED set. If a master is available for synchronization the
        last GTID from the GTID_EXECUTED set is used as sync point  If no
        master is available the union of the GTID_EXECUTED sets among all
        active slaves is used as the sync point.

        active_slaves[in]   List of active slaves to consider. Only required
                            if the master is not available. It is assumed
                            that the list is composed by strings with the
                            format 'host@port', identifying each slave.
        master_uuid[in]     UUID of the master server used to compute its last
                            GTID (sync point). If not provided it is
                            determined, but can lead to issues for servers
                            >= 5.7.6 if specific tables are locked previously.

        Return a GTID set representing to synchronization point (to wait for
        slaves to catch up and stop).
        """
        if self._get_master():
            gtid_set = self._get_master().get_gtid_executed()
            master_uuid = master_uuid if master_uuid \
                else self._get_master().get_server_uuid()
            return get_last_server_gtid(gtid_set, master_uuid)
        else:
            # Get GTID_EXECUTED on all slaves.
            all_gtid_executed = self._apply_for_all_slaves(
                active_slaves, 'get_gtid_executed', multithreading=True
            )

            # Compute the union of all GTID sets for each UUID among slaves.
            gtid_sets_by_uuid = {}
            for _, gtid_executed in all_gtid_executed:
                gtids_list = gtid_executed.split("\n")
                for gtid in gtids_list:
                    gtid_set = gtid.rstrip(', ')
                    uuid = gtid_set.split(':')[0]
                    if uuid not in gtid_sets_by_uuid:
                        gtid_sets_by_uuid[uuid] = gtid_set
                    else:
                        union_set = gtid_set_union(gtid_sets_by_uuid[uuid],
                                                   gtid_set)
                        gtid_sets_by_uuid[uuid] = union_set

            # Return union of all know executed GTID.
            return ",".join(gtid_sets_by_uuid.itervalues())

    def _sync_slaves(self, slaves, gtid):
        """Set synchronization point (specified GTID set) for the given slaves.

        The method set the synchronization point for the given slaves by
        (concurrently) stopping and immediately executing START SLAVE UNTIL
        on all given slaves in order to stop upon reaching the given GTID set
        (i.e., committing all corresponding transactions for the given GTID
        sync point).

        slaves[in]      List of target slaves to synchronize (i.e., instruct
                        to stop upon reaching the synchronization point).
        gtid[in]        GTID set used as the synchronization point.
        """
        # Make running slaves stop until sync point (GTID) is reached.
        if self._verbosity:
            print("#   Setting data synchronization point for slaves.")
        # STOP slave (only SQL thread).
        self._apply_for_all_slaves(slaves, 'stop_sql_thread',
                                   multithreading=True)
        # START slave UNTIL sync point is reached.
        # Note: Only the SQL thread is stopped when the condition is reached.
        until_ops = {'until_gtid_set': gtid, 'sql_after_gtid': True,
                     'only_sql_thread': True}
        self._apply_for_all_slaves(slaves, 'start', (), until_ops,
                                   multithreading=True)

    def _checksum_and_resume_rpl(self, not_sync_slaves, sync_slave, table):
        """Checksum table and resume replication on slaves.

        This method computes (concurrently) the table checksum of the given
        slaves lists (those synced and not synced). For the list of not synced
        slaves the table checksum is immediately computed. For the list of
        synced slaves, first it waits for them to catch up and the sync point
        and only then compute the table checksum and resume replication.

        not_sync_slaves[in] List of not synced slaves.
        sync_slave[in]      List of (previously) synced slaves.
        table[in]           Target table to compute the checksum.

        Returns a list of tuples, each tuple containing the identification of
        the server and the corresponding checksum result.
        """
        if self._verbosity:
            print("#   Compute checksum on slaves (wait to catch up and resume"
                  " replication).")
            sys.stdout.flush()
        not_sync_checksum = []
        if not_sync_slaves:
            not_sync_checksum = self._apply_for_all_slaves(
                not_sync_slaves, 'checksum_table', (table,),
                {'exec_timeout': self._checksum_timeout},
                multithreading=True
            )
        sync_checksum = []
        if sync_slave:
            sync_checksum = self._apply_for_all_slaves(
                sync_slave, 'wait_checksum_and_start', (table,),
                {'wait_timeout': self._rpl_timeout,
                 'wait_interval': self._interval,
                 'checksum_timeout': self._checksum_timeout},
                multithreading=True
            )
        return not_sync_checksum + sync_checksum

    def _check_table_data_sync(self, table, slaves):
        """Check table data synchronization for specified slaves.

        This method check the data consistency for the specified table between
        the base server (master or slave) and the specified salves. This
        operation requires the definition of a "synchronization point" in order
        to ensure that the "supposed" same data is compared between servers.
        This coordination process is based on GTIDs (checking that all data
        until a given GTID has been processed on the slaves). A different
        algorithm is used to set the "synchronization point" depending if the
        master is used or not. The data consistency is checked relying on the
        CHECKSUM TABLE query.

        If an error occur during this process, any locked table must be
        unlocked and both master and slaves should resume their previous
        activity.

        Important note: this method assumes that the table exists on the base
        server and all specified slaves, therefore checking the existence of
        the table as well as other integrity checks (server versions, GTID
        definitions, etc.) need to be performed outside the scope of this
        method.

        table[in]       Qualified name of the table to check (quoted with
                        backticks).
        slaves[in]      List of slaves to check. Each element of the list must
                        be a string with the format 'host@port'.

        Returns the number of data consistency found.
        """
        success = False
        checksum_issues = 0
        # If no master used then add base server (slave) to slaves to sync.
        if not self._get_master():
            slaves = slaves + [self._base_server_key]

        # Separate active from non active slaves.
        active_slaves, not_active_slaves = self._split_active_slaves(slaves)

        if self._get_master():
            # Get uuid of the master server
            master_uuid = self._get_master().get_server_uuid()

            # Lock the table on the master to get GTID synchronization point
            # and perform the table checksum.
            try:
                self._get_master().exec_query(
                    "LOCK TABLES {0} READ".format(table)
                )

                last_exec_gtid = self._compute_sync_point(
                    master_uuid=master_uuid
                )
                if self._verbosity > 2:
                    print("#   Sync point GTID: {0}".format(last_exec_gtid))

                # Immediately instruct active slaves to stop on sync point.
                if active_slaves:
                    self._sync_slaves(active_slaves, last_exec_gtid)

                # Perform table checksum on master.
                base_server_checksum = self._get_master().checksum_table(
                    table, self._checksum_timeout
                )
                if base_server_checksum[0]:
                    success = True  # Successful checksum for base server.
                    if self._verbosity > 2:
                        print("#   Checksum on base server (Master): "
                              "{0}".format(base_server_checksum[0][1]))
                else:
                    print("#   [SKIP] {0} checksum on base server (Master) - "
                          "{1}".format(table, base_server_checksum[1]))
            finally:
                # Unlock table.
                self._get_master().exec_query("UNLOCK TABLES")
        elif active_slaves:
            # Perform sync without master, only based on active slave (if any).
            try:
                # Stop all active slaves to get the GTID synchronization point.
                self._apply_for_all_slaves(
                    active_slaves, 'stop_sql_thread', multithreading=True
                )

                sync_gtids = self._compute_sync_point(active_slaves)
                if self._verbosity > 2:
                    print("#   Sync point GTID: {0}".format(sync_gtids))

                # Instruct active slaves to stop on sync point.
                self._sync_slaves(active_slaves, sync_gtids)

            except UtilError:
                # Try to restart the slaves in case an error occurs.
                self._apply_for_all_slaves(
                    active_slaves, 'star_sql_thread', multithreading=True
                )

        # Compute checksum on all slaves and return to previous state.
        slaves_checksum = self._checksum_and_resume_rpl(not_active_slaves,
                                                        active_slaves, table)

        # Check if checksum for base server was successfully computed.
        if not self._get_master():
            for slave_key, checksum in slaves_checksum:
                if slave_key == self._base_server_key:
                    if checksum[0]:
                        success = True  # Successful checksum for base server.
                        base_server_checksum = checksum
                        slaves_checksum.remove((slave_key, checksum))
                        if self._verbosity > 2:
                            print("#   Checksum on base server: "
                                  "{0}".format(base_server_checksum[0][1]))
                    else:
                        print("#   [SKIP] {0} checksum on base server - "
                              "{1}".format(table, checksum[1]))
                    break

        # Compare checksum and report results.
        if success and slaves_checksum:
            for slave_key, checksum_res in slaves_checksum:
                if checksum_res[0] is None:
                    print("#   [SKIP] {0} checksum for Slave '{1}' - "
                          "{2}.".format(table, slave_key, checksum_res[1]))
                else:
                    if self._verbosity > 2:
                        checksum_val = ': {0}'.format(checksum_res[0][1])
                    else:
                        checksum_val = ''
                    if checksum_res[0] != base_server_checksum[0]:
                        print("#   [DIFF] {0} checksum for server '{1}'"
                              "{2}.".format(table, slave_key, checksum_val))
                        checksum_issues += 1
                    else:
                        print("#   [OK] {0} checksum for server '{1}'"
                              "{2}.".format(table, slave_key, checksum_val))

        return checksum_issues

    def check_data_sync(self, options, data_to_include, data_to_exclude):
        """Check data synchronization.

        Check if the data (in all tables) is in sync between the checked
        servers (master and its slaves, or only slaves). It reports structure
        difference database/tables missing or with a different definition and
        data differences between a base server and the others.

        Note: A different algorithm is applied to perform the synchronization,
        depending if the master is specified (available) or not.

        options[in]         Dictionary of options.
        data_to_include[in] Dictionary of data (set of tables) by database to
                            check.
        data_to_exclude[in] Dictionary of data (set of tables) by database to
                            exclude from check.

        Returns the number of consistency issues found (comparing database
        definitions and data).
        """
        issues_count = 0

        # Skip all database objects, except tables.
        options['skip_views'] = True
        options['skip_triggers'] = True
        options['skip_procs'] = True
        options['skip_funcs'] = True
        options['skip_events'] = True
        options['skip_grants'] = True

        diff_options = {}
        diff_options.update(options)
        diff_options['quiet'] = True  # Do not print messages.
        diff_options['suppress_sql'] = True  # Do not print SQL statements.
        diff_options['skip_table_opts'] = True  # Ignore AUTO_INCREMENT diffs.

        # Check the server version requirement to support sync features.
        # Slave servers of version >= 5.6.14 are required due to a known issue
        # for START SLAVE UNTIL with the SQL_AFTER_GTIDS option. More info:
        # https://dev.mysql.com/doc/refman/5.6/en/start-slave.html
        for slave_key in self._slaves:
            if not self._get_slave(slave_key).check_version_compat(5, 6, 14):
                raise UtilError(
                    "Server '{0}' version must be 5.6.14 or greater. Sync is "
                    "not supported for versions prior to 5.6.14 due to a "
                    "known issue with START SLAVE UNTIL and the "
                    "SQL_AFTER_GTIDS option.".format(slave_key))

        print("# Checking data consistency.\n#")
        base_srv_type = 'Master' if self._get_master() else 'Slave'
        print("# Using {0} '{1}' as base server for comparison."
              "".format(base_srv_type, self._base_server_key))

        # Get all databases from the base server.
        db_rows = self._base_server.get_all_databases()
        base_server_dbs = set([row[0] for row in db_rows])

        # Process databases to include/exclude from check.
        db_to_include = set()
        if data_to_include:
            db_to_include = set([db for db in data_to_include])
            base_server_dbs = base_server_dbs & db_to_include
            not_exist_db = db_to_include - base_server_dbs
            if not_exist_db:
                plurals = ('s', '') if len(not_exist_db) > 1 else ('', 'es')
                print('# WARNING: specified database{0} to check do{1} not '
                      'exist on base server and will be skipped: '
                      '{2}.'.format(plurals[0], plurals[1],
                                    ", ".join(not_exist_db)))
        db_to_exclude = set()
        if data_to_exclude:
            db_to_exclude = set(
                [db for db in data_to_exclude if not data_to_exclude[db]]
            )
            base_server_dbs = base_server_dbs - db_to_exclude

        # Check databases on slaves (except the base server).
        slaves_except_base = [key for key in self._slaves
                              if key != self._base_server_key]
        for slave_key in slaves_except_base:
            slave = self._get_slave(slave_key)
            db_rows = slave.get_all_databases()
            slave_dbs = set([row[0] for row in db_rows])
            # Process databases to include/exclude.
            if db_to_include:
                slave_dbs = slave_dbs & db_to_include
            if db_to_exclude:
                slave_dbs = slave_dbs - db_to_exclude
            # Add slave databases set to internal state.
            self._slaves[slave_key]['databases'] = slave_dbs
            # Report databases not on base server and filtered by replication.
            dbs_not_in_base_srv = slave_dbs - base_server_dbs
            filtered_dbs = set(
                [db for db in dbs_not_in_base_srv
                 if self._is_rpl_filtered(db, slave=self._base_server_key)]
            )
            dbs_not_in_base_srv -= filtered_dbs
            for db in filtered_dbs:
                print("# [SKIP] Database '{0}' - filtered by replication "
                      "rule on base server.".format(db))
            if dbs_not_in_base_srv:
                issues_count += len(dbs_not_in_base_srv)
                plural = 's' if len(dbs_not_in_base_srv) > 1 else ''
                print("# [DIFF] Database{0} NOT on base server but found on "
                      "'{1}': {2}".format(plural, slave_key,
                                          ",".join(dbs_not_in_base_srv)))

        # Determine server to check base replication filtering options.
        filter_srv = None if self._get_master() else self._base_server_key

        # Check data consistency for each table on the base server.
        # pylint: disable=R0101
        for db_name in base_server_dbs:
            # Skip database if filtered by defined replication rules.
            if self._is_rpl_filtered(db_name, slave=filter_srv):
                print("# [SKIP] Database '{0}' check - filtered by "
                      "replication rule.".format(db_name))
                continue
            print("# Checking '{0}' database...".format(db_name))
            slaves_to_check = {}
            # Check if database exists on slaves (except the base server).
            for slave_key in slaves_except_base:
                # Skip database if filtered by defined replication rules.
                if self._is_rpl_filtered(db_name, slave=slave_key):
                    print("# [SKIP] Database '{0}' check for '{1}' - filtered "
                          "by replication rule.".format(db_name, slave_key))
                    continue
                if db_name in self._slaves[slave_key]['databases']:
                    # Store slave database instance and common objects.
                    slave_db = Database(self._get_slave(slave_key), db_name,
                                        options)
                    slave_db.init()
                    slave_dic = {'db': slave_db}
                    in_both, in_basesrv, not_in_basesrv = get_common_objects(
                        self._base_server, self._get_slave(slave_key),
                        db_name, db_name, False, options)
                    # Process tables to include/exclude from check (on slaves).
                    if (data_to_include and db_name in data_to_include and
                            data_to_include[db_name]):
                        in_both = [
                            obj_row for obj_row in in_both
                            if obj_row[1][0] in data_to_include[db_name]
                        ]
                        in_basesrv = [
                            obj_row for obj_row in in_basesrv
                            if obj_row[1][0] in data_to_include[db_name]
                        ]
                        not_in_basesrv = [
                            obj_row for obj_row in not_in_basesrv
                            if obj_row[1][0] in data_to_include[db_name]
                        ]
                    if (data_to_exclude and db_name in data_to_exclude and
                            data_to_exclude[db_name]):
                        in_both = [
                            obj_row for obj_row in in_both
                            if obj_row[1][0] not in data_to_exclude[db_name]
                        ]
                        in_basesrv = [
                            obj_row for obj_row in in_basesrv
                            if obj_row[1][0] not in data_to_exclude[db_name]
                        ]
                        not_in_basesrv = [
                            obj_row for obj_row in not_in_basesrv
                            if obj_row[1][0] not in data_to_exclude[db_name]
                        ]
                    slave_dic['in_both'] = in_both
                    slave_dic['in_basesrv'] = in_basesrv
                    slaves_to_check[slave_key] = slave_dic
                    # Report tables not on base server and filtered by
                    # replication.
                    tbls_not_in = set(
                        [obj_row[1][0] for obj_row in not_in_basesrv
                         if obj_row[0] == 'TABLE']
                    )
                    filtered_tbls = set(
                        [tbl for tbl in tbls_not_in if self._is_rpl_filtered(
                            db_name, tbl_name=tbl, slave=self._base_server_key
                        )]
                    )
                    tbls_not_in -= filtered_tbls
                    for tbl in filtered_tbls:
                        print("# [SKIP] Table '{0}' - filtered by replication "
                              "rule on base server.".format(tbl))
                    if tbls_not_in:
                        plural = 's' if len(tbls_not_in) > 1 else ''
                        print("#   [DIFF] Table{0} NOT on base server but "
                              "found on '{1}': "
                              "{2}".format(plural, slave_key,
                                           ", ".join(tbls_not_in)))
                        issues_count += len(tbls_not_in)
                else:
                    print("#   [DIFF] Database '{0}' NOT on server "
                          "'{1}'.".format(db_name, slave_key))
                    issues_count += 1
            # Only check database if at least one slave has it.
            if slaves_to_check:
                db = Database(self._base_server, db_name, options)
                db.init()
                for db_obj in db.get_next_object():
                    obj_type = db_obj[0]
                    obj_name = db_obj[1][0]
                    # Process tables to include/exclude from check (on base
                    # server).
                    if (data_to_include and db_name in data_to_include and
                            data_to_include[db_name] and
                            obj_name not in data_to_include[db_name]):
                        # Skip to the next object if not in data to include.
                        continue
                    if (data_to_exclude and db_name in data_to_exclude and
                            data_to_exclude[db_name] and
                            obj_name in data_to_exclude[db_name]):
                        # Skip to the next object if in data to exclude.
                        continue
                    checksum_task = []
                    # Check object data on all valid slaves.
                    for slave_key in slaves_to_check:
                        # Skip table if filtered by defined replication rules.
                        if (obj_type == 'TABLE' and
                                self._is_rpl_filtered(db_name, obj_name,
                                                      slave=slave_key)):
                            print("# [SKIP] Table '{0}' check for '{1}' - "
                                  "filtered by replication rule."
                                  "".format(obj_name, slave_key))
                            continue
                        slave_dic = slaves_to_check[slave_key]
                        # Check if object does not exist on Slave.
                        if self._exist_in_obj_list(obj_name, obj_type,
                                                   slave_dic['in_basesrv']):
                            print("#   [DIFF] {0} '{1}.{2}' NOT on server "
                                  "'{3}'.".format(obj_type.capitalize(),
                                                  db_name, obj_name,
                                                  slave_key))
                            issues_count += 1
                            continue

                        # Quote object name with backticks.
                        q_obj = '{0}.{1}'.format(
                            quote_with_backticks(db_name, db.sql_mode),
                            quote_with_backticks(obj_name, db.sql_mode)
                        )

                        # Check object definition.
                        def_diff = diff_objects(
                            self._base_server, self._get_slave(slave_key),
                            q_obj, q_obj, diff_options, obj_type
                        )
                        if def_diff:
                            print("#   [DIFF] {0} {1} definition is "
                                  "different on '{2}'."
                                  "".format(obj_type.capitalize(), q_obj,
                                            slave_key))
                            issues_count += 1
                            if self._verbosity:
                                for diff in def_diff[3:]:
                                    print("#       {0}".format(diff))
                            continue

                        # Add slave to table checksum task.
                        checksum_task.append(slave_key)

                    # Perform table checksum on valid slaves.
                    if checksum_task and obj_type == 'TABLE':
                        print("# - Checking '{0}' table data..."
                              "".format(obj_name))
                        num_issues = self._check_table_data_sync(q_obj,
                                                                 checksum_task)
                        issues_count += num_issues

        print("#\n#...done.\n#")
        str_issues_count = 'No' if issues_count == 0 else str(issues_count)
        plural = 's' if issues_count > 1 else ''
        print("# SUMMARY: {0} data consistency issue{1} found.\n"
              "#".format(str_issues_count, plural))
        return issues_count
