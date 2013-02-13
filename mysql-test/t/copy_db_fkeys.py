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
from mysql.utilities.exception import MUTLibError, UtilDBError, UtilError

class test(mutlib.System_test):
    """simple db copy
    This test executes copy database test cases among two servers with
    foreign keys defined.
    """

    def check_prerequisites(self):
        self.check_gtid_unsafe()
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
            except MUTLibError, e:
                raise MUTLibError("Cannot spawn needed servers: %s" % \
                                   e.errmsg)
        self.server2 = self.servers.get_server(1)
        self.drop_all()
        self.server1.disable_foreign_key_checks(True)
        data_file = os.path.normpath("./std_data/fkeys.sql")
        try:
            res = self.server1.read_and_exec_SQL(data_file, self.debug)
        except UtilError, e:
            raise MUTLibError("Failed to read commands from file %s: %s" % \
                               (data_file, e.errmsg))
        self.server1.disable_foreign_key_checks(False)
        return True

    
    def run(self):
        self.res_fname = "result.txt"
        
        from_conn = "--source=" + self.build_connection_string(self.server1)
        to_conn = "--destination=" + self.build_connection_string(self.server2)
       
        comment = "Test case 1 - copy database with foreign keys"
        cmd = "mysqldbcopy.py --skip-gtid %s %s " % (from_conn, to_conn)
        res = self.exec_util(cmd + " util_test_fk:util_db_clone_fk",
                             self.res_fname)
        self.results.append(res)
        if res != 0:
            raise MUTLibError("%s: failed" % comment)

        return True
  
    def get_result(self):
        msg = None
        if self.server2 and self.results[0] == 0:
            query = "SHOW DATABASES LIKE 'util_db_clone_fk'"
            try:
                res = self.server2.exec_query(query)
                if res and res[0][0] == 'util_db_clone_fk':
                    return (True, msg)
            except UtilDBError, e:
                raise MUTLibError(e.errmsg)
            query = "SHOW DATABASES LIKE 'util_test_fk'"
            try:
                res = self.server2.exec_query(query)
                if res and res[0][0] == 'util_test_fk':
                    return (True, msg)
            except UtilDBError, e:
                raise MUTLibError(e.errmsg)
        return (False, ("Result failure.\n", "Database copy not found.\n"))
    
    def record(self):
        # Not a comparative test, returning True
        return True
    
    def drop_db(self, server, db):
        # Check before you drop to avoid warning
        try:
            res = server.exec_query("SHOW DATABASES LIKE 'util_db_clone_fk'")
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
            self.drop_db(self.server1, "util_test_fk")
        except:
            res1 = False
        try:
            self.drop_db(self.server2, "util_test_fk")
        except:
            res2 = False
        try:
            self.drop_db(self.server2, "util_db_clone_fk")
        except:
            res3 = False
        return res1 and res2 and res3
            
    def cleanup(self):
        if self.res_fname:
            os.unlink(self.res_fname)
        return self.drop_all()


