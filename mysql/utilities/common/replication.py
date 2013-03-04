#
# Copyright (c) 2010, 2013, Oracle and/or its affiliates. All rights reserved.
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
This module contains abstractions of MySQL replication functionality.
"""

import os
import time

from mysql.utilities.common.options import parse_user_password
from mysql.utilities.common.server import Server
from mysql.utilities.exception import UtilError, UtilRplWarn, UtilRplError

_MASTER_INFO_COL = [
    'Master_Log_File', 'Read_Master_Log_Pos', 'Master_Host', 'Master_User',
    'Master_Password', 'Master_Port', 'Connect_Retry', 'Master_SSL_Allowed',
    'Master_SSL_CA_File', 'Master_SSL_CA_Path', 'Master_SSL_Cert',
    'Master_SSL_Cipher', 'Master_SSL_Key', 'Master_SSL_Verify_Server_Cert',
    'Heartbeat', 'Bind', 'Ignored_server_ids', 'Uuid', 'Retry_count',
    'SSL_CRL', 'SSL_CRL_Path', 'Enabled_auto_position',
]

_SLAVE_IO_STATE, _SLAVE_MASTER_HOST, _SLAVE_MASTER_USER, _SLAVE_MASTER_PORT, \
    _SLAVE_MASTER_LOG_FILE, _SLAVE_MASTER_LOG_FILE_POS, _SLAVE_IO_RUNNING, \
    _SLAVE_SQL_RUNNING, _SLAVE_DO_DB, _SLAVE_IGNORE_DB, _SLAVE_DELAY, \
    _SLAVE_REMAINING_DELAY, _SLAVE_IO_ERRORNO, _SLAVE_IO_ERROR, \
    _SLAVE_SQL_ERRORNO, _SLAVE_SQL_ERROR, _RETRIEVED_GTID_SET, \
    _EXECUTED_GTID_SET = \
    0, 1, 2, 3, 5, 6, 10, 11, 12, 13, 32, 33, 34, 35, 36, 37, 51, 52

_PRINT_WIDTH = 75

_MASTER_DO_DB, _MASTER_IGNORE_DB = 2, 3

_RPL_USER_QUERY = """
    SELECT user, host, password = "" as has_password
    FROM mysql.user
    WHERE repl_slave_priv = 'Y'
