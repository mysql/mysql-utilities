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
import export_basic
from mysql.utilities.exception import MUTLibError

class test(export_basic.test):
    """Export errors
    This test executes the export utility on a single server to exercise
    the error conditions.
    """

    def check_prerequisites(self):
        return export_basic.test.check_prerequisites(self)

    def setup(self):
        self.server1 = self.servers.get_server(0)
        try:
            res = self.server1.exec_query("CREATE USER 'joe'@'localhost'")
        except:
            pass
        return export_basic.test.setup(self)
    
    def run(self):
        self.server1 = self.servers.get_server(0)
        self.res_fname = "result.txt"
        
        from_conn = "--server=%s" % self.build_connection_string(self.server1)
        
        cmd = "mysqldbexport.py %s util_test --skip-gtid " % from_conn
       
        comment = "Test case 1 - bad --skip values"
        cmd += " --skip=events,wiki-waki,woo-woo "
        res = self.run_test_case(1, cmd, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
                    
        comment = "Test case 2 - exporting data and skipping data"
        cmd += " --skip=data --export=data"
        res = self.run_test_case(1, cmd, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        cmd_str = "mysqldbexport.py %s --skip-gtid " % from_conn
        comment = "Test case 3 - no database specified"
        res = self.run_test_case(2, cmd_str, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        cmd_str = "mysqldbexport.py --server=rocks_rocks_rocks --skip-gtid " \
                  "util_test "
        comment = "Test case 4 - cannot parse --server"
        res = self.run_test_case(2, cmd_str, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        cmd_str = "mysqldbexport.py --skip-gtid " \
                  "--server=nope:nada@localhost:%s util_test" % self.server0.port
        comment = "Test case 5 - error: cannot connect to server"
        res = self.run_test_case(1, cmd_str, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        # Watchout for Windows: it doesn't use sockets!
        joe_conn = "--server=joe@localhost:%s" % self.server1.port
        if os.name == "posix" and self.server1.socket is not None:
            joe_conn += ":%s" % self.server1.socket

        cmd_str = "mysqldbexport.py %s util_test --skip-gtid " % joe_conn
        comment = "Test case 6 - error: not enough privileges"
        res = self.run_test_case(1, cmd_str, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        cmd_str = "mysqldbexport.py %s notthereatall --skip-gtid " % from_conn 
        comment = "Test case 7 - database does not exist"
        res = self.run_test_case(1, cmd_str, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        cmd_str = "mysqldbexport.py %s util_test --export=definitions" \
                  " --skip-gtid " % joe_conn
        comment = "Test case 8 - error: not enough privileges"
        res = self.run_test_case(1, cmd_str, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        cmd_str = "mysqldbexport.py %s util_test --all --skip-gtid" % from_conn
        comment = "Test case 9 - error: db list and --all"
        res = self.run_test_case(2, cmd_str, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        self.replace_substring("1045 (28000)", "1045")

        self.remove_result("# WARNING: The server supports GTIDs")

        self.replace_result("mysqldbexport.py: error: Server connection "
                            "values invalid",
                            "mysqldbexport.py: error: Server connection "
                            "values invalid\n")

        return True
          
    def get_result(self):
        return self.compare(__name__, self.results)
    
    def record(self):
        return self.save_result_file(__name__, self.results)
    
    def cleanup(self):
        try:
            self.server1.exec_query("DROP USER 'joe'@'localhost'")
        except:
            pass 
        return export_basic.test.cleanup(self)




