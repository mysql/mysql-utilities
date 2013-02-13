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
from mysql.utilities.exception import MUTLibError

class test(mutlib.System_test):
    """Process grep
    This test executes the process grep tool on a single server.
    """

    def check_prerequisites(self):
        self.check_gtid_unsafe()
        self.server1 = None
        self.need_servers = False
        if not self.check_num_servers(2):
            self.need_servers = True
        return self.check_num_servers(1)

    def setup(self):
        num_server = self.servers.num_servers()
        if self.need_servers:
            try:
                self.servers.spawn_new_servers(2)
            except MUTLibError, e:
                raise MUTLibError("Cannot spawn needed servers: %s" % \
                                   e.errmsg)
        else:
            num_server -= 1 # Get last server in list
        self.server1 = self.servers.get_server(num_server)
        data_file = os.path.normpath("./std_data/basic_data.sql")
        self.drop_all()
        try:
            res = self.server1.read_and_exec_SQL(data_file, self.debug)
        except MUTLibError, e:
            raise MUTLibError("Failed to read commands from file %s: " % \
                               data_file + e.errmsg)
        return True
    
    def run(self):
        self.res_fname = "result.txt"
        
        from_conn = self.build_connection_string(self.server1)
        conn_val = self.get_connection_values(self.server1)
        
        cmd_base = "mysqlmetagrep.py --server=%s --database=util_test " % \
                   from_conn
        
        test_case_num = 1
        
        comment = "Test case %d - find objects simple search" % test_case_num
        test_case_num += 1
        cmd = cmd_base + "--pattern=t_"
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        self.results.append("\n")
        
        comment = "Test case %d - find objects name search" % test_case_num
        test_case_num += 1
        cmd = cmd_base + "-b --pattern=%t2%"
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        self.results.append("\n")

        comment = "Test case %d - find objects regexp search" % test_case_num
        test_case_num += 1
        cmd = cmd_base + "-Gb --pattern=t2"
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        self.results.append("\n")
        
        comment = "Test case %d - find objects regexp search with type " % \
                  test_case_num
        test_case_num += 1
        cmd = cmd_base + "-Gb --pattern=t2 --search=table"
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        self.results.append("\n")
        
        _FORMATS = ("CSV","TAB","VERTICAL","GRID")
        for format in _FORMATS:
            comment = "Test case %d - find objects " % \
                      test_case_num + " format=%s" % format
            test_case_num += 1
            cmd = cmd_base + "--format=%s -Gb --pattern=t2" % format
            res = self.run_test_case(0, cmd, comment)
            if not res:
                raise MUTLibError("%s: failed" % comment)
            self.results.append("\n")
 
        # CSV masks
        self.mask_column_result("root:*@localhost", ",", 1, "root[...]")

        # TAB masks
        self.mask_column_result("root:*@localhost", "\t", 1, "root[...]")

        # Vertical masks
        self.replace_result("  Connection: ", " Connection: XXXXX\n")

        # Grid masks
        # Here, we truncate all horizontal bars for deterministic results
        self.replace_result("+---", "+---+\n")
        self.mask_column_result("| root", "|", 2, " root[...]  ")
        self.replace_result("| Connection",
                            "| Connection | Object Type  | Object Name  "
                            "| Database   |\n")
        
        return True
          
    def get_result(self):
        return self.compare(__name__, self.results)
    
    def record(self):
        return self.save_result_file(__name__, self.results)
    
    def drop_db(self, server, db):
        # Check before you drop to avoid warning
        try:
            res = server.exec_query("SHOW DATABASES LIKE 'util_%%'")
        except:
            return True # Ok to exit here as there weren't any dbs to drop
        try:
            res = server.exec_query("DROP DATABASE %s" % db)
        except:
            return False
        return True
    
    def drop_all(self):
        try:
            self.drop_db(self.server1, "util_test")
        except:
            return False
        return True

    def cleanup(self):
        if self.res_fname:
            os.unlink(self.res_fname)
        return self.drop_all()




