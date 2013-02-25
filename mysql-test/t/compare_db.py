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

from mysql.utilities.common.table import quote_with_backticks

from mysql.utilities.exception import MUTLibError
from mysql.utilities.exception import UtilError


class test(mutlib.System_test):
    """simple db diff
    This test executes a consistency check of two databases on
    separate servers.
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
            except MUTLibError as err:
                raise MUTLibError("Cannot spawn needed servers: %s"
                                  % err.errmsg)
        self.server2 = self.servers.get_server(1)
        self.drop_all()
        data_file = os.path.normpath("./std_data/db_compare_test.sql")
        try:
            res = self.server1.read_and_exec_SQL(data_file, self.debug)
            res = self.server2.read_and_exec_SQL(data_file, self.debug)
        except UtilError as err:
            raise MUTLibError("Failed to read commands from file %s: %s"
                              % (data_file, err.errmsg))

        # Create backtick database (with weird names)
        data_file_backticks = os.path.normpath(
                                        "./std_data/db_compare_backtick.sql")
        try:
            res = self.server1.read_and_exec_SQL(data_file_backticks,
                                                 self.debug)
            res = self.server2.read_and_exec_SQL(data_file_backticks,
                                                 self.debug)
        except UtilError as err:
            raise MUTLibError("Failed to read commands from file %s: %s"
                              % (data_file_backticks, err.errmsg))

        return True
    
    def alter_data(self):
        try:
            # Now do some alterations...
            res = self.server1.exec_query("USE inventory;")
            res = self.server1.exec_query("DROP VIEW inventory.tools")
            res = self.server1.exec_query("CREATE VIEW inventory.tools AS "
                                          "SELECT * FROM inventory.supplies "
                                          "WHERE type = 'tool'")
            res = self.server1.exec_query("DELETE FROM inventory.supplies "
                                          "WHERE qty > 2")
            res = self.server1.exec_query("INSERT INTO inventory.supplier "
                                          "VALUES (2, 'Never Enough Inc.')")

            res = self.server2.exec_query("USE inventory;")
            res = self.server2.exec_query("DROP VIEW inventory.cleaning")
            res = self.server2.exec_query("DROP VIEW inventory.finishing_up")
            res = self.server2.exec_query("UPDATE inventory.supplies SET " 
                                          "cost = 10.00 WHERE cost = 9.99")
            res = self.server2.exec_query("INSERT INTO inventory.supplier "
                                          "VALUES (2, 'Wesayso Corporation')")
            res = self.server2.exec_query("INSERT INTO inventory.supplier "
                                          "VALUES (3, 'Never Enough Inc.')")
            res = self.server2.exec_query("DELETE FROM inventory.supplies "
                                          "WHERE cost = 10.00 AND "
                                          "type = 'cleaning'")
        except UtilError as err:
            raise MUTLibError("Failed to execute query: %s" % err.errmsg)

    
    def run(self):
        self.server1 = self.servers.get_server(0)
        self.res_fname = "result.txt"
        
        s1_conn = "--server1=" + self.build_connection_string(self.server1)
        s2_conn = "--server2=" + self.build_connection_string(self.server2)
        s2_conn_dupe = "--server2=" + self.build_connection_string(self.server1)
       
        cmd_str = "mysqldbcompare.py %s %s " % (s1_conn, s2_conn)

        comment = "Test case 1 - check a sample database"
        res = self.run_test_case(0, cmd_str + "inventory:inventory -a",
                                 comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
            
        self.alter_data()

        comment = "Test case 2 - check database with known differences " + \
                  "direction = server1 (default)"
        res = self.run_test_case(1, cmd_str + "inventory:inventory -a "
                                 "--format=CSV", comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
            
        comment = "Test case 3 - check database with known differences " + \
                  "direction = server2"
        res = self.run_test_case(1, cmd_str + "inventory:inventory -a "
                                 "--format=CSV --changes-for=server2", comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        comment = "Test case 4 - check database with known differences " + \
                  "direction = server1 and reverse"
        res = self.run_test_case(1, cmd_str + "inventory:inventory -a "
                                 "--format=CSV --changes-for=server1 "
                                 "--show-reverse", comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        comment = "Test case 5 - check database with known differences " + \
                  "direction = server2 and reverse"
        res = self.run_test_case(1, cmd_str + "inventory:inventory -a "
                                 "--format=CSV --changes-for=server2 "
                                 "--show-reverse", comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        # execute a compare on the same server to test messages
        
        self.server1.exec_query("CREATE DATABASE inventory2")
        
        comment = "Test case 6 - compare two databases on same server w/server2"
        cmd_str = "mysqldbcompare.py %s %s " % (s1_conn, s2_conn_dupe)
        res = self.run_test_case(1, cmd_str + "inventory:inventory2 -a ",
                                 comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
            
        comment = "Test case 7 - compare two databases on same server"
        cmd_str = "mysqldbcompare.py %s " % s1_conn
        res = self.run_test_case(1, cmd_str + "inventory:inventory2 -a ",
                                 comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        # Set input parameter with appropriate quotes for the OS
        if os.name == 'posix':
            cmd_arg = "'`db``:db`:`db``:db`' -a"
        else:
            cmd_arg = '"`db``:db`:`db``:db`" -a'
        cmd_str = "mysqldbcompare.py %s %s %s" % (s1_conn, s2_conn, cmd_arg)
        comment = ("Test case 8 - compare a database with weird names "
                   "(backticks)")
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        self.do_replacements()

        return True
          
    def get_result(self):
        return self.compare(__name__, self.results)

    def do_replacements(self):
        # The following are necessary due to changes in character spaces
        # introduced with Python 2.7.X in the difflib.
        prefixes = ['***','---','+++']
        names = ['supplies','supplier','tools']
        for prefix in prefixes:
            for name in names:
                self.replace_result("%s inventory.%s" % (prefix, name),
                                    "%s inventory.%s\n" % (prefix, name))
                
        # Mask inconsistent Python 2.7 behavior
        self.replace_result("@@ -1 +1 @@", "@@ -1,1 +1,1 @@\n")
        self.replace_result("# @@ -1 +1 @@", "# @@ -1,1 +1,1 @@\n")
    
    def record(self):
        return self.save_result_file(__name__, self.results)
    
    def drop_db(self, server, db):
        # Check before you drop to avoid warning
        try:
            res = server.exec_query("SHOW DATABASES LIKE '%s'" % db)
        except:
            return True # Ok to exit here as there weren't any dbs to drop
        try:
            q_db = quote_with_backticks(db)
            res = server.exec_query("DROP DATABASE %s" % q_db)
        except:
            return False
        return True
    
    def drop_all(self):
        self.drop_db(self.server1, "inventory")
        self.drop_db(self.server1, "inventory1")
        self.drop_db(self.server1, "inventory2")
        self.drop_db(self.server2, "inventory")
        self.drop_db(self.server1, 'db`:db')
        self.drop_db(self.server2, 'db`:db')
        return True

    def cleanup(self):
        if self.res_fname:
            os.unlink(self.res_fname)
        return self.drop_all()