"""

_WARNING = "# WARNING: %s"
_MASTER_BINLOG = "Server '%s' does not have binary logging turned on."
_NO_RPL_USER = "No --rpl-user specified and multiple users found with " + \
               "replication privileges."
_RPL_USER_PASS = "No --rpl-user specified and the user found with " + \
                 "replication privileges requires a password."

_GTID_EXECUTED = "SELECT @@GLOBAL.GTID_EXECUTED"
_GTID_WAIT = "SELECT WAIT_UNTIL_SQL_THREAD_AFTER_GTIDS('%s', %s)"

def _get_list(rows, cols):
    """Return a list of information in GRID format to stdout.

    rows[in]          rows of data
    cols[in]          column headings

    Returns list of strings
    """
    import StringIO
    from mysql.utilities.common.format import format_tabular_list

    ostream = StringIO.StringIO()
    format_tabular_list(ostream, cols, rows)
    return ostream.getvalue().splitlines()


def negotiate_rpl_connection(server, is_master=True, strict=True, options={}):
    """Determine replication connection

    This method attempts to determine if it is possible to build a CHANGE
    MASTER command based on the server passed. If it is possible, the method
    will return a CHANGE MASTER command. If there are errors and the strict
    option is turned on, it will throw errors if there is something missing.
    Otherwise, it will return the CHANGE MASTER command with warnings.

    If the server is a master, the following error checks will be performed.

      - if binary log is turned OFF, and strict = False, a warning message
        is added to the strings returned else an error is thrown

      - if the rpl_user option is missing, the method attempts to find a
        replication user. If more than one user is found or none are found, and
        strict = False, a warning message is added to the strings returned else
        an error is thrown

      - if a replication user is found but the user requires a password,
        the MASTER_USER and MASTER_PASSWORD options are commented out

    Note: the CHANGE MASTER command is formatted whereby each option is
          separated by a newline and indented two spaces

    Note: the make_change_master method does not support SSL connections

    server[in]        a Server class instance
    is_master[in]     if True, the server is acting as a master
                      Default = True
    strict[in]        if True, raise exception on errors
                      Default = True
    options[in]       replication options including rpl_user, quiet, multiline

    Returns list - strings containing the CHANGE MASTER command
    """

    rpl_mode = options.get("rpl_mode", "master")
    rpl_user = options.get("rpl_user", None)
    quiet = options.get("quiet", False)

    # Copy options and add connected server
    new_opts = options.copy()
    new_opts["conn_info"] = server

    master_values = {}
    change_master = []

    # If server is a master, perform error checking
    if is_master:
        master = Master(new_opts)
        master.connect()

        # Check master for binlog
        if not master.binlog_enabled():
            raise UtilError("Master must have binary logging turned on.")
        else:
            # Check rpl user
            if rpl_user is None and not quiet:
                # Try to find the replication user
                res = master.get_rpl_users()
                if len(res) > 1:
                    uname = ""
                    passwd = ""
                    # Throw error if strict but not for rpl_mode = both
                    if strict and not rpl_mode == 'both':
                        raise UtilRplError(_NO_RPL_USER)
                    else:
                        change_master.append(_WARNING % _NO_RPL_USER)
                else:
                    uname = res[0][0]
                    if res[0][2]:
                        # Throw error if strict but not for rpl_mode = both
                        if strict and not rpl_mode == 'both':
                            raise UtilRplError(_RPL_USER_PASS)
                        else:
                            change_master.append(_WARNING % _RPL_USER_PASS)
                    passwd = res[0][1]
            else:
                # Parse username and password (supports login-paths)
                uname, passwd = parse_user_password(rpl_user, options=options)
                if not passwd:
                    passwd = ''

                # Check replication user privileges
                errors = master.check_rpl_user(uname, master.host)
                if errors != []:
                    raise UtilError(errors[0])

            res = master.get_status()
            if not res:
               raise UtilError("Cannot retrieve master status.")

            # Need to get the master values for the make_change_master command
            master_values = {
                'Master_Host'          : master.host,
                'Master_Port'          : master.port,
                'Master_User'          : uname,
                'Master_Password'      : passwd,
                'Master_Log_File'      : res[0][0],
                'Read_Master_Log_Pos'  : res[0][1],
            }

    # Use slave class to get change master command
    slave = Slave(new_opts)
    slave.connect()
    cm_cmd = slave.make_change_master(False, master_values)

    if rpl_user is None and uname == "" and not quiet:
        cm_cmd = cm_cmd.replace("MASTER_PORT", "# MASTER_USER = '', "
                                "# MASTER_PASSWORD = '', MASTER_PORT")

    if options.get("multiline", False):
        cm_cmd = cm_cmd.replace(", ", ", \n  ") + ";"
        change_master.extend(cm_cmd.split("\n"))
    else:
        change_master.append(cm_cmd + ";")

    return change_master


class Replication(object):
    """
    The Replication class can be used to establish a replication connection
    between a master and a slave with the following utilities:

        - Create the replication user
        - Setup replication
        - Test prerequisites for replication
        - Conduct validation checks:
            - binlog
            - server ids
            - storage engine compatibility
            - innodb version compatibility
            - master binlog
            - lower case table name compatibility
            - slave connection to master
            - slave delay

    Replication prerequisite tests shall be constructed so that they return
    None if the check passes (no errors) or a list of strings containing the
    errors or warnings. They shall accept a dictionary of options set to
    options={}. This will allow for reduced code needed to call multiple tests.
    """

    def __init__(self, master, slave, options):
        """Constructor

        master[in]         Master Server object
        slave[in]          Slave Server object
        options[in]        Options for class
          verbose          print extra data during operations (optional)
                           default value = False
          master_log_file  master log file
                           default value = None
          master_log_pos   position in log file
                           default = -1 (no position specified)
          from_beginning   if True, start from beginning of logged events
                           default = False
        """
        self.verbosity = options.get("verbosity", 0)
        self.master_log_file = options.get("master_log_file", None)
        self.master_log_pos = options.get("master_log_pos", 0)
        self.from_beginning = options.get("from_beginning", False)
        self.master = master
        self.slave = slave
        self.replicating = False
        self.query_options = {
            'fetch' : False
        }


    def check_server_ids(self):
        """Check server ids on master and slave

        This method will check the server ids on the master and slave. It will
        raise exceptions for error conditions.

        Returns [] if compatible, list of errors if not compatible
        """
        master_server_id = self.master.get_server_id()
        slave_server_id = self.slave.get_server_id()
        if master_server_id == 0:
            raise UtilRplError("Master server_id is set to 0.")

        if slave_server_id == 0:
            raise UtilRplError("Slave server_id is set to 0.")

        # Check for server_id uniqueness
        if master_server_id == slave_server_id:
            raise UtilRplError("The slave's server_id is the same as the "
                                 "master.")

        return []


    def check_server_uuids(self):
        """Check UUIDs on master and slave

        This method will check the UUIDs on the master and slave. It will
        raise exceptions for error conditions.

        Returns [] if compatible or no UUIDs used, list of errors if not
        """
        master_uuid = self.master.get_uuid()
        slave_uuid = self.slave.get_uuid()

        # Check for both not supporting UUIDs.
        if master_uuid is None and slave_uuid is None:
            return []

        # Check for unbalanced servers - one with UUID, one without
        if master_uuid is None or slave_uuid is None:
            raise UtilRplError("%s does not support UUIDs." %
                               "Master" if master_uuid is None else "Slave")

        # Check for uuid uniqueness
        if master_uuid == slave_uuid:
            raise UtilRplError("The slave's UUID is the same as the "
                                 "master.")

        return []


    def check_innodb_compatibility(self, options):
        """Check InnoDB compatibility

        This method checks the master and slave to ensure they have compatible
        installations of InnoDB. It will print the InnoDB settings on the
        master and slave if quiet is not set. If pedantic is set, method
        will raise an error.

        options[in]   dictionary of options (verbose, pedantic)

        Returns [] if compatible, list of errors if not compatible
        """

        pedantic = options.get("pedantic", False)
        verbose = options.get("verbosity", 0) > 0

        errors = []

        master_innodb_stats = self.master.get_innodb_stats()
        slave_innodb_stats = self.slave.get_innodb_stats()

        if master_innodb_stats != slave_innodb_stats:
            if not pedantic:
                errors.append("WARNING: Innodb settings differ between master "
                              "and slave.")
            if verbose or pedantic:
                cols = ['type', 'plugin_version', 'plugin_type_version',
                        'have_innodb']
                rows = []
                rows.append(master_innodb_stats)
                errors.append("# Master's InnoDB Stats:")
                errors.extend(_get_list(rows, cols))
                rows = []
                rows.append(slave_innodb_stats)
                errors.append("# Slave's InnoDB Stats:")
                errors.extend(_get_list(rows, cols))
            if pedantic:
                for line in errors:
                    print line
                raise UtilRplError("Innodb settings differ between master "
                                     "and slave.")

        return errors


    def check_storage_engines(self, options):
        """Check compatibility of storage engines on master and slave

        This method checks that the master and slave have compatible storage
        engines. It will print the InnoDB settings on the master and slave if
        quiet is not set. If pedantic is set, method will raise an error.

        options[in]   dictionary of options (verbose, pedantic)

        Returns [] if compatible, list of errors if not compatible
        """

        pedantic = options.get("pedantic", False)
        verbose = options.get("verbosity", 0) > 0

        errors = []
        slave_engines = self.slave.get_storage_engines()
        results = self.master.check_storage_engines(slave_engines)
        if results[0] is not None or results[1] is not None:
            if not pedantic:
                errors.append("WARNING: The master and slave have differing "
                              "storage engine configurations!")
            if verbose or pedantic:
                cols = ['engine', 'support']
                if results[0] is not None:
                    errors.append("# Storage engine configuration on Master:")
                    errors.extend(_get_list(results[0], cols))
                if results[1] is not None:
                    errors.append("# Storage engine configuration on Slave:")
                    errors.extend(_get_list(results[1], cols))
            if pedantic:
                for line in errors:
                    print line
                raise UtilRplError("The master and slave have differing "
                                     "storage engine configurations!")

        return errors


    def check_master_binlog(self):
        """Check prerequisites for master for replication

        Returns [] if master ok, list of errors if binary logging turned off.
        """
        errors = []
        if not self.master.binlog_enabled():
            errors.append("Master must have binary logging turned on.")
        return errors


    def check_lctn(self):
        """Check lower_case_table_name setting

        Returns [] - no exceptions, list if exceptions found
        """
        errors = []
        slave_lctn = self.slave.get_lctn()
        master_lctn = self.master.get_lctn()
        if slave_lctn != master_lctn:
            return (master_lctn, slave_lctn)
        if slave_lctn == 1:
            msg = "WARNING: identifiers can have inconsistent case " + \
                  "when lower_case_table_names = 1 on the slave and " + \
                  "the master has a different value."
            errors.append(msg)

        return errors


    def get_binlog_exceptions(self):
        """Get any binary logging exceptions

        This method queries the master and slave status for the *-do-db and
        *-ignore-db settings. It returns the values of either of these for
        the master and slave.

        Returns [] - no exceptions, list if exceptions found
        """
        binlog_ex = []
        rows = []
        rows.extend(self.master.get_binlog_exceptions())
        rows.extend(self.slave.get_binlog_exceptions())
        if len(rows) > 0:
            cols = ['server', 'do_db', 'ignore_db']
            binlog_ex = _get_list(rows, cols)

        return binlog_ex


    def check_slave_connection(self):
        """Check to see if slave is connected to master

        This method will check the slave specified at instantiation to see if
        it is connected to the master specified. If the slave is connected
        to a different master, an error is returned. It will also raise an
        exception if the slave is stopped or if the server is not setup as a
        slave.

        Returns bool - True = slave connected to master
        """
        state = self.slave.get_io_running()
        if not state:
            raise UtilRplError("Slave is stopped.")
        if not self.slave.is_configured_for_master(self.master) or \
           state.upper() != "YES":
            return False
        return True


    def check_slave_delay(self):
        """Check to see if slave is behind master.

        This method checks slave_behind_master returning None if 0 or a
        message containing the value if non-zero. Also includes the slave's
        position as related to the master.

        Returns [] - no exceptions, list if exceptions found
        """
        m_log_file = None
        m_log_pos = 0
        errors = []
        res = self.master.get_status()
        if res != []:
            m_log_file = res[0][0]       # master's binlog file
            m_log_pos = res[0][1]        # master's binlog position
        else:
            raise UtilRplError("Cannot read master status.")
        delay_info = self.slave.get_delay()
        if delay_info is None:
            raise UtilRplError("The server specified as the slave is "
                                 "not configured as a replication slave.")


        state, sec_behind, delay_remaining, \
            read_log_file, read_log_pos = delay_info

        if not state:
            raise UtilRplError("Slave is stopped.")
        if delay_remaining is None: # if unknown, return the error
            errors.append("Cannot determine slave delay. Status: UNKNOWN.")
            return errors

        if sec_behind == 0:
            if m_log_file is not None and \
               (read_log_file != m_log_file or
                read_log_pos != m_log_pos):
                errors.append("Slave is behind master.")
                errors.append("Master binary log file = %s" % m_log_file)
                errors.append("Master binary log position = %s" % m_log_pos)
                errors.append("Slave is reading master binary log "
                              "file = %s" % read_log_file)
                errors.append("Slave is reading master binary log "
                              "position = %s" % read_log_pos)
            else:
                return errors
        else:
            errors.append("Slave is % seconds behind master." %
                          sec_behind)

        return errors


    def create_rpl_user(self, r_user, r_pass=None):
        """Create the replication user and grant privileges

        If the user exists, check privileges and add privileges as needed.
        Calls Master class method to execute.

        r_user[in]     user to create
        r_pass[in]     password for user to create (optional)

        Returns bool - True = success, False = errors
        """
        return self.master.create_rpl_user(self.slave.host, self.slave.port,
                                           r_user, r_pass, self.verbosity)


    def setup(self, rpl_user, num_tries):
        """Setup replication among a slave and master.

        Note: Must have connected to a master and slave before calling this
        method.

        rpl_user[in]       Replication user in form user:passwd
        num_tries[in]      Number of attempts to wait for slave synch

        Returns True if success, False if error
        """
        if self.master is None or self.slave is None:
            print "ERROR: Must connect to master and slave before " \
                  "calling replicate()"
            return False

        result = True

        # Parse user and password (support login-paths)
        r_user, r_pass = parse_user_password(rpl_user)

        # Check to see if rpl_user is present, else create her
        if not self.create_rpl_user(r_user, r_pass):
            return False

        # Read master log file information
        res = self.master.get_status()
        if not res:
            print "ERROR: Cannot retrieve master status."
            return False

        # If master log file, pos not specified, read master log file info
        read_master_info = False
        if self.master_log_file is None:
            res = self.master.get_status()
            if not res:
                print "ERROR: Cannot retrieve master status."
                return False

            read_master_info = True
            self.master_log_file = res[0][0]
            self.master_log_pos = res[0][1]
        else:
            # Check to make sure file is accessible and valid
            found = False
            res = self.master.get_binary_logs(self.query_options)
            for row in res:
                if row[0] == self.master_log_file:
                    found = True
                    break
            if not found:
                raise UtilError("Master binary log file not listed as a "
                                "valid binary log file on the master.")

        if self.master_log_file is None:
            raise UtilError("No master log file specified.")

        # Stop slave first
        res = self.slave.get_thread_status()
        if res is not None:
            if res[1] == "Yes" or res[2] == "Yes":
                res = self.slave.stop(self.query_options)

        # Connect slave to master
        if self.verbosity > 0:
            print "# Connecting slave to master..."
        master_values = {
            'Master_Host'          : self.master.host,
            'Master_Port'          : self.master.port,
            'Master_User'          : r_user,
            'Master_Password'      : r_pass,
            'Master_Log_File'      : self.master_log_file,
            'Read_Master_Log_Pos'  : self.master_log_pos,
        }
        change_master = self.slave.make_change_master(self.from_beginning,
                                                      master_values)
        res = self.slave.exec_query(change_master, self.query_options)
        if self.verbosity > 0:
            print "# %s" % change_master

        # Start slave
        if self.verbosity > 0:
            if not self.from_beginning:
                if read_master_info:
                    print "# Starting slave from master's last position..."
                else:
                    msg = "# Starting slave from master log file '%s'" % \
                          self.master_log_file
                    if self.master_log_pos >= 0:
                        msg += " using position %s" % self.master_log_pos
                    msg += "..."
                    print msg
            else:
                print "# Starting slave from the beginning..."
        res = self.slave.start(self.query_options)

        # Add commit because C/Py are auto_commit=0 by default
        self.slave.exec_query("COMMIT")

        # Check slave status
        i = 0
        while i < num_tries:
            time.sleep(1)
            res = self.slave.get_slaves_errors()
            status = res[0]
            sql_running = res[4]
            if self.verbosity > 0:
                io_errorno = res[1]
                io_error = res[2]
                io_running = res[3]
                sql_errorno = res[5]
                sql_error = res[6]
                print "# IO status: %s" % status
                print "# IO thread running: %s" % io_running
                # if io_errorno = 0 and error = '' -> no error
                if not io_errorno and not io_error:
                    print "# IO error: None"
                else:
                    print "# IO error: %s:%s" % (io_errorno, io_error)
                # if io_errorno = 0 and error = '' -> no error
                print "# SQL thread running: %s" % sql_running
                if not sql_errorno and not sql_error:
                    print "# SQL error: None"
                else:
                    print "# SQL error: %s:%s" % (io_errorno, io_error)
            if status == "Waiting for master to send event" and sql_running:
                break
            elif not sql_running:
                if self.verbosity > 0:
                    print "# Retry to start the slave SQL thread..."
                #SQL thread is not running, retry to start it
                res = self.slave.start_sql_thread(self.query_options)
            if self.verbosity > 0:
                print "# Waiting for slave to synchronize with master"
            i += 1
        if i == num_tries:
            print "ERROR: failed to synch slave with master."
            result = False

        if result is True:
            self.replicating = True

        return result


    def test(self, db, num_tries):
        """Test the replication setup.

        Requires a database name which is created on the master then
        verified it appears on the slave.

        db[in]             Name of a database to use in test
        num_tries[in]      Number of attempts to wait for slave synch
        """

        if not self.replicating:
            print "ERROR: Replication is not running among master and slave."
        print "# Testing replication setup..."
        if self.verbosity > 0:
            print "# Creating a test database on master named %s..." % db
        res = self.master.exec_query("CREATE DATABASE %s" % db,
                                     self.query_options)
        i = 0
        while i < num_tries:
            time.sleep (1)
            res = self.slave.exec_query("SHOW DATABASES")
            for row in res:
                if row[0] == db:
                    res = self.master.exec_query("DROP DATABASE %s" % db,
                                                 self.query_options)
                    print "# Success! Replication is running."
                    i = num_tries
                    break
            i += 1
            if i < num_tries and self.verbosity > 0:
                print "# Waiting for slave to synchronize with master"
        if i == num_tries:
            print "ERROR: Unable to complete testing."


class Master(Server):
    """The Slave class is a subclass of the Server class. It represents a
    MySQL server performing the role of a slave in a replication topology.
    The following utilities are provide in addition to the Server utilities:

        - check to see if replication user is defined and has privileges
        - get binary log exceptions
        - get master status
        - reset master

    """

    def __init__(self, options={}):
        """Constructor

        The method accepts one of the following types for options['conn_info']:

            - dictionary containing connection information including:
              (user, passwd, host, port, socket)
            - connection string in the form: user:pass@host:port:socket
            - an instance of the Server class

        options[in]        options for controlling behavior:
            conn_info      a dictionary containing connection information
                           (user, passwd, host, port, socket)
            role           Name or role of server (e.g., server, master)
            verbose        print extra data during operations (optional)
                           default value = False
            charset        Default character set for the connection.
                           (default latin1)
        """

        assert not options.get("conn_info") == None

        self.options = options
        Server.__init__(self, options)


    def get_status(self):
        """Return the master status

        Returns result set
        """
        return self.exec_query("SHOW MASTER STATUS")


    def get_binlog_exceptions(self):
        """Get any binary logging exceptions

        This method queries the server status for the *-do-db and
        *-ignore-db settings.

        Returns [] - no exceptions, list if exceptions found
        """
        rows = []
        res = self.get_status()
        if res != []:
            do_db = res[0][_MASTER_DO_DB]
            ignore_db = res[0][_MASTER_IGNORE_DB]
            if len(do_db) > 0 or len(ignore_db) > 0:
                rows.append(('master', do_db, ignore_db))

        return rows


    def get_rpl_users(self, options={}):
        """Attempts to find the users who have the REPLICATION SLAVE privilege

        options[in]    query options

        Returns tuple list - (string, string, bool) = (user, host, has_password)
        """
        return self.exec_query(_RPL_USER_QUERY, options)


    def create_rpl_user(self, host, port, r_user, r_pass=None, verbosity=0):
        """Create the replication user and grant privileges

        If the user exists, check privileges and add privileges as needed.

        host[in]       host of the slave
        port[in]       port of the slave
        r_user[in]     user to create
        r_pass[in]     password for user to create (optional)
        verbosity[in]  verbosity of output
                       Default = 0

        Returns bool - True = success, False = errors
        """

        from mysql.utilities.common.user import User

        # Create user class instance
        user = User(self, "%s@%s:%s" % (r_user, host, port), verbosity)

        if not user.has_privilege("*", "*", "REPLICATION SLAVE"):
            if verbosity > 0:
                print "# Granting replication access to replication user..."
            query_str = "GRANT REPLICATION SLAVE ON *.* TO '%s'@'%s' " % \
                        (r_user, host)
            if r_pass:
                query_str += "IDENTIFIED BY '%s'" % r_pass
            try:
                self.exec_query(query_str)
            except UtilError, e:
                print "ERROR: Cannot grant replication slave to " + \
                      "replication user."
                return False

        return True


    def reset(self, options={}):
        """Reset the master

        options[in]    query options
        """
        return self.exec_query("RESET MASTER", options)


    def check_rpl_health(self):
        """Check replication health of the master.

        This method checks to see if the master is setup correctly to
        operate in a replication environment. It returns a tuple with a
        bool to indicate if health is Ok (True), and a list to contain any
        errors encountered during the checks.

        Returns tuple (bool, []) - (True, []) = Ok,
                                   (False, error_list) = not setup correctly
        """
        errors = []
        rpl_ok = True

        if not self.is_alive():
            return (False, ["Cannot connect to server"])

        gtid_enabled = self.supports_gtid() == "ON"

        # Check for binlogging
        if not gtid_enabled and not self.binlog_enabled():
            errors.append("No binlog on master.")
            rpl_ok = False

        # See if there is at least one user with rpl privileges
        res = self.get_rpl_users()
        if len(res) == 0:
            errors.append("There are no users with replication privileges.")
            rpl_ok = False

        return (rpl_ok, errors)


    def _check_discovered_slave(self, conn_dict):
        """ Check discovered slave is configured to this master

        This method attempts to determine if the slave specified is
        configured to connect to this master.

        conn_dict[in]  dictionary of connection information

        Returns bool - True - is configured, False - not configured
        """
        if conn_dict['conn_info']['host'] == '127.0.0.1':
            conn_dict['conn_info']['host'] = 'localhost'
        # Now we must attempt to connect to the slave.
        slave_conn = Slave(conn_dict)
        is_configured = False
        try:
            slave_conn.connect()
            # Skip discovered slaves that are not configured
            # to connect to the master
            if slave_conn.is_configured_for_master(self, verify_state=False):
                is_configured = True
        except Exception, e:
            print "Error connecting to a slave as %s@%s: %s" % \
                  (conn_dict['conn_info']['user'],
                   conn_dict['conn_info']['host'],
                   e.errmsg)
        finally:
            slave_conn.disconnect()

        return is_configured


    def get_slaves(self, user, password):
        """Return the slaves registered for this master.

        This method returns a list of slaves (host, port) if this server is
        a master in a replication topology and has slaves registered.

        user[in]       user login
        password[in]   user password

        Returns list - [host:port, ...]
        """
        def _get_slave_info(host, port):
            if len(host) > 0:
                slave_info = host
            else:
                slave_info = "unknown host"
            slave_info += ":%s" % port
            return slave_info

        slaves = []
        no_host_slaves = []
        connect_error_slaves = []
        res = self.exec_query("SHOW SLAVE HOSTS")
        if not res == []:
            res.sort()  # Sort for conformity
            for row in res:
                info = _get_slave_info(row[1], row[2])
                conn_dict = {
                    'conn_info' : { 'user' : user, 'passwd' : password,
                                    'host' : row[1], 'port' : row[2],
                                    'socket' : None },
                    'role'      : 'slave',
                    'verbose'   : self.options.get("verbosity", 0) > 0,
                }
                if not row[1]:
                    no_host_slaves.append(info)
                elif self._check_discovered_slave(conn_dict):
                    slaves.append(info)
                else:
                    connect_error_slaves.append(info)

        if no_host_slaves:
            print "WARNING: There are slaves that have not been registered" + \
                  " with --report-host or --report-port."
            if self.options.get("verbosity", 0) > 0:
                for row in no_host_slaves:
                    print "\t", row

        if connect_error_slaves:
            print "\nWARNING: There are slaves that had connection errors."
            if self.options.get("verbosity", 0) > 0:
                for row in connect_error_slaves:
                    print "\t", row

        return slaves


    def get_gtid_purged_statement(self):
        """General the SET @@GTID_PURGED statement for backup

        Returns string - statement for slave if GTID=ON, else None
        """
        if self.supports_gtid == "ON":
            gtid_executed = self.exec_query("SELECT @@GLOBAL.GTID_EXECUTED")[0]
            return 'SET @@GLOBAL.GTID_PURGED = "%s"' % gtid_executed
        else:
            return None


class MasterInfo(object):
    """The MasterInfo is an abstraction of the mechanism for storing the
    master information for slave servers. It is designed to return an
    implementation neutral representation of the information for use in
    newer servers that use a table to store the information as well as
    older servers that use a file to store the information.
    """

    def __init__(self, slave, options):
        """Constructor

        The method accepts one of the following types for options['conn_info']:

            - dictionary containing connection information including:
              (user, passwd, host, port, socket)
            - connection string in the form: user:pass@host:port:socket
            - an instance of the Server class

        options[in]        options for controlling behavior:
          filename         filename for master info file - valid only for
                           servers with master-info-repository=FILE or
                           versions prior to 5.6.5.
          verbosity        determines level of output. Default = 0.
          quiet            turns off all messages except errors.
                           Default is False.
        """

        assert slave is not None, "MasterInfo requires an instance of Slave."
        self.slave = slave
        self.filename = options.get("master_info", "master.info")
        self.quiet = options.get("quiet", False)
        self.verbosity = options.get("verbosity", 0)
        self.values = {}      # internal dictionary of the values
        self.repo = "FILE"
        if self.slave is not None:
            res = self.slave.show_server_variable("master_info_repository")
            if res is not None and res != [] and \
               res[0][1].upper() == "TABLE":
                self.repo = "TABLE"


    def read(self):
        """Read the master information

        This method reads the master information either from a file or a
        table depending on the availability of and setting for
        master-info-repository. If missing (server version < 5.6.5), it
        defaults to reading from a file.

        Returns bool - True = success
        """
        if self.verbosity > 2:
            print "# Reading master information from a %s." % self.repo.lower()
        if self.repo == "FILE":
            import socket

            # Check host name of this host. If not the same, issue error.
            if self.slave.is_alias(socket.gethostname()):
                return self._read_master_info_file()
            else:
                raise UtilRplWarn("Cannot read master information file "
                                  "from a remote machine.")
        else:
            return self._read_master_info_table()


    def _check_read(self, refresh=False):
        """Check if master information has been read

        refresh[in]    if True, re-read the master information.
                       Default is False.

        If the master information has not been read, read it and populate
        the dictionary.
        """
        # Read the values if not already read or user says to refresh them.
        if self.values is None or self.values == {} or refresh:
            self.read()


    def _build_dictionary(self, rows):
        """Build the internal dictionary of values.

        rows[in]       Rows as read from the file or table
        """
        for i in range(0, len(rows)):
            self.values[_MASTER_INFO_COL[i]] = rows[i]


    def _read_master_info_file(self):
        """Read the contents of the master.info file.

        This method will raise an error if the file is missing or cannot be
        read by the user.

        Returns bool - success = True
        """
        contents = []
        res = self.slave.show_server_variable('datadir')
        if res is None or res == []:
            raise UtilRplError("Cannot get datadir.")
        datadir = res[0][1]
        if self.filename == 'master.info':
            self.filename = os.path.join(datadir, self.filename)

        if not os.path.exists(self.filename):
            raise UtilRplError("Cannot find master information file: "
                               "%s." % self.filename)
        try:
            mfile = open(self.filename, 'r')
            num = int(mfile.readline())
            # Protect overrun of array if master_info file length is
            # changed (more values added).
            if num > len(_MASTER_INFO_COL):
                num = len(_MASTER_INFO_COL)
        except:
            raise UtilRplError("Cannot read master information file: "
                               "%s.\nUser needs to have read access to "
                               "the file." % self.filename)
        # Build the dictionary
        for i in range(1, num):
            contents.append(mfile.readline().strip('\n'))
        self._build_dictionary(contents)
        mfile.close()

        return True


    def _read_master_info_table(self):
        """Read the contents of the slave_master_info table.

        This method will raise an error if the file is missing or cannot be
        read by the user.

        Returns bool - success = True
        """
        res = None
        try:
            res = self.slave.exec_query("SELECT * FROM "
                                        "mysql.slave_master_info")
        except UtilError, e:
            raise UtilRplError("Unable to read the slave_master_info table. "
                               "Error: %s" % e.errmsg)
        if res is None or res == []:
            return False

        # Build dictionary for the information with column information
        rows = []
        for i in range(0, len(res[0][1:])):
            rows.append(res[0][i+1])
        self._build_dictionary(rows)

        return True


    def show_master_info(self, refresh=False):
        """Display the contents of the master information.

        refresh[in]    if True, re-read the master information.
                       Default is False.
        """
        # Check to see if we need to read the information
        self._check_read(refresh)
        stop = len(self.values)
        for i in range(0, stop):
            print "{0:>30} : {1}".format(_MASTER_INFO_COL[i],
                                         self.values[_MASTER_INFO_COL[i]])


    def check_master_info(self, refresh=False):
        """Check to see if master info file matches slave status

        This method will return a list of discrepancies if the master.info
        file does not match slave status. It will also raise errors if there
        are problem accessing the master.info file.

        refresh[in]    if True, re-read the master information.
                       Default is False.

        Returns [] - no exceptions, list if exceptions found
        """
        # Check to see if we need to read the information
        self._check_read(refresh)
        errors = []
        res = self.slave.get_status()
        if res != []:
            state = res[0][_SLAVE_IO_STATE]
            if not state:
                raise UtilRplError("Slave is stopped.")
            m_host = res[0][_SLAVE_MASTER_HOST]
            m_port = res[0][_SLAVE_MASTER_PORT]
            rpl_user = res[0][_SLAVE_MASTER_USER]
            if m_host != self.values['Master_Host'] or \
               int(m_port) != int(self.values['Master_Port']) or \
               rpl_user != self.values['Master_User']:
                errors.append("Slave is connected to master differently "
                              "than what is recorded in the master "
                              "information file. Master information file "
                              "= user=%s, host=%s, port=%s." %
                              (self.values['Master_User'],
                               self.values['Master_Host'],
                               self.values['Master_Port']))

        return errors


    def get_value(self, key, refresh=False):
        """Returns the value found for the key or None if key not found.

        refresh[in]    if True, re-read the master information.
                       Default is False.

        Returns value - Value found for the key or None if key missing
        """
        # Check to see if we need to read the information
        self._check_read(refresh)
        try:
            return self.values[key]
        except:
            return None

    def get_master_info(self, refresh=False):
        """Returns the master information dictionary.

        refresh[in]    if True, re-read the master information.
                       Default is False.

        Returns dict - master information
        """
        # Check to see if we need to read the information
        self._check_read(refresh)
        return self.values


class Slave(Server):
    """The Slave class is a subclass of the Server class. It represents a
    MySQL server performing the role of a slave in a replication topology.
    The following utilities are provide in addition to the Server utilities:

        - get methods to return status, binary log exceptions, slave delay,
          thread status, io error, and master information
        - form the change master command with either known master or user-
          supplied values
        - check to see if slave is connected to a master
        - display slave status
        - show master information
        - verify master information matches currently connected master
        - start, stop, and reset slave

    """

    def __init__(self, options={}):
        """Constructor

        The method accepts one of the following types for options['conn_info']:

            - dictionary containing connection information including:
              (user, passwd, host, port, socket)
            - connection string in the form: user:pass@host:port:socket
            - an instance of the Server class

        options[in]        options for controlling behavior:
            conn_info      a dictionary containing connection information
                           (user, passwd, host, port, socket)
            role           Name or role of server (e.g., server, master)
            verbose        print extra data during operations (optional)
                           default value = False
            charset        Default character set for the connection.
                           (default latin1)
        """

        assert not options.get("conn_info") == None
        self.options = options
        Server.__init__(self, options)
        self.master_info = None


    def get_status(self, col_options={}):
        """Return the slave status

        col_options[in]    options for displaying columns (optional)

        Returns result set
        """
        return self.exec_query("SHOW SLAVE STATUS", col_options)


    def get_retrieved_gtid_set(self):
        """Get any events (gtids) read but not executed

        Returns list - gtids in retrieved_gtid_set
        """
        res = self.get_status()
        if res != []:
            return res[0][_RETRIEVED_GTID_SET]
        return []


    def get_executed_gtid_set(self):
        """Get any events (gtids) executed

        Returns list - gtids in retrieved_gtid_set
        """
        res = self.get_status()
        if res != []:
            return res[0][_EXECUTED_GTID_SET]

        return []


    def get_binlog_exceptions(self):
        """Get any binary logging exceptions

        This method queries the server status for the *-do-db and
        *-ignore-db settings.

        Returns [] - no exceptions, list if exceptions found
        """
        rows = []
        res = self.get_status()
        if res != []:
            do_db = res[0][_SLAVE_DO_DB]
            ignore_db = res[0][_SLAVE_IGNORE_DB]
            if len(do_db) > 0 or len(ignore_db) > 0:
                rows.append(('slave', do_db, ignore_db))

        return rows


    def get_master_host_port(self):
        """Get the slave's connected master host and port

        Returns tuple - (master host, master port) or
                        None if not acting as slave
        """
        res = self.get_status()
        if res == []:
            return None
        m_host = res[0][_SLAVE_MASTER_HOST]
        m_port = res[0][_SLAVE_MASTER_PORT]

        return (m_host, m_port)


    def is_connected(self):
        """Check to see if slave is connected to master

        This method will check the slave to see if it is connected to a master.

        Returns bool - True = slave is connected
        """
        res = self.get_status()
        if res == []:
            return False
        return res[0][10].upper() == "YES"

    def get_rpl_master_user(self):
        """Get the rpl master user from the slave status

        Returns the slave_master_user as string or False if there is
        no slave status.
        """
        res = self.get_status()
        if not res:
            return False
        return res[0][_SLAVE_MASTER_USER]

    def get_state(self):
        """Get the slave's connection state

        Returns state or None if not acting as slave
        """
        res = self.get_status()
        if res == []:
            return None
        state = res[0][_SLAVE_IO_STATE]

        return state


    def get_io_running(self):
        """Get the slave's IO thread status

        Returns IO_THREAD state or None if not acting as slave
        """
        res = self.get_status()
        if res == []:
            return None
        state = res[0][_SLAVE_IO_RUNNING]

        return state


    def get_delay(self):
        """Return slave delay values

        This method retrieves the slave's delay parameters.

        Returns tuple - slave delay values or None if not connected
        """
        res = self.get_status()
        if res == []:
            return None

        # slave IO state
        state = res[0][_SLAVE_IO_STATE]
        # seconds behind master
        if res[0][_SLAVE_DELAY] is None:
            sec_behind = 0
        else:
            sec_behind = int(res[0][_SLAVE_DELAY])
        # remaining delay
        delay_remaining = res[0][_SLAVE_REMAINING_DELAY]
        # master's log file read
        read_log_file = res[0][_SLAVE_MASTER_LOG_FILE]
        # position in master's binlog
        read_log_pos = res[0][_SLAVE_MASTER_LOG_FILE_POS]

        return (state, sec_behind, delay_remaining,
                read_log_file, read_log_pos)


    def get_thread_status(self):
        """Return the slave threads status

        Returns tuple - (slave_io_state, slave_io_running, slave_sql_running)
                        or None if not connected
        """
        res = self.get_status()
        if res == []:
            return None

        # slave IO state
        state = res[0][_SLAVE_IO_STATE]
        # slave_io_running
        io_running = res[0][_SLAVE_IO_RUNNING]
        # slave_sql_running
        sql_running = res[0][_SLAVE_SQL_RUNNING]

        return (state, io_running, sql_running)


    def get_io_error(self):
        """Return the slave slave io error status

        Returns tuple - (slave_io_state, io_errorno, io_error)
                        or None if not connected
        """
        res = self.get_status()
        if res == []:
            return None

        state = res[0][_SLAVE_IO_STATE]
        io_errorno = int(res[0][_SLAVE_IO_ERRORNO])
        io_error = res[0][_SLAVE_IO_ERROR]

        return (state, io_errorno, io_error)

    def get_slaves_errors(self):
        """Return the slave slave io and sql error status

        Returns tuple - (slave_io_state, io_errorno, io_error, io_running,
                         sql_running, sql_errorno, sql_error)
                        or None if not connected
        """
        res = self.get_status()
        if not res:
            return None

        state = res[0][_SLAVE_IO_STATE]
        io_errorno = int(res[0][_SLAVE_IO_ERRORNO])
        io_error = res[0][_SLAVE_IO_ERROR]
        io_running = res[0][_SLAVE_IO_RUNNING]
        sql_running = res[0][_SLAVE_SQL_RUNNING]
        sql_errorno = int(res[0][_SLAVE_SQL_ERRORNO])
        sql_error = res[0][_SLAVE_SQL_ERROR]

        return (state, io_errorno, io_error, io_running, sql_running,
                sql_errorno, sql_error)


    def show_status(self):
        """Display the slave status from the slave server
        """
        col_options = {
            'columns' : True
        }
        res = self.get_status(col_options)
        if res != [] and res[1] != []:
            stop = len(res[0])
            cols = res[0]
            rows = res[1]
            for i in range(0, stop):
                print "{0:>30} : {1}".format(cols[i], rows[0][i])
        else:
            raise UtilRplError("Cannot get slave status or slave is "
                                 "not configured as a slave or not "
                                 "started.")


    def get_rpl_user(self):
        """Return the master user from the master info record.

        Returns - tuple = (user, password) or (None, None) if errors
        """
        self.master_info = MasterInfo(self, self.options)
        m_host = self.master_info.get_value("Master_User")
        m_passwd = self.master_info.get_value("Master_Password")
        if m_host is not None:
            return (m_host, m_passwd)
        return (None, None)


    def start(self, options={}):
        """Start the slave

        options[in]    query options
        """
        return self.exec_query("START SLAVE", options)

    def start_sql_thread(self, options={}):
        """Start the slave SQL thread

        options[in]    query options
        """
        return self.exec_query("START SLAVE SQL_THREAD", options)

    def stop(self, options={}):
        """Stop the slave

        options[in]    query options
        """
        return self.exec_query("STOP SLAVE", options)


    def reset(self, options={}):
        """Reset the slave

        options[in]    query options
        """
        return self.exec_query("RESET SLAVE", options)


    def reset_all(self, options={}):
        """Reset all information on this slave.

        options[in]    query options
        """
        # Must be sure to do stop first
        self.stop()
        # RESET SLAVE ALL was implemented in version 5.5.16 and later
        if not self.check_version_compat(5, 5, 16):
            return self.reset()
        return self.exec_query("RESET SLAVE ALL", options)


    def num_gtid_behind(self, master_gtids):
        """Get the number of transactions the slave is behind the master.

        master_gtids[in]  the master's GTID_EXECUTED list

        Returns int - number of trans behind master
        """
        slave_gtids = self.exec_query(_GTID_EXECUTED)[0][0]
        gtids = self.exec_query("SELECT GTID_SUBTRACT('%s','%s')" %
                               (master_gtids[0][0], slave_gtids))[0]
        if len(gtids) == 1 and len(gtids[0]) == 0:
            gtid_behind = 0
        else:
            gtids = gtids[0].split("\n")
            gtid_behind = len(gtids)
        return gtid_behind


    def wait_for_slave(self, binlog_file, binlog_pos, timeout=300):
        """Wait for the slave to read the master's binlog to specified position

        binlog_file[in]  master's binlog file
        binlog_pos[in]   master's binlog file position
        timeout[in]      maximum number of seconds to wait for event to occur

        Returns bool - True = slave has read to the file and pos,
                       False = slave is behind.
        """
        # Wait for slave to read the master log file
        _MASTER_POS_WAIT = "SELECT MASTER_POS_WAIT('%s', %s, %s)"
        res = self.exec_query(_MASTER_POS_WAIT % (binlog_file,
                                                  binlog_pos, timeout))
        if res is None or (res[0][0] is not None and int(res[0][0]) < 0):
            return False
        return True


    def wait_for_slave_gtid(self, master_gtid, timeout=300, verbose=False):
        """Wait for the slave to read the master's GTIDs.

        This method requires that the server supports GTIDs.

        master_gtid[in]  the list of gtids from the master
                         obtained via SELECT @@GLOBAL.GTID_EXECUTED on master
        timeout[in]      timeout for waiting for slave to catch up
                         Note: per GTID call. Default is 300 seconds (5 min.).
        verbose[in]      if True, print query used.
                         Default is False

        Returns bool - True = slave has read all GTIDs
                       False = slave is behind
        """
        m_gtid_str = " ".join(master_gtid[0][0].split('\n'))
        master_gtids = master_gtid[0][0].split('\n')
        slave_wait_ok = True
        for gtid in master_gtids:
            try:
                if verbose:
                    print "# Slave %s:%s:" % (self.host, self.port)
                    print "# QUERY =", _GTID_WAIT % (gtid.strip(','), timeout)
                res = self.exec_query(_GTID_WAIT % (gtid.strip(','), timeout))
                if verbose:
                    print "# Return Code =", res[0][0]
                if res is None or res[0] is None or res[0][0] is None or \
                   int(res[0][0]) < 0:
                    slave_wait_ok = False
            except UtilRplError, e:
                raise UtilRplError("Error executing %s: %s" %
                                   ((_GTID_WAIT % (gtid.strip(','), timeout)),
                                   e.errmsg))
        return slave_wait_ok


    def make_change_master(self, from_beginning=False, master_values={}):
        """Make the CHANGE MASTER command.

        This method forms the CHANGE MASTER command based on the current
        settings of the slave. If the user supplies a dictionary of options,
        the method will use those values provided by the user if present
        otherwise it will use current settings.

        Note: the keys used in the dictionary are defined in the
              _MASTER_INFO_COL list defined above.

        from_beginning[in] if True, omit specification of master's binlog info
        master_values[in] if provided, use values in the dictionary

        Returns string - CHANGE MASTER command
        """
        if master_values == {} and not self.is_connected():
            raise UtilRplError("Cannot generate CHANGE MASTER command. The "
                               "slave is not connected to a master and no "
                               "master information was provided.")
        elif self.is_connected():
            m_info = MasterInfo(self, self.options)
            master_info = m_info.get_master_info()
            if master_info is None and master_values == {}:
                raise UtilRplError("Cannot create CHANGE MASTER command.")
        else:
            master_info = None

        # Form values for command.
        # If we cannot get the master info information, try the values passed
        if master_info is None:
            master_host = master_values['Master_Host']
            master_port = master_values['Master_Port']
            master_user = master_values['Master_User']
            master_passwd = master_values['Master_Password']
            master_log_file = master_values['Master_Log_File']
            master_log_pos = master_values['Read_Master_Log_Pos']
        else:
            master_host = master_values.get('Master_Host',
                                            master_info['Master_Host'])
            master_port = master_values.get('Master_Port',
                                            master_info['Master_Port'])
            master_user = master_values.get('Master_User',
                                            master_info['Master_User'])
            master_passwd = master_values.get('Master_Password',
                                               master_info['Master_Password'])
            master_log_file = master_values.get('Master_Log_File',
                                                master_info['Master_Log_File'])
            master_log_pos = master_values.get('Read_Master_Log_Pos',
                                            master_info['Read_Master_Log_Pos'])

        change_master = "CHANGE MASTER TO MASTER_HOST = '%s', " % master_host
        if master_user:
            change_master += "MASTER_USER = '%s', " % master_user
        if master_passwd:
            change_master += "MASTER_PASSWORD = '%s', " % master_passwd
        change_master += "MASTER_PORT = %s" % master_port
        if self.supports_gtid() == "ON":
            change_master += ", MASTER_AUTO_POSITION=1"
        elif not from_beginning:
            change_master += ", MASTER_LOG_FILE = '%s'" % master_log_file
            if master_log_pos >= 0:
                change_master += ", MASTER_LOG_POS = %s" % master_log_pos

        return change_master


    def is_configured_for_master(self, master, verify_state=False):
        """Check that slave is connected to the master at host, port.

        master[in]     instance of the master

        Returns bool - True = is connected
        """
        res = self.get_status()
        if res == [] or not res[0]:
            return False
        res = res[0]
        m_host, m_port = self.get_master_host_port()
        # Suppose the state is True for "Waiting for master to send event"
        # so we can ignore it if verify_state is not given as True.
        state = True
        if verify_state:
            state = self.get_state() == "Waiting for master to send event"
        if (not master.is_alias(m_host) or int(m_port) != int(master.port)
            or not state):
            return False
        return True


    def check_rpl_health(self, master, master_log, master_log_pos,
                         max_delay, max_pos, verbosity):
        """Check replication health of the slave.

        This method checks to see if the slave is setup correctly to
        operate in a replication environment. It returns a tuple with a
        bool to indicate if health is Ok (True), and a list to contain any
        errors encountered during the checks.

        master[in]         Master class instance
        master_log[in]     master's log file
        master_log_pos[in] master's log file position
        max_delay[in]      if the slave delay (in seconds) is greater than this
                           value, the slave health is not Ok
        max_pos[in]        maximum position difference from master to slave to
                           determine if slave health is not Ok
        verbosity[in]      if > 1, return detailed errors else return only
                           short phrases

        Returns tuple (bool, []) - (True, []) = Ok,
                                   (False, error_list) = not setup correctly
        """
        errors = []
        rpl_ok = True

        if not self.is_alive():
            return (False, ["Cannot connect to server"])

        res = self.get_status()
        if res != [] and res[0] != []:
            res = res[0]
            state = res[_SLAVE_IO_STATE]
            m_host, m_port = self.get_master_host_port()
            m_log = res[_SLAVE_MASTER_LOG_FILE]
            m_log_pos = res[_SLAVE_MASTER_LOG_FILE_POS]
            io_running = res[_SLAVE_IO_RUNNING]
            sql_running = res[_SLAVE_SQL_RUNNING]
            s_delay = res[_SLAVE_DELAY]
            delay = s_delay if s_delay is not None else 0
            remaining_delay = res[_SLAVE_REMAINING_DELAY]
            io_error_num = res[_SLAVE_IO_ERRORNO]
            io_error_text = res[_SLAVE_IO_ERROR]

            # Check to see that slave is connected to the right master
            if not self.is_configured_for_master(master):
                return (False, ["Not connected to correct master."])

            # Check slave status for errors, threads activity
            if io_running.upper() != "YES":
                errors.append("IO thread is not running.")
                rpl_ok = False
            if sql_running.upper() != "YES":
                errors.append("SQL thread is not running.")
                rpl_ok = False
            if int(io_error_num) > 0:
                errors.append(io_error_text)
                rpl_ok = False

            # Check slave delay with threshhold of SBM, and master's log pos
            if int(delay) > int(max_delay):
                errors.append("Slave delay is %s seconds behind master." %
                              delay)
                if len(remaining_delay):
                    errors.append(remaining_delay)
                rpl_ok = False

            # Check master position
            if self.supports_gtid() != "ON":
                if m_log != master_log:
                    errors.append("Wrong master log file.")
                    rpl_ok = False
                elif (int(m_log_pos) + int(max_pos)) < int(master_log_pos):
                    errors.append("Slave's master position exceeds maximum.")
                    rpl_ok = False

            # Check GTID trans behind.
            elif self.supports_gtid() == "ON":
                master_gtids = master.exec_query(_GTID_EXECUTED)
                num_gtids_behind = self.num_gtid_behind(master_gtids)
                if num_gtids_behind > 0:
                    errors.append("Slave has %s transactions behind master." %
                                  num_gtids_behind)
                    rpl_ok = False

        else:
            errors.append("Not connected")
            rpl_ok = False

        if len(errors) > 1:
            errors = [", ".join(errors)]

        return (rpl_ok, errors)


    def get_rpl_details(self):
        """Return slave status variables for health reporting

        This method retrieves the slave's parameters for checking relationship
        with master.

        Returns tuple - slave values or None if not connected
        """
        res = self.get_status()
        if res == []:
            return None

        res = res[0]
        read_log_file = res[_SLAVE_MASTER_LOG_FILE]
        read_log_pos = res[_SLAVE_MASTER_LOG_FILE_POS]
        io_thread = res[_SLAVE_IO_RUNNING]
        sql_thread = res[_SLAVE_SQL_RUNNING]

        # seconds behind master
        if res[_SLAVE_DELAY] is None:
            sec_behind = 0
        else:
            sec_behind = int(res[_SLAVE_DELAY])
        delay_remaining = res[_SLAVE_REMAINING_DELAY]

        io_error_num = res[_SLAVE_IO_ERRORNO]
        io_error_text = res[_SLAVE_IO_ERROR]
        sql_error_num = res[_SLAVE_SQL_ERRORNO]
        sql_error_text = res[_SLAVE_SQL_ERROR]

        return (read_log_file, read_log_pos, io_thread, sql_thread, sec_behind,
                delay_remaining, io_error_num, io_error_text, sql_error_num,
                sql_error_text)


    def switch_master(self, master, user, passwd="", from_beginning=False,
                      master_log_file=None, master_log_pos=None,
                      show_command=False):
        """Switch slave to a new master

        This method stops the slave and issues a new change master command
        to the master specified then starts the slave. No prerequisites are
        checked and it does not wait to see if slave catches up to the master.

        master[in]           Master class instance
        user[in]             replication user
        passwd[in]           replication user password
        from_beginning[in]   if True, start from beginning of logged events
                             Default = False
        master_log_file[in]  master's log file (not needed for GTID)
        master_log_pos[in]   master's log file position (not needed for GTID)
        show_command[in]     if True, display the change master command
                             Default = False

        returns bool - True = success
        """
        hostport = "%s:%s" % (self.host, self.port)

        master_values = {
            'Master_Host'          : master.host,
            'Master_Port'          : master.port,
            'Master_User'          : user,
            'Master_Password'      : passwd,
            'Master_Log_File'      : master_log_file,
            'Read_Master_Log_Pos'  : master_log_pos,
        }
        change_master = self.make_change_master(from_beginning, master_values)
        if show_command:
            print "# Change master command for %s:%s" % (self.host, self.port)
            print "#", change_master
        res = self.exec_query(change_master)
        if res is None or res != ():
            raise UtilRplError("Slave %s:%s change master failed.",
                               (hostport, res[0]))
        return True
