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
import os
import mutlib
import replicate
from mysql.utilities.exception import MUTLibError, UtilDBError

_MASTER_DB_CMDS = [
    "DROP DATABASE IF EXISTS master_db1",
    "CREATE DATABASE master_db1",
    "CREATE TABLE master_db1.t1 (a int)",
    "INSERT INTO master_db1.t1 VALUES (1), (2), (3)",
]

_TEST_CASE_RESULTS = [
    # util result, db check results before, db check results after as follows:
    # BEFORE:
    #   SHOW DATABASES LIKE 'util_test'
    #   SELECT COUNT(*) FROM util_test.t1
    #   SHOW DATABASES LIKE 'master_db1'
    #   SELECT COUNT(*) FROM master_db1.t1
    # AFTER:
    #   SHOW DATABASES LIKE 'util_test'
    #   SELECT COUNT(*) FROM util_test.t1
    #   SHOW DATABASES LIKE 'master_db1'
    #   SELECT COUNT(*) FROM master_db1.t1
    #   <insert 2 rows into master_db1.t1>
    #   SELECT COUNT(*) FROM master_db1.t1
    [0, 'util_test', '7', None, False, 'util_test', '7', 'master_db1', '3', '5'],
    [0, None, False, None, False, 'util_test', '7', 'master_db1', '5', '7'],
    [0, None, False, None, False, 'util_test', '7', 'master_db1', '7', '9'],
]

_MAX_ATTEMPTS = 10   # Max tries to wait for slave before failing.

