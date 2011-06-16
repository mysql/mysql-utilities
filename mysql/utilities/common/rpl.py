#
# Copyright (c) 2010, 2011 Oracle and/or its affiliates. All rights reserved.
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
import re
import sys
import time
from mysql.utilities.exception import MySQLUtilError

# List of database objects for enumeration
DATABASE, TABLE, VIEW, TRIGGER, PROC, FUNC, EVENT, GRANT = "DATABASE", \
    "TABLE", "VIEW", "TRIGGER", "PROCEDURE", "FUNCTION", "EVENT", "GRANT"

_MINFO_COL = [
    'Master_Log_File', 'Read_Master_Log_Pos', 'Master_Host', 'Master_User',
    'Master_Password', 'Master_Port', 'Connect_Retry', 'Master_SSL_Allowed',
    'Master_SSL_CA_File', 'Master_SSL_CA_Path', 'Master_SSL_Cert',
    'Master_SSL_Cipher', 'Master_SSL_Key', 'Master_SSL_Verify_Server_Cert'
]

_PRINT_WIDTH = 75    

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


class Replication(object):
    """
    The Replication class can be used to establish a replication connection
    between a master and a slave with the following utilities:
    
        - Test prerequisites for replication
        
    Replication prerequisite tests shall be constructed so that they return
    None if the check passes (no errors) or a list of strings containing the
    errors or warnings. They shall accept a dictionary of options set to
    options={}. This will allow for reduced code needed to call multiple tests.
    """   
    
    def __init__(self, master, slave, verbose=False):
        """Constructor
        
        master[in]         Master Server object
        slave[in]          Slave Server object
        verbose[in]        print extra data during operations (optional)
                           default value = False
        """
        self.verbose = verbose
        self.master = master
        self.slave = slave
        self.master_server_id = None
        self.slave_server_id = None
        self.master_lctn = None
        self.slave_lctn = None
        self.replicating = False
        
        
    def get_lctn_values(self):
        """Get lower_case_table_name setting for master and slave.
        
        Returns tuple containing master and slave lctn values
        """
        if self.slave_lctn is None:
            res = self.slave.show_server_variable("lower_case_table_names")
            if res != []:
                self.slave_lctn = res[0][1]
        if self.master_lctn is None:
            res = self.master.show_server_variable("lower_case_table_names")
            if res != []:
                self.master_lctn = res[0][1]

        return (self.master_lctn, self.slave_lctn)
        
        
    def get_server_ids(self):
        """Get server_d setting for master and slave.
        
        Returns tuple containing master and slave server_id values
        """
        # Get server_id from Master
        if self.master_server_id is None:
            try:
                res = self.master.show_server_variable("server_id")
            except:
                raise MySQLUtilError("Cannot retrieve server id from master.")
            
            self.master_server_id = int(res[0][1])
            
        # Get server_id from Slave
        if self.slave_server_id is None:
            try:
                res = self.slave.show_server_variable("server_id")
            except:
                raise MySQLUtilError("Cannot retrieve server id from slave.")
                
            self.slave_server_id = int(res[0][1])

        return (self.master_server_id, self.slave_server_id)

    
    def get_master_info(self, filename):
        """Return the contents of the master.info file.
        
        This method will raise an error if the file is missing or cannot be
        read by the user.
        
        filename[in]  path to master information file

        Returns dictionary - values in master.info 
        """
        contents = {}
        
        res = self.slave.show_server_variable('datadir')
        if res is None or res == []:
            raise MySQLUtilError("Cannot get datadir.")
        datadir = res[0][1]
        if filename == 'master.info':
            filename = os.path.join(datadir, filename)

        if os.path.exists(filename):
            mfile = open(filename, 'r')
            num = int(mfile.readline())
            # Protect overrun of array if master_info file length is
            # changed (more values added).
            if num > len(_MINFO_COL):
                num = len(_MINFO_COL)
            for i in range(1,num):
                contents[_MINFO_COL[i-1]] = mfile.readline().strip('\n')
            mfile.close()
        else:
            raise MySQLUtilError("Cannot read master information file: "
                                 "%s." % filename)

        return contents
        
        
    def show_master_info(self, options):
        """Display the contents of the master information file.
        
        options[in]   dictionary of options (verbose, pedantic)
        """
        
        filename = options.get("master_info", 'master.info')
        res = self.slave.show_server_variable('datadir')
        if res is None or res == []:
            raise MySQLUtilError("Cannot get datadir.")
        datadir = res[0][1]
        if filename == 'master.info':
            filename = os.path.join(datadir, filename)

        contents = self.get_master_info(filename)
        stop = len(contents)
        for i in range(0,stop):
            print "{0:>30} : {1}".format(_MINFO_COL[i],
                                         contents[_MINFO_COL[i]])
        
    
    def show_slave_status(self):
        """Display the slave status from the slave server
        """
        res = self.slave.exec_query("SHOW SLAVE STATUS", (), True)
        if res != [] and res[1] != []:
            stop = len(res[0])
            cols = res[0]
            rows = res[1]
            for i in range(0,stop):
                print "{0:>30} : {1}".format(cols[i], rows[0][i])
        else:
            raise MySQLUtilError("Cannot get slave status or slave is "
                                 "not configured as a slave or not "
                                 "started.")
        
        
    def check_server_ids(self):
        """Check server ids on master and slave
        
        This method will check the server ids on the master and slave. It will
        raise exceptions for error conditions.
        
        Returns [] if compatible, list of errors if not compatible
        """
        self.get_server_ids()        
        if self.master_server_id == 0:
            raise MySQLUtilError("Master server_id is set to 0.")
        
        if self.slave_server_id == 0:
            raise MySQLUtilError("Slave server_id is set to 0.")
            
        # Check for server_id uniqueness
        if self.master_server_id == self.slave_server_id:
            raise MySQLUtilError("The slave's server_id is the same as the "
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
                raise MySQLUtilError("Innodb settings differ between master "
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
                raise MySQLUtilError("The master and slave have differing " 
                                     "storage engine configurations!")
    
        return errors


    def check_master_binlog(self):
        """Check prerequisites for master for replication
        
        Returns [] if master ok, list of errors if binary logging turned off.
        """
        errors = []
        res = self.master.show_server_variable("log_bin")
        if not res:
            return (["Cannot retrieve status of log_bin variable."])
        log_bin = res[0][1]
        if log_bin == "OFF" or log_bin == "0":
            errors.append("Master must have binary logging turned on.")

        return errors
    
    
    def check_lctn(self):
        """Check lower_case_table_name setting
        
        Returns [] - no exceptions, list if exceptions found
        """
        errors = []
        self.get_lctn_values()
        if self.slave_lctn != self.master_lctn:
            return (self.master_lctn, self.slave_lctn)
        if self.slave_lctn == 1:
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
        res = self.master.exec_query("SHOW MASTER STATUS")
        if res != []:
            if len(res[0][2]) > 0 or len(res[0][3]) > 0:
                rows.append(('master', res[0][2], res[0][3]))
        res = self.slave.exec_query("SHOW SLAVE STATUS")
        if res != []:
            if len(res[0][12]) > 0 or len(res[0][13]) > 0:
                rows.append(('slave', res[0][12], res[0][13]))
        if len(rows) > 0:
            cols = ['server', 'do_db', 'ignore_db']
            binlog_ex = _get_list(rows, cols)

        return binlog_ex


    def check_rpl_user(self):
        """Check replication user exists on master and has the correct
        privileges.
        
        options[in]   dictionary of options (verbose, pedantic)

        Returns [] - no exceptions, list if exceptions found
        """
        
        from mysql.utilities.common.user import User
        
        errors = []
        res = self.slave.exec_query("SHOW SLAVE STATUS")
        if res != []:
            if res[0][2] is None or len(res[0][2]) == 0:
                raise MySQLUtilError("Slave is not connected to a master.")
                
            result = self.master.exec_query("SELECT * FROM mysql.user "
                                            "WHERE user = '%s' AND "
                                            "host = '%s'" %
                                            (res[0][2], res[0][1]))
            if result is None or result == []:
                errors.append("The replication user %s@%s was not found "
                              "on the master." % (res[0][2], res[0][1]))
            else:
                rpl_user = User(self.master,
                                "%s@%s" % (res[0][2], res[0][1]))
                if not rpl_user.has_privilege('*', '*',
                                              'REPLICATION SLAVE'):
                    errors.append("Replication user does not have the "
                                  "correct privilege. She needs "
                                  "'REPLICATION SLAVE' on all replicated "
                                  "databases.")

        return errors


    def check_slave_connection(self):
        """Check to see if slave is connected to master
        
        This method will check the slave specified at instantiation to see if
        it is connected to the master specified. If the slave is connected
        to a different master, an error is returned. It will also raise an
        exception if the slave is stopped or if the server is not setup as a
        slave.

        Returns [] - no exceptions, list if exceptions found
        """
        errors = []
        res = self.slave.exec_query("SHOW SLAVE STATUS")
        if res != []:
            if res[0][0] is None or len(res[0][0]) == 0:
                raise MySQLUtilError("Slave is stopped.")
            m_host = res[0][1]
            m_port = res[0][3]
            m_IO = res[0][10]
            if m_host != self.master.host or \
               int(m_port) != int(self.master.port):
                if m_IO.upper() != "YES":
                    errors.append("Slave is not connected to a master.")
                else:
                    errors.append("Slave is not connected to the master. It "
                                  "is connected to host=%s, port=%s." %
                                  (m_host, m_port))
        else:
            raise MySQLUtilError("The server specified as the slave is "
                                 "not configured as a replication slave.")
        
        return errors
    
    
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
        res = self.master.exec_query("SHOW MASTER STATUS")
        if res != []:
            m_log_file = res[0][0]       # master's binlog file
            m_log_pos = res[0][1]        # master's binlog position
        else:
            raise MySQLUtilError("Cannot read master status.")
        res = self.slave.exec_query("SHOW SLAVE STATUS")
        if res != []:
            if res[0][0] is None or len(res[0][0]) == 0:
                raise MySQLUtilError("Slave is stopped.")
            if res[0][33] is None: # if unknown, return the error
                errors.append("Cannot determine slave delay. Status: UNKNOWN.")
                return errors

            sec_behind = int(res[0][32])  # Seconds behind master
            read_log_file = res[0][5]     # master's log file read
            read_log_pos = res[0][6]      # position in master's binlog
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
                errors.append("Slave is %d seconds behind master." %
                              sec_behind)
        else:
            raise MySQLUtilError("The server specified as the slave is "
                                 "not configured as a replication slave.")
        
        return errors
    
    
    def check_master_info(self, options):
        """Check to see if master info file matches slave status
        
        This method will return a list of discrepancies if the master.info
        file does not match slave status. It will also raise errors if there
        are problem accessing the master.info file.
        
        options[in]   dictionary of options (verbose, pedantic)

        Returns [] - no exceptions, list if exceptions found
        """
        errors = []
        filename = options.get("master_info", "master.info")
        
        res = self.slave.show_server_variable('datadir')
        if res is None or res == []:
            raise MySQLUtilError("Cannot get datadir.")
        datadir = res[0][1]
        if filename == 'master.info':
            filename = os.path.join(datadir, filename)

        master_info = self.get_master_info(filename)
        res = self.slave.exec_query("SHOW SLAVE STATUS")
        if res != []:
            if res[0][0] is None or len(res[0][0]) == 0:
                raise MySQLUtilError("Slave is stopped.")
            m_host = res[0][1]
            m_port = res[0][3]
            rpl_user = res[0][2]
            if m_host != master_info['Master_Host'] or \
               int(m_port) != int(master_info['Master_Port']) or \
               rpl_user != master_info['Master_User']:
                errors.append("Slave is connected to master differently "
                              "than what is recorded in the master "
                              "information file. Master information file "
                              "= user=%s, host=%s, port=%s." %
                              (master_info['Master_User'],
                               master_info['Master_Host'],
                               master_info['Master_Port']))

        return errors

    
    def replicate(self, rpl_user, num_tries):
        """Setup replication among a slave and master.
        
        Note: Must have connected to a master and slave before calling this
        method.

        rpl_user[in]       Replication user in form user:passwd
        num_tries[in]      Number of attempts to wait for slave synch
        
        Returns True if success, False if error
        """
        
        from mysql.utilities.common.user import User

        if self.master is None or self.slave is None:
            print "ERROR: Must connect to master and slave before " \
                  "calling replicate()"
            return False
        
        result = True
        
        # Create user class instance
        user = User(self.master,
                    "%s@%s:%s" % (rpl_user, self.master.host, self.master.port),
                    self.verbose)

        r_user, r_pass = re.match("(\w+)(?:\:(\w+))?", rpl_user).groups()
        
        # Check to see if rpl_user is present, else create her
        if not user.exists():
            if self.verbose:
                print "# Creating replication user..."
            user.create()
        
        # Check to see if rpl_user has the correct grants, else grant rights
        if not user.has_privilege("*", "*", "REPLICATION SLAVE"):
            if self.verbose:
                print "# Granting replication access to replication user..."
            query_str = "GRANT REPLICATION SLAVE ON *.* TO '%s'@'%s' " % \
                        (r_user, self.slave.host)
            if r_pass:
                query_str += "IDENTIFIED BY '%s'" % r_pass
            try:
                self.master.exec_query(query_str, (), False, False)
            except:
                print "ERROR: Cannot grant replication slave to " + \
                      "replication user."
                return False

        # Flush tables on master
        if self.verbose:
            print "# Flushing tables on master with read lock..."
        res = self.master.exec_query("FLUSH TABLES WITH READ LOCK",
                                     (), False, False)
        
        # Read master log file information
        res = self.master.exec_query("SHOW MASTER STATUS")
        if not res:
            print "ERROR: Cannot retrieve master status."
            exit(1)
            
        master_file = res[0][0]
        master_pos = res[0][1]
         
        # Stop slave first
        res = self.slave.exec_query("SHOW SLAVE STATUS")
        if res != () and res != []:
            if res[0][10] == "Yes" or res[0][11] == "Yes":
                res = self.slave.exec_query("STOP SLAVE", (), False, False)
        
        # Connect slave to master
        if self.verbose:
            print "# Connecting slave to master..."
        change_master = "CHANGE MASTER TO MASTER_HOST = '%s', " % \
                        self.master.host
        change_master += "MASTER_USER = '%s', " % r_user
        change_master += "MASTER_PASSWORD = '%s', " % r_pass
        change_master += "MASTER_PORT = %s, " % self.master.port
        change_master += "MASTER_LOG_FILE = '%s', " % master_file
        change_master += "MASTER_LOG_POS = %s" % master_pos
        res = self.slave.exec_query(change_master, (), False, False)
        if self.verbose:
            print "# %s" % change_master
        
        # Start slave
        if self.verbose:
            print "# Starting slave..."
        res = self.slave.exec_query("START SLAVE", (), False, False)
        
        # Check slave status
        i = 0
        while i < num_tries:
            time.sleep(1)
            res = self.slave.exec_query("SHOW SLAVE STATUS")
            status = res[0][0]
            if self.verbose:
                print "# status: %s" % status
                print "# error: %s:%s" % (res[0][34], res[0][35])
            if status == "Waiting for master to send event":
                break
            if self.verbose:
                print "# Waiting for slave to synchronize with master"
            i += 1
        if i == num_tries:
            print "ERROR: failed to synch slave with master."
            result = False
            
        # unlock tables on master
        if self.verbose:
            print "# Unlocking tables on master..."
        query_str = "UNLOCK TABLES"
        res = self.master.exec_query(query_str, (), False, False)
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
        if self.verbose:
            print "# Creating a test database on master named %s..." % db
        res = self.master.exec_query("CREATE DATABASE %s" % db,
                                     (), False, False)
        i = 0
        while i < num_tries:
            time.sleep (1)
            res = self.slave.exec_query("SHOW DATABASES")
            for row in res:
                if row[0] == db:
                    res = self.master.exec_query("DROP DATABASE %s" % db,
                                                 (), False, False)
                    print "# Success! Replication is running."
                    i = num_tries
                    break
            i += 1
            if i < num_tries and self.verbose:
                print "# Waiting for slave to synchronize with master"
        if i == num_tries:
            print "ERROR: Unable to complete testing."
        

class _TestReplication(object):
    """
    The _TestReplication class can be used to determine if two servers are
    correctly configured for replication.
    
    This class provides a rpl_test() method which can be overridden to
    execute specific tests.
    """
    
    def __init__(self, rpl, options):
        """Constructor

        rpl[in]           replication class instance 
        options[in]       dictionary of options to include width, verbosity,
                          pedantic, quiet
        """
        self.options = options
        self.verbosity = options.get("verbosity", 0)
        self.quiet = options.get("quiet", False)
        self.suppress = options.get("suppress", False)
        self.width = options.get("width", _PRINT_WIDTH)
        self.rpl = rpl
        self.description = ""  # Users must set this.
        self.warning = False


    def report_test(self, description):
        """Print the test category
        
        description[in]   description of test
        """
        self.description = description
        if not self.quiet:
            sys.stdout.write(self.description[0:self.width-9])
            sys.stdout.write(' ' * (self.width-len(self.description)-6))
        sys.stdout.flush()
   

    def report_status(self, state, errors):
        """Print the results of a test.
        
        state[in]         state of the test
        errors[in]        list of errors
        
        Returns bool True if errors detected during epilog reporting.
        """
        if not self.quiet:
            sys.stdout.write("[%s]\n" % state)
        if len(errors) > 0:
            print
            for error in errors:
                print error
            print
        res = False
        if state == "pass": # Only execute epilog if test passes.
            try:
                self.report_epilog()
            except MySQLUtilError, e:
                print "ERROR:", e.errmsg
                res = True
        sys.stdout.flush()
            
        return res


    def rpl_test(self):
        """Execute replication test.
        
        Override this method to provide specific tests for replication.
        """
        pass


    def report_epilog(self):
        """Execute post-test reporting.
        
        Override this method for post-test reporting.
        """
        pass


    def exec_test(self):
        """Execute a test for replication prerequisites
        
        This method will report the test to be run, execute the test, and if
        the result is None, report the test as 'pass' else report the test
        as 'FAIL' and print the error messages. If warning is set, the method will
        report 'WARN' instead of 'FAIL' and print the error messages.
        
        Should the test method raise an error, the status is set to 'FAIL' and
        the exception is reported.
        
        Returns bool  True if test passes, False if warning or failure
        """
        try:
            res = self.rpl_test()
            if res == []:
                return self.report_status("pass", [])
            else:
                if self.warning:
                    if not self.suppress:
                        if not self.quiet:
                            self.report_status("WARN", res)
                        else:
                            print "WARNING:", self.description
                            for error in res:
                                print error
                    elif not self.quiet:
                        self.report_status("WARN", res)
                else:
                    self.report_status("FAIL", res)
                return True
        except MySQLUtilError, e:
            if not self.quiet:
                self.report_status("FAIL", [e.errmsg])
            else:
                print "Test: %s failed. Errors:" % self.description
                for error in [e.errmsg]:
                    print error
            return True


class _TestMasterBinlog(_TestReplication):
    """Test master has binlog enabled.
    """
    
    def rpl_test(self):
        """Execute test.
        """
        # Check master for binary logging
        self.report_test("Checking for binary logging on master")
        return self.rpl.check_master_binlog()

class _TestBinlogExceptions(_TestReplication):
    """Test for binary log exceptions.
    """
    
    def rpl_test(self):
        """Execute test.
        """
        # Check binlog exceptions
        self.warning = True
        self.report_test("Are there binlog exceptions?")
        return self.rpl.get_binlog_exceptions()
    

class _TestRplUser(_TestReplication):
    """Test replication user permissions.
    """
    
    def rpl_test(self):
        """Execute test.
        """
        # Check rpl_user
        self.report_test("Replication user exists?")
        return self.rpl.check_rpl_user()

class _TestServerIds(_TestReplication):
    """Test server ids are different.
    """
    
    def rpl_test(self):
        """Execute test.
        """
        # Check server ids
        self.report_test("Checking server_id values")
        return self.rpl.check_server_ids()
        
    def report_epilog(self):
        """Report server_ids.
        """
        if self.verbosity > 0 and not self.quiet:
            master_id, slave_id = self.rpl.get_server_ids()
            print "\n master id = %s" % master_id
            print "  slave id = %s\n" % slave_id
            

class _TestSlaveConnection(_TestReplication):
    """Test whether slave can connect or is connected to the master.
    """
    
    def rpl_test(self):
        """Execute test.
        """
        # Check slave connection
        self.warning = True
        self.report_test("Is slave connected to master?")
        return self.rpl.check_slave_connection()


class _TestMasterInfo(_TestReplication):
    """Ensure master info file matches slave connection.
    """
    
    def rpl_test(self):
        """Execute test.
        """
        # Check master.info file
        self.warning = True
        self.report_test("Check master information file")
        return self.rpl.check_master_info(self.options)
        
    def report_epilog(self):
        """Report master info contents.
        """
        if self.verbosity > 0 and not self.quiet:
            print "\n#\n# Master information file: \n#" 
            self.rpl.show_master_info(self.options)
            print
            

class _TestInnoDB(_TestReplication):
    """Test InnoDB compatibility.
    """
    
    def rpl_test(self):
        """Execute test.
        """
        # Check InnoDB compatibility
        self.report_test("Checking InnoDB compatibility")
        return self.rpl.check_innodb_compatibility(self.options)


class _TestStorageEngines(_TestReplication):
    """Test storage engines lists such that slave has the same storage engines
    as the master.
    """
    
    def rpl_test(self):
        """Execute test.
        """
        # Checking storage engines
        self.report_test("Checking storage engines compatibility")
        return self.rpl.check_storage_engines(self.options)

class _TestLCTN(_TestReplication):
    """Test the LCTN settings of master and slave.
    """
    
    def rpl_test(self):
        """Execute test.
        """
        # Check lctn
        self.warning = True
        self.report_test("Checking lower_case_table_names settings")
        return self.rpl.check_lctn()
        
    def report_epilog(self):
        """Report lctn settings.
        """
        if self.verbosity > 0 and not self.quiet:
            master_lctn, slave_lctn = self.rpl.get_lctn_values()
            print "\n  Master lower_case_table_names: %s" % master_lctn
            print "   Slave lower_case_table_names: %s\n" % slave_lctn

class _TestSlaveBehindMaster(_TestReplication):
    """Test for slave being behind master.
    """
    
    def rpl_test(self):
        """Execute test.
        """
        # Check slave behind master
        self.report_test("Checking slave delay (seconds behind master)")
        return self.rpl.check_slave_delay()

    
def get_replication_tests(rpl, options):
    """Return list of replication test function pointers.
    
    This list can be used to iterate over the replication tests for ensuring
    a properly configured master and slave topology.
    """
    return [
        _TestMasterBinlog(rpl, options),
        _TestBinlogExceptions(rpl, options),
        _TestRplUser(rpl, options),
        _TestServerIds(rpl, options),
        _TestSlaveConnection(rpl, options),
        _TestMasterInfo(rpl, options),
        _TestInnoDB(rpl, options),
        _TestStorageEngines(rpl, options),
        _TestLCTN(rpl, options),
        _TestSlaveBehindMaster(rpl, options),
    ]
