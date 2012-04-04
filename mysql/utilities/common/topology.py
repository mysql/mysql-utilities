#
# Copyright (c) 2010, 2012 Oracle and/or its affiliates. All rights reserved.
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

import logging
import os
import re
import time
from mysql.utilities.common.lock import Lock
from mysql.utilities.common.replication import Master, Slave, Replication
from mysql.utilities.common.server import Server, get_server_state
from mysql.utilities.exception import UtilError, UtilDBError
from mysql.utilities.exception import UtilRplError, UtilBinlogError
        

_HEALTH_COLS = ["host", "port", "role", "state", "gtid_mode", "health"]
_HEALTH_DETAIL_COLS = ["version", "master_log_file", "master_log_pos",
                       "IO_Thread", "SQL_Thread", "Secs_Behind",
                       "Remaining_Delay", "IO_Error_Num", "IO_Error",
                       "SQL_Error_Num", "SQL_Error", "Trans_Behind"]

_GTID_DONE = "SELECT @@GLOBAL.GTID_DONE"
_GTID_WAIT = "SELECT SQL_THREAD_WAIT_AFTER_GTIDS('%s', %s)"


def parse_failover_connections(options):
    """Parse the --master, --slaves, and --candidates options
    
    This method returns a tuple with server connection dictionaries for
    the master, slaves, and candidates lists.
    
    If no master, will return (None, ...) for master element.
    If no slaves, will return (..., [], ...) for slaves element.
    If no canidates, will return (..., ..., []) for canidates element.
    
    Will raise error if cannot parse connection options.
    
    options[in]        options from parser
    
    Returns tuple - (master, slaves, candidates) dictionaries
    """
    from mysql.utilities.common.options import parse_connection
    from mysql.utilities.exception import FormatError

    if options.master:
        try:
            master_val = parse_connection(options.master)
        except FormatError, e:
            msg = "Master connection values invalid or cannot be parsed."
            raise UtilRplError(msg)
    else:
        master_val = None

    slaves_val = []
    if options.slaves:
        slaves = options.slaves.split(",")
        for slave in slaves:
            try:
                s_values = parse_connection(slave)
                slaves_val.append(s_values)
            except FormatError, e:
                msg = "Slave connection values invalid or " + \
                      "cannot be parsed: %s" % slave
                raise UtilRplError(msg)
    
    candidates_val = []
    if options.candidates:
        candidates = options.candidates.split(",")
        for slave in candidates:
            try:
                s_values = parse_connection(slave)
                candidates_val.append(s_values)
            except FormatError, e:
                msg = "Candidate connection values invalid or " + \
                      "cannot be parsed: %s" % slave
                raise UtilRplError(msg)
                
    return (master_val, slaves_val, candidates_val)


