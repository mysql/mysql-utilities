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
import clone_db
from mysql.utilities.exception import MUTLibError, UtilDBError

class test(clone_db.test):
    """check errors for clone db
    This test ensures the known error conditions are tested. It uses the
    clone_db test as a parent for setup and teardown methods.
    """

    def check_prerequisites(self):
        return clone_db.test.check_prerequisites(self)

    def setup(self):
        return clone_db.test.setup(self)
        
    def run(self):
        self.server1 = self.servers.get_server(0)
        self.res_fname = "result.txt"
       
        from_conn = "--source=" + self.build_connection_string(self.server1)
        to_conn = "--destination=" + self.build_connection_string(self.server1)

        cmd_str = "mysqldbcopy.py --skip-gtid %s %s " % (from_conn, to_conn)
        
        cmd_opts = "util_test:util_test"
        comment = "Test case 1 - error: same database"
        res = self.run_test_case(1, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        cmd_opts = "NOT_THERE_AT_ALL:util_db_clone"
        comment = "Test case 2 - error: old database doesn't exist"
        res = self.run_test_case(1, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        
        try:
            self.server1.exec_query("CREATE DATABASE util_db_clone")
        except UtilDBError, e:
            raise MUTLibError("%s: failed: %s" % (comment, e.errmsg))
        
        cmd_opts = "util_test:util_db_clone"
        comment = "Test case 3 - error: target database already exists"
        res = self.run_test_case(1, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        try:
            self.server1.exec_query("CREATE USER 'joe'@'localhost'")
        except UtilDBError, e:
            raise MUTLibError("%s: failed: %s" % (comment, e.errmsg))

        if os.name == "posix" and self.server1.socket is not None:
            from_conn = "--source=joe@localhost:%s:%s" % \
                        (self.server1.port, self.server1.socket)
        else:
            from_conn = "--source=joe@localhost:%s" % self.server1.port

        cmd_str = "mysqldbcopy.py --skip-gtid %s %s " % (from_conn, to_conn)
        cmd_opts = "util_test:util_db_clone --force"
        comment = "Test case 4 - error: user with % - not enough permissions"
        res = self.run_test_case(1, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
                
        try:
            self.server1.exec_query("GRANT ALL ON util_test.* TO 'joe'@'%'")
        except UtilDBError, e:
            raise MUTLibError("%s: failed: %s" % (comment, e.errmsg))
        try:
            self.server1.exec_query("GRANT SELECT ON mysql.* TO 'joe'@'%'")
        except UtilDBError, e:
            raise MUTLibError("%s: failed: %s" % (comment, e.errmsg))
        
        comment = "Test case 5 - No error: user with % - has permissions"
        res = self.run_test_case(0, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        
        try:
            self.server1.exec_query("CREATE USER 'will'@'127.0.0.1'")
        except UtilDBError, e:
            raise MUTLibError("%s: failed: %s" % (comment, e.errmsg))
        try:
            self.server1.exec_query("GRANT ALL ON *.* TO 'will'@'127.0.0.1'")
        except UtilDBError, e:
            raise MUTLibError("%s: failed: %s" % (comment, e.errmsg))
        
        cmd_str = "mysqldbcopy.py --source=rocks_rocks_rocks %s " % to_conn
        cmd_str += "util_test:util_db_clone --force "
        comment = "Test case 6 - cannot parse --source"
        res = self.run_test_case(2, cmd_str, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        cmd_str = "mysqldbcopy.py --destination=rocks_rocks_rocks %s " % \
                  from_conn
        cmd_str += "util_test:util_db_clone --force "
        comment = "Test case 7 - cannot parse --destination"
        res = self.run_test_case(2, cmd_str, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        cmd_str = "mysqldbcopy.py --source=rocks_rocks_rocks "
        cmd_str += "util_test:util_db_clone --force "
        comment = "Test case 8 - no destination specified"
        res = self.run_test_case(2, cmd_str, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        cmd_str = "mysqldbcopy.py %s %s " % (to_conn, from_conn)
        cmd_str += " "
        comment = "Test case 9 - no database specified"
        res = self.run_test_case(2, cmd_str, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        from_conn = "--source=" + self.build_connection_string(self.server1)
        to_conn = "--destination=" + self.build_connection_string(self.server1)

        cmd_str = "mysqldbcopy.py %s %s --all" % (to_conn, from_conn)
        comment = "Test case 10 - clone with --all"
        res = self.run_test_case(1, cmd_str, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        # Ignore GTID messages (skipping GTIDs in this test)
        self.remove_result("# WARNING: The server supports GTIDs")

        # Replace connection errors
        self.replace_result("mysqldbcopy.py: error: Source connection "
                            "values invalid",
                            "mysqldbcopy.py: error: Source connection "
                            "values invalid\n")
        self.replace_result("mysqldbcopy.py: error: Destination connection "
                            "values invalid",
                            "mysqldbcopy.py: error: Destination connection "
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
        try:
            self.server1.exec_query("DROP USER 'joe'")
        except:
            pass
        try:
            self.server1.exec_query("DROP USER 'joe'@'%'")
        except:
            pass
        try:
            self.server1.exec_query("DROP USER 'will'@'127.0.0.1'")
        except:
            pass
        return clone_db.test.cleanup(self)




