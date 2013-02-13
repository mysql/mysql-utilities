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
from mysql.utilities.exception import UtilError, MUTLibError

class test(mutlib.System_test):
    """simple db copy
    This test executes copy of a database with an object that has
    names or identifiers with special symbols to check for compatibility -
    see BUG#61840.
    """

    def check_prerequisites(self):
        # Need at least one server.
        self.server1 = None
        self.server2 = None
        self.need_server = False
        if not self.check_num_servers(2):
            self.need_server = True
        return self.check_num_servers(1)

    def setup(self):
        self.server1 = self.servers.get_server(0)
        if self.need_server:
            try:
                self.servers.spawn_new_servers(2)
            except UtilError, e:
                raise MUTLibError("Cannot spawn needed servers: %s" % \
                                   e.errmsg)
        self.server2 = self.servers.get_server(1)
        self.drop_all()
        data_file = os.path.normpath("./std_data/special_data.sql")
        try:
            res = self.server1.read_and_exec_SQL(data_file, self.debug)
        except UtilError, e:
            raise MUTLibError("Failed to read commands from file %s: " % \
                               data_file + e.errmsg)
        return True

    
    def run(self):
        self.res_fname = "result.txt"
        
        from_conn = "--source=" + self.build_connection_string(self.server1)
        to_conn = "--destination=" + self.build_connection_string(self.server2)
       
        comment = "Test case 1 - copy a database with special symbols"
        cmd_str = "mysqldbcopy.py --skip-gtid %s %s " % (from_conn, to_conn)
        res = self.run_test_case(0, cmd_str + " util_spec:util_spec_clone",
                                 comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
            
        res = self.server2.exec_query("SELECT ROUTINE_DEFINITION FROM "
                                      "INFORMATION_SCHEMA.ROUTINES "
                                      "WHERE ROUTINE_SCHEMA = 'util_spec_clone'"
                                      " AND ROUTINE_NAME = 'spec_date'")
        self.results.append(res[0][0].strip(' ')+"\n")
        
        # Ignore GTID messages (skipping GTIDs in this test)
        self.remove_result("# WARNING: The server supports GTIDs")

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
        res1, res2, res3 = True, True, True
        try:
            self.drop_db(self.server1, "util_spec")
        except:
            res1 = False
        try:
            self.drop_db(self.server2, "util_spec_clone")
        except:
            res2 = False
        return res1 and res2
            
    def cleanup(self):
        if self.res_fname:
            os.unlink(self.res_fname)
        return self.drop_all()