class Topology(Replication):
    """The Topology class supports administrative operations for an existing
    master-to-many slave topology. It has the following capabilities:

        - determine the health of the topology
        - discover slaves connected to the master provided they have
          --report-host and --report-port specified
        - switchover from master to a candidate slave
        - demote the master to a slave in the topology
        - perform best slave election
        - failover to a specific slave or best of slaves available
        
    Notes:
    
        - the switchover and demote methods work with versions prior to and
          after 5.6.5.
        - failover and best slave election require version 5.6.5 and later
          and GTID_MODE=ON.
        
    """

    def __init__(self, master_vals, slave_vals, options={},
                 skip_conn_err=False):
        """Constructor
        
        The slaves parameter requires a dictionary in the form:
                
        master_vals[in]    master server connection dictionary
        slave_vals[in]     list of slave server connection dictionaries
        options[in]        options dictionary
          verbose          print extra data during operations (optional)
                           Default = False
          ping             maximum number of seconds to ping
                           Default = 3
          max_delay        maximum delay in seconds slave and be behind
                           master and still be 'Ok'. Default = 0
          max_position     maximum position slave can be behind master's
                           binlog and still be 'Ok'. Default = 0
        skip_conn_err[in]  if True, do not fail on connection failure 
                           Default = True                           
        """
        # Get options needed
        self.options = options
        self.verbosity = options.get("verbosity", 0)
        self.verbose = self.verbosity > 0
        self.quiet = self.options.get("quiet", False)
        self.pingtime = self.options.get("ping", 3)
        self.max_delay = self.options.get("max_delay", 0)
        self.max_pos = self.options.get("max_position", 0)
        self.force = self.options.get("force", False)
        self.before_script = self.options.get("before", None)
        self.after_script = self.options.get("after", None)
        self.timeout = self.options.get("timeout", 3)
        self.logging = self.options.get("logging", False)
        
        # Attempt to connect to all servers        
        self.master, self.slaves = self._connect_to_servers(master_vals,
                                                            slave_vals,
                                                            self.options,
                                                            skip_conn_err)
        self.discover_slaves()
        
        
    def _report(self, message, level=logging.INFO, print_msg=True):
        """Log message if logging is on
        
        This method will log the message presented if the log is turned on.
        Specifically, if options['log_file'] is not None. It will also
        print the message to stdout.
        
        message[in]    message to be printed
        level[in]      level of message to log. Default = INFO
        print_msg[in]  if True, print the message to stdout. Default = True
        """
        # First, print the message.
        if print_msg and not self.quiet:
            print message
        # Now log message if logging turned on
        if self.logging:
            logging.log(int(level), message.strip("#").strip(' '))


    def _connect_to_servers(self, master_vals, slave_vals, options,
                            skip_conn_err=True):
        """Connect to the master and one or more slaves
    
        This method will attempt to connect to the master and slaves provided.
        For slaves, if the --force option is specified, it will skip slaves
        that cannot be reached setting the slave dictionary to None
        in the list instead of a Slave class instance.
        
        The dictionary of the list of slaves returns is as follows.
        
        slave_dict = {
          'host'     : # host name for slave
          'port'     : # port for slave
          'instance' : Slave class instance or None if cannot connect and --force    
        }
                
        master_vals[in]    master server connection dictionary
        slave_vals[in]     list of slave server connection dictionaries
        options[in]        options dictionary
          verbose          print extra data during operations (optional)
                           Default = False
          ping             maximum number of seconds to ping
                           Default = 3
          max_delay        maximum delay in seconds slave and be behind
                           master and still be 'Ok'. Default = 0
          max_position     maximum position slave can be behind master's
                           binlog and still be 'Ok'. Default = 0
        skip_conn_err[in]  if True, do not fail on connection failure 
                           Default = True                           

        Returns tuple - master instance, list of dictionary slave instances
        """
        from mysql.utilities.common.server import get_server
    
        master = None
        slaves = []
        
        # attempt to connect to the master
        if master_vals:
            master = get_server('master', master_vals, True)
        
        for slave_val in slave_vals:
            host = slave_val['host']
            port = slave_val['port']
            try:
                slave = get_server('slave', slave_val, True)
            except:
                msg = "Cannot connect to slave %s:%s as user '%s'." % \
                      (host, port, slave_val['user'])
                if skip_conn_err:
                    if self.verbose:
                        self._report("# ERROR: %s" % msg, logging.ERROR)
                    slave = None
                else:
                    raise UtilRplError(msg)
            slave_dict = {
              'host'     : host,      # host name for slave
              'port'     : port,      # port for slave
              'instance' : slave,     # Slave class instance or None
            }
            slaves.append(slave_dict)
        
        return (master, slaves)
        
        
    def _is_connected(self):
        """Check to see if all servers are connected.
        
        Method will skip any slaves that do not have an instance (offline)
        but requires the master be instantiated and connected.
        
        The method will also skip the checks altogether if self.force is
        specified.
        
        Returns bool - True if all connected or self.force is specified.
        """
        # Skip check if --force specified.
        if self.force:
            return True
        if self.master is None or not self.master.is_alive():
            return False
        for slave_dict in self.slaves:
            slave = slave_dict['instance']
            if slave is not None and not slave.is_alive():
                return False
            
        return True
    

    def remove_discovered_slaves(self):
        """Reset the slaves list to the original list at instantiation
        
        This method is used in conjunction with discover_slaves to remove
        any discovered slave from the slaves list. Once this is done,
        a call to discover slaves will rediscover the slaves. This is helpful
        for when failover occurs and a discovered slave is used for the new
        master.
        """
        new_list = []
        for slave_dict in self.slaves:
            if not slave_dict.get("discovered", False):
                new_list.append(slave_dict)
        self.slaves = new_list


    def discover_slaves(self, skip_conn_err=True):
        """Discover slaves connected to the master
        
        Returns bool - True if new slaves found
        """
        from mysql.utilities.common.replication import Slave

        # See if the user wants us to discover slaves.
        discover = self.options.get("discover", None)
        if discover is None:
            return
        
        # Get user and password
        try:
            user, password = discover.split(":")
        except:
            user = discover
            passord = None
            
        # Find discovered slaves
        new_slaves_found = False
        self._report("# Discovering slaves for master at %s:%s" %
                     (self.master.host, self.master.port), False)
        discovered_slaves = self.master.get_slaves()
        for slave in discovered_slaves:
            host, port = slave.split(":")
            # Skip hosts that are not registered properly
            if host == 'unknown host':
                continue
            # Check to see if the slave is already in the list
            else:
                found = False
                # Eliminate if already a slave
                for slave_dict in self.slaves:
                    if slave_dict['host'] == host and \
                       int(slave_dict['port']) == int(port):
                        found = True
                if not found:
                    # Now we must attempt to connect to the slave.
                    conn_dict = {
                        'conn_info' : { 'user' : user, 'passwd' : password,
                                        'host' : host, 'port' : port,
                                        'socket' : None },
                        'role'      : slave,
                        'verbose'   : self.options.get("verbosity", 0) > 0,
                    }
                    slave_conn = Slave(conn_dict)
                    try:
                        slave_conn.connect()
                        m_host = self.master.host
                        m_port = self.master.port
                        # Skip discovered slaves that are not connected
                        # to the master
                        if slave_conn.is_connected_to_master(m_host, m_port) \
                           and slave_conn.is_connected():
                            self.slaves.append({ 'host' : host, 'port' : port,
                                                 'instance' : slave_conn,
                                                 'discovered' : True})
                            new_slaves_found = True                            
                    except:
                        msg = "Cannot connect to slave %s:%s as user '%s'." % \
                              (host, port, user)
                        if skip_conn_err:
                            if self.verbose:
                                self._report("# ERROR: %s" % msg, logging.ERROR)
                        else:
                            raise UtilRplError(msg)
        
        return new_slaves_found


    def _get_server_gtid_data(self, server, role):
        """Retrieve the GTID information from the server.
        
        This method builds a tuple of three lists corresponding to the three
        GTID lists (executed, purged, owned) retrievable via the global
        variables. It generates lists suitable for format and printing.
        
        role[in]           role of the server (used for report generation)
        
        Returns tuple - (executed list, purged list, owned list)
        """
        executed = []
        purged = []
        owned = []
    
        if server.supports_gtid() == "NO":
            return (executed, purged, owned)
    
        try:
            gtids = server.get_gtid_status()
        except UtilError, e:
            self._report("# ERROR retrieving GTID information: %s" % e.errmsg,
                         logging.ERROR)
            return None
        for gtid in gtids[0]:
            for row in gtid.split("\n"):
                if len(row):
                    executed.append((server.host, server.port, role,
                                     row.strip(",")))
        for gtid in gtids[1]:
            for row in gtid.split("\n"):
                if len(row):
                    purged.append((server.host, server.port, role,
                                   row.strip(",")))
        for gtid in gtids[2]:
            for row in gtid.split("\n"):
                if len(row):
                    owned.append((server.host, server.port, role,
                                  row.strip(",")))
        
        return (executed, purged, owned)
    

    def _check_switchover_prerequisites(self, candidate=None):
        """Check prerequisites for performing switchover
        
        This method checks the prerequisites for performing a switch from a
        master to a candidate slave.
        
        candidate[in]  if supplied, use this candidate instead of the
                       candidate supplied by the user. Must be instance of
                       Master class.
                       
        Returns bool - True if success, raises error if not
        """
        if candidate is None:
            candidate = self.options.get("candidate", None)
            
        assert (candidate is not None), "A candidate server is required."
        assert (type(candidate) == Master), \
               "A candidate server must be a Master class instance."
        
        from mysql.utilities.common.replication import Slave

        # If master has GTID=ON, ensure all servers have GTID=ON
        gtid_enabled = self.master.supports_gtid() == "ON"
        if gtid_enabled:
            gtid_ok = True
            for slave_dict in self.slaves:
                slave = slave_dict['instance']
                # skip dead or zombie slaves
                if slave is None or not slave.is_alive():
                    continue
                if slave.supports_gtid() != "ON":
                    gtid_ok = False
            if not gtid_ok:
                msg = "GTIDs are enabled on the master but not " + \
                      "on all of the slaves."
                self._report(msg, logging.CRITICAL)
                raise UtilRplError(msg)
            elif self.verbose:
                self._report("# GTID_MODE=ON is set for all servers.")

        # Need Slave class instance to check master and replication user
        slave = self._change_role(candidate)
        
        # Check eligibility
        candidate_ok = self._check_candidate_eligibility(slave.host,
                                                         slave.port,
                                                         slave)
        if not candidate_ok[0]:
            # Create replication user if --force is specified.
            if self.force and candidate_ok[1] == "RPL_USER":
                user, passwd = slave.get_rpl_user()
                m_candidate.create_rpl_user("%s:%s" % (user, passwd),
                                            slave.host, slave.port)
            else:
                msg = candidate_ok[2]
                self._report(msg, logging.CRITICAL)
                raise UtilRplError(msg)

        return True

    
    def _get_rpl_user(self, server):
        """Get the replication user
        
        This method returns the user and password for the replication user
        as read from the Slave class.
        
        Returns tuple - user, password
        """
        slave = self._change_role(server)
        user, passwd = slave.get_rpl_user()
        return user, passwd

    
    def run_script(self, script, quiet):
        """Run an external script
        
        This method executes an external script. Result is checked for
        success (res == 0).
        
        script[in]     script to execute
        quiet[in]      if True, do not print messages
        
        Returns bool - True = success
        """
        from mysql.utilities.common.tools import execute_script

        if script is None:
            return
        self._report("# Spawning external script.")
        res = execute_script(script)
        if res == 0:
            self._report("# Script completed Ok.")
        elif not quiet:
            self._report("ERROR: %s Script failed. Result = %s" %
                         (script, res), logging.ERROR)


    def _check_filters(self, master, slave):
        """Check filters to ensure they are compatible with the master.
        
        This method compares the binlog_do_db with the replicate_do_db and
        the binlog_ignore_db with the replicate_ignore_db on the master and
        slave to ensure the candidate slave is not filtering out different
        databases than the master.
        
        master[in]     the Master class instance of the master
        slave[in]      the Slave class instance of the slave
        
        Returns bool - True = filters agree
        """
        import sys
        from mysql.utilities.common.format import print_list
        
        m_filter = master.get_binlog_exceptions()
        s_filter = slave.get_binlog_exceptions()
        
        failed = False
        if len(m_filter) != len(s_filter):
            failed = True
        elif len(m_filter) == 0:
            return True
        elif m_filter[0][1] != s_filter[0][1] or m_filter[0][2] != s_filter[0][2]:
            failed = True
        if failed:
            if self.verbose and not self.quiet:
                format = self.options.get("format", "GRID")
                rows = []
                if len(m_filter) == 0:
                    rows.append(('MASTER','',''))
                else:
                    rows.append(m_filter[0])
                if len(s_filter) == 0:
                    rows.append(('SLAVE','',''))
                else:
                    rows.append(s_filter[0])
                cols = ["role","*_do_db","*_ignore_db"]
                self._report("# Filter Check Failed.", logging.ERROR)
                print_list(sys.stdout, format, cols, rows)
            return False
        return True


    def _check_candidate_eligibility(self, host, port, slave,
                                     check_master=True, quiet=False):
        """Perform sanity checks for slave promotion
        
        This method checks the slave candidate to ensure it meets the
        requirements as follows.
        
        Check Name  Description
        ----------- --------------------------------------------------
        CONNECTED   slave is connected to the master
        GTID        slave has GTID_MODE = ON if master has GTID = ON
                    (GTID only)
        BEHIND      slave is not behind master
                    (non-GTID only)
        FILTER      slave's filters match the master
        RPL_USER    slave has rpl user defined
        BINLOG      slave must have binary logging enabled

        host[in]         host name for the slave (used for errors)
        port[in]         port for the slave (used for errors)
        slave[in]        Slave class instance of candidate
        check_master[in] if True, check that slave is connected to the master
        quiet[in]        if True, do not print messages even if verbosity > 0

        Returns tuple (bool, check_name, string) -
            (True, "", "") = candidate is viable,
            (False, check_name, error_message) = candidate is not viable
        """
        assert (slave is not None), "No Slave instance for eligibility check."

        gtid_enabled = slave.supports_gtid() == "ON"
        
        # Is slave connected to master?
        if self.verbose and not quiet:
            self._report("# Checking eligibility of slave %s:%s for "
                         "candidate." % (host, port))
        if check_master:
            msg = "#   Slave connected to master ... %s"
            if not slave.is_alive():
                if self.verbose and not quiet:
                    self._report(msg % "FAIL", logging.WARN)
                return (False, "CONNECTED",
                        "Connection to slave server lost.")            
            if not slave.is_connected_to_master(self.master.host,
                                                self.master.port):
                if self.verbose and not quiet:
                    self._report(msg % "FAIL", logging.WARN)
                return (False, "CONNECTED",
                        "Candidate is not connected to the correct master.")
            if self.verbose and not quiet:
                self._report(msg % "Ok")
        
        # If GTID is active on master, ensure slave is on too.
        if gtid_enabled:
            msg = "#   GTID_MODE=ON ... %s"
            if slave.supports_gtid() != "ON":
                if self.verbose and not quiet:
                    self._report(msg % "FAIL", logging.WARN)
                return (False, "GTID",
                        "Slave does not have GTID support enabled.")
            if self.verbose and not quiet:
                self._report(msg % "Ok")
        
        # Check for slave behind master
        if not gtid_enabled and check_master:
            msg = "#   Slave not behind master ... %s"
            rpl = Replication(self.master, slave, self.options)
            errors = rpl.check_slave_delay()
            if errors != []:
                if self.verbose and not quiet:
                    self._report(msg % "FAIL", logging.WARN)
                return (False, "BEHIND", " ".join(errors))
            if self.verbose and not quiet:
                self._report(msg % "Ok")
        
        # Check filters unless force is on.
        if not self.force and check_master:
            msg = "#   Logging filters agree ... %s"
            if not self._check_filters(self.master, slave):
                if self.verbose and not quiet:
                    self._report(msg % "FAIL", logging.WARN)
                return (False, "FILTERS",
                        "Master and slave filters differ.")
            elif self.verbose and not quiet:
                self._report(msg % "Ok")
                
        # Check replication user - must exist with correct privileges
        user, passwd = slave.get_rpl_user()
        if user is None or slave.check_rpl_user(user, passwd) == []:
            msg = "#   Replication user exists ... %s"
            if self.verbose and not force and not quiet:
                self._report(msg % "FAIL", logging.WARN)
            return (False, "RPL_USER",
                    "Candidate slave is missing replication user.")
        if self.verbose and not self.force and not quiet:
            self._report(msg % "Ok")
                
        # If no GTIDs, we need binary logging enabled on candidate.
        if not gtid_enabled:
            msg = "#   Binary logging turned on ... %s"
            if not slave.binlog_enabled():
                if self.verbose and not quiet:
                    self._report(msg % "FAIL", logging.WARN)
                return (False, "BINLOG",
                        "Binary logging is not enabled on the candidate.")
            if self.verbose and not quiet:
                self._report(msg % "Ok")

        return (True, "", "")
            
    
    def _prepare_candidate_for_failover(self, candidate, user, passwd=""):
        """Prepare candidate slave for slave promotion (in failover)
        
        This method uses the candidate slave specified and connects it to
        each slave in the topology performing a GTID_SUBSET query to wait
        for the candidate (acting as a slave) to catch up. This ensures
        the candidate is now the 'best' or 'most up-to-date' slave in the
        topology.
        
        Method works only for GTID-enabled candidate servers.
        
        candidate[in]  Slave class instance of candidate
        user[in]       replication user
        passwd[in]     replication user password
                       
        Returns bool - True if successful,
                       raises exception if failure and forst is False
        """
        
        assert (candidate is not None), "Candidate must be a Slave instance."
        
        if candidate.supports_gtid() != "ON":
            msg = "Candidate does not have GTID turned on or " + \
                  "does not support GTIDs."
            self._report(msg, logging.CRITICAL)
            raise UtilRplError(msg)

        lock_options = {
            'locking'   : 'flush',
            'verbosity' : 3 if self.verbose else self.verbosity,
            'silent'    : self.quiet,
            'rpl_mode'  : "master",
        }

        hostport = "%s:%s" % (candidate.host, candidate.port)
        for slave_dict in self.slaves:
            subset_error = False
            subset_warning = False
            s_host = slave_dict['host']
            s_port = slave_dict['port']
            catchup_msg = "Candidate unable to resolve missing " + \
                          "GTIDs with slave %s:%s." % (s_host, s_port)

            master = slave_dict['instance']
            # skip dead or zombie slaves
            if master is None or not master.is_alive():
                continue

            # Sanity check: ensure candidate and slave are not the same.
            if s_host == candidate.host and int(s_port) == int(candidate.port):
                continue
            
            res = candidate.stop()
            if res is None or res != () and not self.quiet:
                self._report("Candidate %s:%s failed to stop." %
                             (hostport, res[0]))
 
            # Block writes to slave (master)
            lock_ftwrl = Lock(master, [], lock_options)
            master.set_read_only(True)

            # Connect candidate to slave as its master
            if self.verbose and not self.quiet:
                self._report("# Connecting candidate to %s:%s as a master to "
                             "retrieve unprocessed GTIDs." % (s_host, s_port))  

            if not candidate.switch_master(master, user, passwd, False,
                                           None, None,
                                           self.verbose and not self.quiet):
                msg = "Cannot switch candidate to slave for " + \
                      "slave promotion process."
                self._report(msg, logging.CRITICAL)
                raise UtilRplError(msg)
            
            # Unblock writes to slave (master).
            master.set_read_only(False)
            lock_ftwrl.unlock()

            res = candidate.start()
            if res is None or res != () and not self.quiet:
                self._report("Candidate %s:%s failed to start." % 
                             (hostport, res[0]))

            if self.verbose and not self.quiet:
                self._report("# Waiting for candidate to catch up to slave " 
                             "%s:%s." % (s_host, s_port))
            master_gtid = master.exec_query(_GTID_DONE)
            candidate.wait_for_slave_gtid(master_gtid, self.timeout,
                                          self.verbose and not self.quiet)
            
            # Disconnect candidate from slave (master)
            candidate.stop()
            
        return True


    def _check_all_slaves(self, new_master):
        """Check all slaves for errors.
        
        Check each slave's status for errors during replication. If errors are
        found, they are printed as warning statements to stdout.
        
        new_master[in] the new master in Master class instance
        """
        slave_errors = []
        for slave_dict in self.slaves:
            slave = slave_dict['instance']
            # skip dead or zombie slaves
            if slave is None or not slave.is_alive():
                continue
            rpl = Replication(new_master, slave, self.options)
            # Use timeout to check slave status
            iteration = 0
            slave_ok = True
            while iteration < int(self.timeout):
                res = rpl.check_slave_connection()
                if not res and iteration >= self.timeout:
                    slave_error = None
                    if self.verbose:
                        res = slave.get_io_error()
                        slave_error = "%s:%s" % (res[1], res[2])                    
                    slave_errors.append((slave_dict['host'],
                                         slave_dict['port'],
                                         slave_error))
                    slave_ok = False
                    if self.verbose and not self.quiet:
                        self._report("# %s:%s status: FAIL " %
                                     (slave_dict['host'],
                                      slave_dict['port']), logging.WARN)
                elif res:
                    iteration = int(self.timeout) + 1
                else:
                    time.sleep(1)
                    iteration += 1
            if slave_ok and self.verbose and not self.quiet:
                self._report("# %s:%s status: Ok " % (slave_dict['host'],
                             slave_dict['port']))
                
        if len(slave_errors) > 0:
            self._report("WARNING - The following slaves failed to connect to "
                         "the new master:", logging.WARN)
            for error in slave_errors:
                self._report("  - %s:%s" % (error[0], error[1]), logging.WARN)
                if self.verbose and error[2] is not None:
                    self._report(error[2], logging.WARN)
                else:
                    print
            return False
        
        return True

    
    def _remove_slave(self, slave):
        """Remove a slave from the slaves dictionary list
        
        slave[in]      the dictionary for the slave to remove
        """
        i = 0
        for slave_dict in self.slaves:
            if slave_dict['host'] == slave['host'] and \
               int(slave_dict['port']) == int(slave['port']):
                # Disconnect to satisfy new server restrictions on termination
                self.slaves[i]['instance'].disconnect()
                self.slaves.pop(i)
                break
            i += 1


    def gtid_enabled(self):
        """Check if topology has GTID turned on.
        
        Returns bool - True = GTID_MODE=ON.
        """
        if self.master is not None:
            return self.master.supports_gtid() == "ON"
        for slave_dict in self.slaves:
            slave = slave_dict['instance']
            # skip dead or zombie slaves
            if slave is None or not slave.is_alive():
                continue
            return slave.supports_gtid() == "ON"
        return False


    def get_health(self):
        """Retrieve the replication health for the master and slaves.
        
        This method will retrieve the replication health of the topology. This
        includes the following for each server.
        
          - host       : host name
          - port       : connection port
          - role       : "MASTER" or "SLAVE"
          - state      : UP = connected, WARN = cannot connect but can ping,
                         DOWN = cannot connect nor ping
          - gtid       : ON = gtid supported and turned on, OFF = supported
                         but not enabled, NO = not supported
          - rpl_health : (master) binlog enabled,
                         (slave) IO tread is running, SQL thread is running,
                         no errors, slave delay < max_delay,
                         read log pos + max_position < master's log position
                         Note: Will show 'ERROR' if there are multiple
                         errors encountered otherwise will display the
                         health check that failed.
        
        If verbosity is set, it will show the following additional information.
        
          (master)
            - server version, binary log file, position
           
          (slaves)
            - server version, master's binary log file, master's log position,
              IO_Thread, SQL_Thread, Secs_Behind, Remaining_Delay,
              IO_Error_Num, IO_Error
              
        Returns tuple - (columns, rows) 
        """    
        assert (self.master is not None), "No master or connection failed."

        # Get master health
        rpl_health = self.master.check_rpl_health()
        self._report("# Getting health for master: %s:%s." %
                     (self.master.host, self.master.port), logging.INFO, False)
        have_gtid = self.master.supports_gtid()
        rows = []
        master_data = [
            self.master.host,
            self.master.port,
            "MASTER",
            get_server_state(self.master, self.master.host, self.pingtime,
                             self.verbosity > 0),
            have_gtid,
            "OK" if rpl_health[0] else ", ".join(rpl_health[1]),
        ]
    
        m_status = self.master.get_status()
        if len(m_status):
            master_log, master_log_pos = m_status[0][0:2]
        else:
            master_log = None
            master_log_pos = 0
        
        columns = []
        columns.extend(_HEALTH_COLS)
        # Show additional details if verbosity turned on
        if self.verbosity > 0:
            columns.extend(_HEALTH_DETAIL_COLS)
            master_data.extend([self.master.get_version(), master_log,
                                master_log_pos, "","","","","","","","",""])
    
        rows.append(master_data)
        
        # Get the health of the slaves
        if have_gtid == "ON":
            master_gtids = self.master.exec_query(_GTID_DONE)
        for slave_dict in self.slaves:
            host = slave_dict['host']
            port = slave_dict['port']
            slave = slave_dict['instance']
            if slave is None or \
               (slave is not None and (not slave.is_alive() or \
               not slave.is_connected_to_master(self.master.host,
                                                self.master.port))):
                rpl_health = (False, ["Cannot connect to slave."])
                slave = None
            if slave is not None:
                rpl_health = slave.check_rpl_health(self.master,
                                                    master_log, master_log_pos,
                                                    self.max_delay, self.max_pos,
                                                    self.verbosity)
                
                # Now, see if filters are in compliance
                if not self._check_filters(self.master, slave):
                    if rpl_health[0]:
                        errors = rpl_health[1]
                        errors.append("Binary log and Relay log filters differ.")
                        rpl_health = (False, errors)
            
            slave_data = [
                host,
                port,
                "SLAVE",
                get_server_state(slave, host, self.pingtime,
                                 self.verbosity > 0),
                " " if slave is None else slave.supports_gtid(),
                "OK" if rpl_health[0] else ", ".join(rpl_health[1]),
            ]
            
            # Show additional details if verbosity turned on
            if self.verbosity > 0:
                if slave is None:
                    slave_data.extend(["","","","","","","","","","","","",""])
                else:
                    slave_data.append(slave.get_version())
                    res = slave.get_rpl_details()
                    if res is not None:
                        slave_data.extend(res)
                        if have_gtid == "ON":
                            gtid_behind = slave.num_gtid_behind(master_gtids)
                            slave_data.extend([gtid_behind])
                        else:
                            slave_data.extend([""])
                    else:
                        slave_data.extend(["","","","","","","","","","","","",""])
                                   
            rows.append(slave_data)
    
        return (columns, rows)
        
        
    def get_server_uuids(self):
        """Return a list of the server's uuids.
        
        Returns list of tuples = (host, port, role, uuid)
        """
        # Get the master's uuid
        uuids = []
        uuids.append((self.master.host, self.master.port, "MASTER",
                      self.master.get_uuid()))
        for slave_dict in self.slaves:
            uuids.append((slave_dict['host'], slave_dict['port'], "SLAVE",
                          slave_dict['instance'].get_uuid()))
        return uuids
    
        
    def get_gtid_data(self):
        """Get the GTID information from the topology
        
        This method retrieves the executed, purged, and owned GTID lists from
        the servers in the topology. It arranges them into three lists and
        includes the host name, port, and role of each server.
        
        Returns tuple - lists for GTID data
        """
        executed = []
        purged = []
        owned = []

        gtid_data = self._get_server_gtid_data(self.master, "MASTER")
        if gtid_data is not None:
            executed.extend(gtid_data[0])
            purged.extend(gtid_data[1])
            owned.extend(gtid_data[2])
    
        for slave_dict in self.slaves:
            slave = slave_dict['instance']
            if slave is not None:
                gtid_data = self._get_server_gtid_data(slave, "SLAVE")
                if gtid_data is not None:
                    executed.extend(gtid_data[0])
                    purged.extend(gtid_data[1])
                    owned.extend(gtid_data[2])

        return (executed, purged, owned)
        
    
    def check_privileges(self, failover=False):
        """Check privileges for the master and all known servers
        
        failover[in]   if True, check permissions for switchover and
                       failover commands. Default is False.
        
        Returns list - [(user, host)] if not enough permissions,
                       [] if no errors
        """
        from mysql.utilities.common.user import User
        
        servers = []
        errors = []

        # Collect all users first.
        if self.master is not None:
            servers.append(self.master)
            for slave_conn in self.slaves:
                slave = slave_conn['instance']
                servers.append(slave)

        # If candidates were specified, check those too.
        candidates = self.options.get("candidates", None)
        candidate_slaves = []
        if candidates:
            self._report("# Checking privileges on candidates.")
            for candidate in candidates:
                slave_dict = self.connect_candidate(candidate, False)
                slave = slave_dict['instance']
                if slave is not None:
                    servers.append(slave)
                    candidate_slaves.append(slave)
            
        for server in servers:
            user_inst = User(server, "%s@%s" % (server.user, server.host))
            if not failover:
                if not user_inst.has_privilege("*", "*", "SUPER"):
                    errors.append((server.user, server.host))
            else:
                if not user_inst.has_privilege("*", "*", "SUPER") or \
                   not user_inst.has_privilege("*", "*", "GRANT") or \
                   not user_inst.has_privilege("*", "*", "REPLICATION SLAVE"):
                    errors.append((server.user, server.host))

        # Disconnect if we connected to any candidates
        for slave in candidate_slaves:
            slave.disconnect()

        return errors

    
    def run_cmd_on_slaves(self, command, quiet=False):
        """Run a command on a list of slaves.
        
        This method will run one of the following slave commands.
        
          start - START SLAVE;
          stop  - STOP SLAVE;
          reset - STOP SLAVE; RESET SLAVE;
    
        command[in]        command to execute
        quiet[in]          If True, do not print messges
                           Default is False
        """
        
        assert (self.slaves is not None), \
               "No slaves specified or connections failed."
        
        self._report("# Performing %s on all slaves." %
                     command.upper())
        i = 0
        for slave_dict in self.slaves:
            hostport = "%s:%s" % (slave_dict['host'], slave_dict['port'])
            msg = "#   Executing %s on slave %s " % (command, hostport)
            slave = slave_dict['instance']
            # skip dead or zombie slaves
            if slave is None or not slave.is_alive():
                self._report(msg + "WARN - cannot connect to slave",
                             logging.WARN)
            elif command == 'reset':
                res = slave.reset()
                if res is None or res != () and not quiet:
                    self._report(msg + "WARN - slave failed to reset",
                                 logging.WARN)
                elif not quiet:
                    self._report(msg + "Ok")
            elif command == 'start':
                res = slave.start()
                if res is None or res != () and not quiet:
                    self._report(msg + "WARN - slave failed to start",
                                 logging.WARN)
                elif not quiet:
                    self._report(msg + "Ok")
            elif command == 'stop':
                res = slave.stop()
                if res is None or res != () and not quiet:
                    self._report(msg + "WARN - slave failed to stop",
                                 logging.WARN)
                elif not quiet:
                    self._report(msg + "Ok")
            i += 1
            
            
    def connect_candidate(self, candidate, master=True):
        """Parse and connect to the candidate
        
        This method parses the candidate string and returns a slave dictionary
        if master=False else returns a Master class instance.
        
        candidate[in]  candidate connection string
        master[in]     if True, make Master class instance
        
        Returns slave_dict or Master class instance
        """
        # Need instance of Master class for operation
        conn_dict = {
            'conn_info' : candidate,
            'quiet'     : True,
            'verbose'   : self.verbose,
        }
        if master:
            m_candidate = Master(conn_dict)
            m_candidate.connect()
            return m_candidate
        else:
            s_candidate = Slave(conn_dict)
            s_candidate.connect()
            slave_dict = {
                'host'     : s_candidate.host,
                'port'     : s_candidate.port,
                'instance' : s_candidate,
            }
            return slave_dict


    def switchover(self, candidate):
        """Perform switchover from master to candidate slave.

        This method switches the role of master to a candidate slave. The
        candidate is checked for viability before the switch is made.
        
        If the user specified --demote-master, the method will make the old
        master a slave of the candidate.
        
        candidate[in]  the connection information for the --candidate option
        
        Return bool - True = success, raises exception on error
        """
        from mysql.utilities.common.server import get_connection_dictionary

        # Need instance of Master class for operation
        m_candidate = self.connect_candidate(candidate)

        # Switchover needs to succeed and prerequisites must be met else abort.
        self._report("# Checking candidate slave prerequisites.")
        try:
            self._check_switchover_prerequisites(m_candidate)
        except UtilError, e:
            self._report("ERROR: %s" % e.errmsg, logging.ERROR)
            # If user wants to force the issue, we do so.
            if not self.force:
                return

        user, passwd = self._get_rpl_user(m_candidate)
        # Create user on m_candidate.
        if passwd:
            rpl_user = "%s:%s" % (user, passwd)
        else:
            rpl_user = user
        if self.verbose:
            self._report("# Creating replication user if it does not exist.")
        res = m_candidate.create_rpl_user(rpl_user, m_candidate.host,
                                           m_candidate.port)

        # Call exec_before script - display output if verbose on
        self.run_script(self.before_script, False)
        
        if self.verbose:
            self._report("# Blocking writes on master.")
        lock_options = {
            'locking'   : 'flush',
            'verbosity' : 3 if self.verbose else self.verbosity,
            'silent'    : self.quiet,
            'rpl_mode'  : "master",
        }
        lock_ftwrl = Lock(self.master, [], lock_options)
        self.master.set_read_only(True)
        
        # Wait for all slaves to catch up.
        gtid_enabled = self.master.supports_gtid() == "ON"
        if gtid_enabled:
            master_gtid = self.master.exec_query(_GTID_DONE)
        self._report("# Waiting for slaves to catch up to old master.")
        for slave_dict in self.slaves:
            master_info = self.master.get_status()[0]
            slave = slave_dict['instance']
            # skip dead or zombie slaves
            if slave is None or not slave.is_alive():
                continue
            if gtid_enabled:
                res = slave.wait_for_slave_gtid(master_gtid, self.timeout,
                                                self.verbose and not self.quiet)
            else:
                res = slave.wait_for_slave(master_info[0], master_info[1],
                                           self.timeout)
            if not res:
                msg = "Slave %s:%s did not catch up to the master." % \
                      (slave_dict['host'], slave_dict['port'])
                if not self.force:
                    self._report(msg, logging.CRITICAL)
                    raise UtilRplError(msg)
                else:
                    self._report("# %s" % msg)
        
        # Stop all slaves
        self._report("# Stopping slaves.")
        self.run_cmd_on_slaves("stop", not self.verbose)

        # Unblock master
        self.master.set_read_only(False)
        lock_ftwrl.unlock()
        
        # Make master a slave (if specified)
        if self.options.get("demote", False):
            self._report("# Demoting old master to be a slave to the "
                         "new master.")
            slave = self._change_role(self.master)
            slave.stop()
            slave_dict = {
              'host'     : self.master.host,  # host name for slave
              'port'     : self.master.port,  # port for slave
              'instance' : slave,             # Slave class instance 
            }
            self.slaves.append(slave_dict)
        
        # Move candidate slave to master position in lists
        self.master_vals = m_candidate.get_connection_values()
        self.master = m_candidate
        
        # Remove slave from list of slaves
        self._remove_slave({'host':m_candidate.host,
                            'port':m_candidate.port,
                            'instance':m_candidate})
        
        # Switch all slaves to new master
        self._report("# Switching slaves to new master.")
        new_master_info = m_candidate.get_status()[0]
        master_values = {
            'Master_Host'         : m_candidate.host,
            'Master_Port'         : m_candidate.port,
            'Master_User'         : user,
            'Master_Password'     : passwd,
            'Master_Log_File'     : new_master_info[0],
            'Read_Master_Log_Pos' : new_master_info[1],
        }
        for slave_dict in self.slaves:
            if self.verbose:
                self._report("# Executing CHANGE MASTER on %s:%s." % 
                             (slave_dict['host'], slave_dict['port']))
            slave = slave_dict['instance']
            # skip dead or zombie slaves
            if slave is None or not slave.is_alive():
                continue
            change_master = slave.make_change_master(False, master_values)
            if self.verbose:
                self._report("# %s" % change_master)
            slave.exec_query(change_master)
        
        # Start all slaves
        self._report("# Starting all slaves.")
        self.run_cmd_on_slaves("start", not self.verbose)
        
        # Call exec_after script - display output if verbose on
        self.run_script(self.after_script, False)
    
        # Check all slaves for status, errors
        self._report("# Checking slaves for errors.")
        if not self._check_all_slaves(self.master):
            return False
        
        self._report("# Switchover complete.")
        
        return True
    
    
    def _change_role(self, server, slave=True):
        """Reverse role of Master and Slave classes
        
        This method can be used to get a Slave instance from a Master instance
        or a Master instance from a Slave instance.
        
        server[in]     Server class instance
        slave[in]      if True, create Slave class instance
                       Default is True

        Return Slave or Master instance
        """
        from mysql.utilities.common.server import get_connection_dictionary

        conn_dict = {
            'conn_info' : get_connection_dictionary(server),
            'verbose'   : self.verbose,
        }
        if slave and type(server) != Slave:
            slave_conn = Slave(conn_dict)
            slave_conn.connect()
            return slave_conn
        if not slave and type(server) != Master:
            master_conn = Master(conn_dict)
            master_conn.connect()
            return master_conn
        return server        
    
    
    def find_best_slave(self, candidates=None, check_master=True,
                        strict=False):
        """Find the best slave
        
        This method checks each slave in the topology to determine if
        it is a viable slave for promotion. It returns the first slave
        that is determined to be eligible for promotion.
        
        The method uses the order of the slaves in the topology as
        specified by the slaves list to search for a best slave. If a
        candidate slave is provided, it is checked first.
        
        candidates[in]   list of candidate connection dictionaries
        check_master[in] if True, check that slave is connected to the master
                         Default is True
        strict[in]       if True, use only the candidate list for slave
                         election and fail if no candidates are viable.
                         Default = False
                         
        Returns dictionary = (host, port, instance) for 'best' slave,
                             None = no candidate slaves found
        """
        msg = "None of the candidates was the best slave."
        for candidate in candidates:
            slave_dict = self.connect_candidate(candidate, False)
            slave = slave_dict['instance']
            # Ignore dead or offline slaves
            if slave is None or not slave.is_alive():
                continue
            slave_ok = self._check_candidate_eligibility(slave.host, slave.port,
                                                         slave, check_master)
            if slave_ok is not None and slave_ok[0]:
                return slave_dict
            
        # If strict is on and we have found no viable candidates, return None
        if strict:
            self._report("ERROR: %s" % msg, logging.ERROR)
            return None
            
        if candidates is not None and len(candidates) > 0:
            self._report("WARNING: %s" % msg, logging.WARN)
            
        for slave_dict in self.slaves:
            s_host = slave_dict['host']
            s_port = slave_dict['port']
            slave = slave_dict['instance']
            # skip dead or zombie slaves
            if slave is None or not slave.is_alive():
                continue
            # Check eligibility
            try:
                slave_ok = self._check_candidate_eligibility(s_host, s_port,
                                                             slave,
                                                             check_master)
                if slave_ok is not None and slave_ok[0]:
                    return slave_dict
            except:
                pass # Slave gone away, skip it.
            
        return None


    def failover(self, candidates, strict=False):
        """Perform failover to best slave in a GTID-enabled topology.
        
        This method performs a failover to one of the candidates specified. If
        no candidates are specified, the method will use the list of slaves to
        choose a candidate. In either case, priority is given to the server
        listed first that meets the prerequisites - a sanity check to ensure if
        the candidate's GTID_MODE matches the other slaves.
        
        In the event the candidates list is exhausted, it will use the slaves
        list to find a candidate. If no servers are viable, the method aborts.
        
        If the strict parameter is True, the search is limited to the
        candidates list.

        Once a candidate is selected, the candidate is prepared to become the
        new master by collecting any missing GTIDs by being made a slave to
        each of the other slaves.
        
        Once prepared, the before script is run to trigger applications,
        then all slaves are connected to the new master. Once complete,
        all slaves are started, the after script is run to trigger
        applications, and the slaves are checked for errors.

        candidates[in] list of slave connection dictionary of candidate
        strict[in]     if True, use only the candidate list for slave
                       election and fail if no candidates are viable.
                       Default = False
                       
        Returns bool - True if successful,
                       raises exception if failure and forst is False
        """
        from mysql.utilities.common.server import get_connection_dictionary

        # Get best slave from list of candidates
        new_master_dict = self.find_best_slave(candidates, False, strict)
        if new_master_dict is None:
            msg = "No candidate found for failover."
            self._report(msg, logging.CRITICAL)
            raise UtilRplError(msg)
            
        new_master = new_master_dict['instance']
        # All servers must have GTIDs match candidate
        gtid_mode = new_master.supports_gtid()
        if gtid_mode != "ON":
            msg = "Failover requires all servers support " + \
                   "global transaction ids and have GTID_MODE=ON"
            self._report(msg, logging.CRITICAL)
            raise UtilRplError(msg)

        for slave_dict in self.slaves:
            # Ignore dead or offline slaves
            slave = slave_dict['instance']
            # skip dead or zombie slaves
            if slave is None or not slave.is_alive():
                continue
            if slave.supports_gtid() != gtid_mode:
                msg = "Cannot perform failover unless all " + \
                      "slaves support GTIDs and GTID_MODE=ON"
                self._report(msg, logging.CRITICAL)
                raise UtilRplError(msg)

        host = new_master_dict['host']
        port = new_master_dict['port']
        self._report("# Candidate slave %s:%s will become the new master." % 
                     (host, port))
        
        user, passwd = self._get_rpl_user(self._change_role(new_master))

        # Prepare candidate
        self._report("# Preparing candidate for failover.")
        self._prepare_candidate_for_failover(new_master, user, passwd)

        # Create replication user on candidate.
        if passwd:
            rpl_user = "%s:%s" % (user, passwd)
        else:
            rpl_user = user
        self._report("# Creating replication user if it does not exist.")
            
        # Need Master class instance to check master and replication user
        self.master = self._change_role(new_master, False)
        res = self.master.create_rpl_user(rpl_user, host, port)

        # Call exec_before script - display output if verbose on
        self.run_script(self.before_script, False)

        # Stop all slaves
        self._report("# Stopping slaves.")
        self.run_cmd_on_slaves("stop", not self.verbose)

        self._report("# Switching slaves to new master.")
        for slave_dict in self.slaves:
            slave = slave_dict['instance']
            # skip dead or zombie slaves
            if slave is None or not slave.is_alive():
                continue
            slave.switch_master(self.master, user, passwd, False, None, None,
                                self.verbose and not self.quiet)

        # Take the server out of the list.
        self._remove_slave(new_master_dict)

        # Starting all slaves
        self._report("# Starting slaves.")
        self.run_cmd_on_slaves("start", not self.verbose)

        # Call exec_after script - display output if verbose on
        self.run_script(self.after_script, False)

        # Check slaves for errors
        self._report("# Checking slaves for errors.")
        if not self._check_all_slaves(self.master):
            return False

        self._report("# Failover complete.")

        return True
    
    