class test(replicate.test):
    """test mysqldbcopy replication features
    This test executes the replication feature in mysqldbcopy to sync a slave
    and to test provisioning a slave from either a master or a slave. It uses
    the replicate test as a parent for testing methods.
    """
    
    # Test Cases:
    #    - copy extra db on master
    #    - provision a new slave from master
    #    - provision a new slave from existing slave
        
    def check_prerequisites(self):
        if self.servers.get_server(0).check_version_compat(5, 6, 5):
            raise MUTLibError("Test requires server version prior to 5.6.5")
        # Need at least one server.
        self.server1 = None
        self.server2 = None
        self.need_server = False
        if not self.check_num_servers(3):
            self.need_server = True
        return self.check_num_servers(1)
        
    def setup(self):
        self.res_fname = "result.txt"
        result = replicate.test.setup(self)

        # Note: server1 is master, server2, server3 are slaves.
        #       server3 is a new slave with nothing on it.
        
        index = self.servers.find_server_by_name("new_slave")
        if index >= 0:
            self.server3 = self.servers.get_server(index)
            try:
                res = self.server3.show_server_variable("server_id")
            except MUTLibError, e:
                raise MUTLibError("Cannot get new replication slave " +
                                   "server_id: %s" % e.errmsg)
            self.s3_serverid = int(res[0][1])
        else:
            self.s3_serverid = self.servers.get_next_id()
            res = self.servers.spawn_new_server(self.server0, self.s3_serverid,
                                               "new_slave")
            if not res:
                raise MUTLibError("Cannot spawn new replication slave server.")
            self.server3 = res[0]
            self.servers.add_new_server(self.server3, True)

        self._drop_all()

        self.server1.exec_query("STOP SLAVE")
        self.server1.exec_query("RESET SLAVE")
        self.server2.exec_query("STOP SLAVE")
        self.server2.exec_query("RESET SLAVE")
        try:
            for cmd in _MASTER_DB_CMDS:
                self.server1.exec_query(cmd)
        except MUTLibError, e:
            raise MUTLibError(e.errmsg)

        data_file = os.path.normpath("./std_data/basic_data.sql")
        try:
            res = self.server1.read_and_exec_SQL(data_file, self.debug)
            res = self.server2.read_and_exec_SQL(data_file, self.debug)
        except MUTLibError, e:
            raise MUTLibError("Failed to read commands from file %s: " % \
                               data_file + e.errmsg)

        master_str = "--master=%s" % self.build_connection_string(self.server1)
        slave_str = " --slave=%s" % self.build_connection_string(self.server2)
        conn_str = master_str + slave_str
        
        cmd = "mysqlreplicate.py --rpl-user=rpl:rpl %s" % conn_str
        try:
            res = self.exec_util(cmd, self.res_fname)
        except MUTLibError, e:
            raise MUTLibError(e.errmsg)

        return result
    
    def wait_for_slave(self, slave, attempts):
        # Wait for slave to read the master log file
        i = 0
        while i < attempts:
            if self.debug:
                print ".",
            res = slave.exec_query("SHOW SLAVE STATUS")
            if res and res[0][0] == 'Waiting for master to send event':
                break
            i += 1
            if i == attempts:
                raise MUTLibError("Slave did not sync with master.")
        return
    
    def _check_result(self, server, query):
        # Returns first query result, None if no result, False if error
        try:
            res = server.exec_query(query)
            if res:
                return res[0][0]
            else:
                return None
        except:
            return False

    def run_test_case(self, actual_result, test_num, master, source,
                      destination, cmd_list, db_list, cmd_opts, comment,
                      expected_results, restart_replication=False,
                      skip_wait=False):
        
        results = []
        results.append(comment)
        
        # Drop all databases and reestablish replication
        if restart_replication:
            destination.exec_query("STOP SLAVE")
            destination.exec_query("RESET SLAVE")
            for db in db_list:
                self.drop_db(destination, db)
            master_str = "--master=%s" % self.build_connection_string(master)
            slave_str = " --slave=%s" % self.build_connection_string(destination)
            conn_str = master_str + slave_str
            
            cmd = "mysqlreplicate.py --rpl-user=rpl:rpl %s" % conn_str
            try:
                res = self.exec_util(cmd, self.res_fname)
            except MUTLibError, e:
                raise MUTLibError(e.errmsg)
        
        # Check databases on slave and save results for 'BEFORE' check
        results.append(self._check_result(destination, "SHOW DATABASES LIKE 'util_test'"))
        results.append(self._check_result(destination, "SELECT COUNT(*) FROM util_test.t1"))
        results.append(self._check_result(destination, "SHOW DATABASES LIKE 'master_db1'"))
        results.append(self._check_result(destination, "SELECT COUNT(*) FROM master_db1.t1"))

        # Run the commands
        for cmd_str in cmd_list:    
            try:
                res = self.exec_util(cmd_str + cmd_opts, self.res_fname)
                results.insert(1, res)  # save result at front of list
                if res != actual_result:
                    return False
            except MUTLibError, e:
                raise MUTLibError(e.errmsg)

        # Wait for slave to catch up
        if not skip_wait:
            if self.debug:
                print "# Waiting for slave to sync",
            try:
                self.wait_for_slave(destination, _MAX_ATTEMPTS)
            except MUTLibError, e:
                raise MUTLibError(e.errmsg)
            if self.debug:
                print "done."

        # Check databases on slave and save results for 'AFTER' check
        results.append(self._check_result(destination, "SHOW DATABASES LIKE 'util_test'"))
        results.append(self._check_result(destination, "SELECT COUNT(*) FROM util_test.t1"))
        results.append(self._check_result(destination, "SHOW DATABASES LIKE 'master_db1'"))
        results.append(self._check_result(destination, "SELECT COUNT(*) FROM master_db1.t1"))
        
        # Add something to master and check slave
        res = master.exec_query("INSERT INTO master_db1.t1 VALUES (10), (11)")
        # Wait for slave to catch up
        if not skip_wait:
            if self.debug:
                print "# Waiting for slave to sync",
            try:
                self.wait_for_slave(destination, _MAX_ATTEMPTS)
            except MUTLibError, e:
                raise MUTLibError(e.errmsg)
            if self.debug:
                print "done."

        results.append(self._check_result(destination, "SELECT COUNT(*) FROM master_db1.t1"))
        
        if self.debug:
            print comment
            print "Expected Results:", expected_results[test_num-1]
            print "  Actual Results:", results[1:]
        
        self.results.append(results)
        
        return True
    
    def run(self):
        from_conn = "--source=" + self.build_connection_string(self.server1)
        to_conn = "--destination=" + self.build_connection_string(self.server2)
        db_list = ["master_db1"]

        cmd_str = "mysqldbcopy.py %s --rpl-user=rpl:rpl --skip-gtid " % " ".join(db_list) + \
                  "%s %s " % (from_conn, to_conn)

        # Copy master database
        test_num = 1
        comment = "Test case %s - Copy extra database from master to slave" % \
                  test_num
        cmd_opts = "--rpl=master "
        res = self.run_test_case(0, test_num, self.server1, self.server1,
                                 self.server2, [cmd_str], db_list,
                                 cmd_opts, comment, _TEST_CASE_RESULTS, False)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        test_num += 1

        to_conn = "--destination=" + self.build_connection_string(self.server3)
        db_list = ["util_test", "master_db1"]

        cmd_str = "mysqldbcopy.py %s --rpl-user=rpl:rpl --skip-gtid " % " ".join(db_list) + \
                  "%s %s " % (from_conn, to_conn)

        # Provision a new slave from master
        comment = "Test case %s - Provision a new slave from the master" % \
                  test_num
        cmd_opts = "--rpl=master "
        res = self.run_test_case(0, test_num, self.server1, self.server1,
                                 self.server3, [cmd_str], db_list,
                                 cmd_opts, comment, _TEST_CASE_RESULTS, True)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        test_num += 1
        
        from_conn = "--source=" + self.build_connection_string(self.server2)
        to_conn = "--destination=" + self.build_connection_string(self.server3)

        cmd_str = "mysqldbcopy.py %s --rpl-user=rpl:rpl --skip-gtid " % " ".join(db_list) + \
                  "%s %s " % (from_conn, to_conn)

        # Provision a new slave from existing slave
        comment = "Test case %s - Provision a new slave from existing slave" % \
                  test_num
        cmd_opts = "--rpl=slave "
        res = self.run_test_case(0, test_num, self.server1, self.server2,
                                 self.server3, [cmd_str], db_list,
                                 cmd_opts, comment, _TEST_CASE_RESULTS, True)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        test_num += 1

        return True
          
    def get_result(self):
        # Here we check the result from execution of each test case.
        for i in range(0,len(_TEST_CASE_RESULTS)):
            if self.debug:
                print self.results[i][0]
                print "  Actual results:", self.results[i][1:]
                print "Expected results:", _TEST_CASE_RESULTS[i]
            if self.results[i][1:] != _TEST_CASE_RESULTS[i]:
                msg = "\n%s\nExpected result = " % self.results[i][0]+ \
                      "%s\n  Actual result = %s\n" % (self.results[i][1:],
                                                     _TEST_CASE_RESULTS[i])
                return (False, msg)
            
        return (True, '')
    
    def record(self):
        return True # Not a comparative test
    
    def drop_db(self, server, db):
        # Check before you drop to avoid warning
        try:
            res = server.exec_query("DROP DATABASE `%s`" % db)
        except:
            return False
        return True
    
    def _drop_all(self):
        self.drop_db(self.server1, "util_test")
        self.drop_db(self.server1, "master_db1")
        self.drop_db(self.server2, "util_test")
        self.drop_db(self.server2, "master_db1")
        self.drop_db(self.server3, "util_test")
        self.drop_db(self.server3, "master_db1")
        return True

    def cleanup(self):
        if self.res_fname:
            os.unlink(self.res_fname)
        self._drop_all()
        return True
