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
import export_gtid
from mysql.utilities.exception import UtilError, MUTLibError

_DEFAULT_MYSQL_OPTS = '"--log-bin=mysql-bin --skip-slave-start ' + \
                      '--log-slave-updates --gtid-mode=on ' + \
                      '--enforce-gtid-consistency ' + \
                      '--sync-master-info=1 --master-info-repository=table"'

class test(export_gtid.test):
    """check gtid operation for copy utility
    This test executes a series of copy database operations using a variety of
    --skip-gtid and gtid and non-gtid servers. It uses the export_gtid test
    for setup and tear down methods.
    """

    def check_prerequisites(self):
        return export_gtid.test.check_prerequisites(self)

    def setup(self):
        return export_gtid.test.setup(self)
    
    def exec_copy(self, server1, server2, copy_cmd, test_num, test_case,
                  reset=True, load_data=True, ret_val=True):
        conn1 = " --source=" + self.build_connection_string(server1)
        conn2 = " --destination=" + self.build_connection_string(server2)
        if load_data:
            try:
                res = server1.read_and_exec_SQL(self.data_file, self.debug)
            except UtilError, e:
                raise MUTLibError("Failed to read commands from file %s: %s" %
                                  (self.data_file, e.errmsg))

        comment = "Test case %s %s" % (test_num, test_case) 
        cmd_str = copy_cmd + conn1 + conn2
        if reset:
            server2.exec_query("RESET MASTER") # reset GTID_EXECUTED
        res = mutlib.System_test.run_test_case(self, 0, cmd_str, comment)
        if not res == ret_val:
            for row in self.results:
                print row,
            raise MUTLibError("%s: failed" % comment)
            
        self.drop_all()

    def run(self):
        self.res_fname = "result.txt"
        self.data_file = os.path.normpath("./std_data/basic_data.sql")

        copy_cmd_str = "mysqldbcopy.py util_test --quiet "
        
        # Test cases:
        # for each type in [sql, csv, tab, grid, vertical]
        # - gtid -> gtid
        # - gtid -> non-gtid
        # - non-gtid -> gtid
        # Format: server1, server2, test_case (label)
        _TEST_CASES = [
            (self.server1, self.server2, "gtid->gtid"),
            (self.server1, self.server3, "gtid->non_gtid"),
            (self.server3, self.server1, "non_gtid->gtid"),
        ]
        
        test_num = 1
        for test_case in _TEST_CASES:
            self.exec_copy(test_case[0], test_case[1], copy_cmd_str,
                           test_num, test_case[2])
            test_num += 1
                
        # Now do the warnings for GTIDs:
        # - GTIDS but partial backup
        # - GTIDS on but --skip-gtid option present

        self.server1.exec_query("CREATE DATABASE util_test2")
        self.exec_copy(self.server1, self.server2, copy_cmd_str,
                       test_num, "partial backup")
        test_num += 1
        
        self.exec_copy(self.server1, self.server2,
                       copy_cmd_str + " --skip-gtid ",
                       test_num, "skip gtids")
        test_num += 1

        # Now show the error for gtid_executed not empty.
        self.server1.exec_query("RESET MASTER")
        self.server1.exec_query("CREATE DATABASE util_test")
        self.server1.exec_query("CREATE TABLE util_test.t3 (a int)")
        self.server2.exec_query("RESET MASTER")
        self.server2.exec_query("CREATE DATABASE util_test")
        self.exec_copy(self.server1, self.server2,
                       copy_cmd_str + " --force ",
                       test_num, "gtid_executed error",
                       False, False, False)
        test_num += 1
        
        # Show the error for empty GTIDs is fixed.
        self.server1.exec_query("RESET MASTER")
        self.server1.exec_query("CREATE DATABASE util_test")
        self.server1.exec_query("CREATE TABLE util_test.t3 (a int)")
        self.server1.exec_query("RESET MASTER")
        self.server2.exec_query("RESET MASTER")
        self.exec_copy(self.server1, self.server2,
                       copy_cmd_str + " --force ",
                       test_num, "fixed empty gtid_executed error",
                       False, False)
        test_num += 1

        self.replace_result("# GTID operation: SET @@GLOBAL.GTID_PURGED",
                            "# GTID operation: SET @@GLOBAL.GTID_PURGED = ?\n")
        
        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        return export_gtid.test.cleanup(self)
