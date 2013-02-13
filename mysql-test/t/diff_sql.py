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
from mysql.utilities.exception import MUTLibError, UtilDBError

class test(mutlib.System_test):
    """simple db diff
    This test executes a simple diff of two databases on separate servers.
    """

    def check_prerequisites(self):
        if self.servers.get_server(0).check_version_compat(5, 6, 5):
            raise MUTLibError("Test requires server version prior to 5.6.5")
        # Need at least one server.
        self.server1 = None
        self.server2 = None
        self.need_server = False
        if not self.check_num_servers(2):
            self.need_server = True
        return self.check_num_servers(1)

    def _load_data(self, server, data_file):
        try:
            res = server.read_and_exec_SQL(data_file, self.debug)
        except MUTLibError, e:
            raise MUTLibError("Failed to read commands from file %s: " % \
                               data_file + e.errmsg)

    def setup(self):
        self.server1 = self.servers.get_server(0)
        if self.need_server:
            try:
                self.servers.spawn_new_servers(2)
            except MUTLibError, e:
                raise MUTLibError("Cannot spawn needed servers: %s" % \
                                   e.errmsg)
        self.server2 = self.servers.get_server(1)
        self.drop_all()
        self._load_data(self.server1,
                        os.path.normpath("./std_data/basic_data.sql"))
        self._load_data(self.server2,
                        os.path.normpath("./std_data/transform_data.sql"))

        return True
    
    def run(self):
        self.server1 = self.servers.get_server(0)
        self.res_fname = "result.txt"
        
        s1_conn = "--server1=" + self.build_connection_string(self.server1)
        s2_conn = "--server2=" + self.build_connection_string(self.server2)
       
        cmd_str = "mysqldiff.py %s %s util_test:util_test" % (s1_conn, s2_conn)
        cmd_str += " --force --difftype=sql "

        comment = "Test case 1 - create transform for objects for " + \
                  "--changes-for=server1"
        cmd_opts = " --changes-for=server1 "
        res = self.run_test_case(1, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        
        comment = "Test case 2 - create transform for objects for " + \
                  "--changes-for=server2"
        cmd_opts = " --changes-for=server2 "
        res = self.run_test_case(1, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        
        comment = "Test case 3 - create transform for objects for " + \
                  "--changes-for=server1 with reverse"
        cmd_opts = " --changes-for=server1 --show-reverse "
        res = self.run_test_case(1, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        
        comment = "Test case 4 - create transform for objects for " + \
                  "--changes-for=server2 with reverse"
        cmd_opts = " --changes-for=server2 --show-reverse "
        res = self.run_test_case(1, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
            
        # Do transform for tables with different names
        cmd_str = "mysqldiff.py %s %s util_test.t1:util_test.t6" % \
                  (s1_conn, s2_conn)
        cmd_str += " --force --difftype=sql "
        
        self.server2.exec_query("CREATE TABLE util_test.t6 AS "
                                "SELECT * FROM util_test.t1")
        
        comment = "Test case 5 - create transform for renamed table "
        res = self.run_test_case(1, cmd_str, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
            
        # Check to see if rename worked
        
        cmd_str = "mysqldiff.py %s %s util_test.t6:util_test.t6" % \
                  (s1_conn, s2_conn)
        cmd_str += " --force --difftype=sql "

        self.server1.exec_query("ALTER TABLE util_test.t1 "
                                "RENAME TO util_test.t6, ENGINE=MyISAM")

        comment = "Test case 6 - test transform for renamed table "
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        # The following are necessary due to changes in character spaces
        # introduced with Python 2.7.X in the difflib.
        
        self.replace_result("+++ util_test.t1", "+++ util_test.t1\n")
        self.replace_result("+++ util_test.t2", "+++ util_test.t2\n")
        self.replace_result("--- util_test.t1", "--- util_test.t1\n")
        self.replace_result("+++ util_test.t2", "+++ util_test.t2\n")
        self.replace_result("--- util_test.t2", "--- util_test.t2\n")
        self.replace_result("+++ util_test.t3", "+++ util_test.t3\n")
        self.replace_result("--- util_test.t3", "--- util_test.t3\n")
        self.replace_result("+++ util_test.t6", "+++ util_test.t6\n")
        self.replace_result("--- util_test.t6", "--- util_test.t6\n")
        
        return True
          
    def get_result(self):
        return self.compare(__name__, self.results)
    
    def record(self):
        return self.save_result_file(__name__, self.results)
    
    def drop_db(self, server, db):
        # Check before you drop to avoid warning
        try:
            res = server.exec_query("SHOW DATABASES LIKE 'util_%'")
        except:
            return True # Ok to exit here as there weren't any dbs to drop
        try:
            res = server.exec_query("DROP DATABASE %s" % db)
        except:
            return False
        return True
    
    def drop_all(self):
        self.drop_db(self.server1, "util_test")
        self.drop_db(self.server2, "util_test")
        return True

    def cleanup(self):
        if self.res_fname:
            os.unlink(self.res_fname)
        return self.drop_all()




