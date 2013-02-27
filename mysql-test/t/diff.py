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
    This test executes a simple diff of two databases on separate servers.
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
        data_file = os.path.normpath("./std_data/basic_data.sql")
        try:
            res = self.server1.read_and_exec_SQL(data_file, self.debug)
            res = self.server2.read_and_exec_SQL(data_file, self.debug)
        except UtilError as err:
            raise MUTLibError("Failed to read commands from file %s: %s"
                              % (data_file, err.errmsg))
        try:
            # Now do some alterations...
            res = self.server2.exec_query("ALTER TABLE util_test.t1 ADD "
                                          "COLUMN b int")
            res = self.server2.exec_query("ALTER TABLE util_test.t2 "
                                          "ENGINE = MEMORY")
            # Event has time in its definition. Remove for deterministic return
            res = self.server1.exec_query("USE util_test;")
            res = self.server1.exec_query("DROP EVENT util_test.e1")
            res = self.server2.exec_query("USE util_test;")
            res = self.server2.exec_query("DROP EVENT util_test.e1")
        except UtilError as err:
            raise MUTLibError("Failed to execute query: %s" % err.errmsg)

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
    
    def run(self):
        self.server1 = self.servers.get_server(0)
        self.res_fname = "result.txt"
        
        s1_conn = "--server1=" + self.build_connection_string(self.server1)
        s2_conn = "--server2=" + self.build_connection_string(self.server2)
        s2_conn_dupe = "--server2=" + self.build_connection_string(self.server1)
       
        cmd_str = "mysqldiff.py %s %s " % (s1_conn, s2_conn)

        comment = "Test case 1 - diff a sample database"
        res = self.run_test_case(1, cmd_str + "util_test:util_test", comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        comment = "Test case 2 - diff a single object - not same"
        res = self.run_test_case(1, cmd_str + "util_test.t2:util_test.t2",
                                 comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        comment = "Test case 3 - diff a single object - is same"
        res = self.run_test_case(0, cmd_str + "util_test.t3:util_test.t3",
                                 comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        comment = "Test case 4 - diff multiple objects - are same"
        res = self.run_test_case(0, cmd_str + "util_test.t3:util_test.t3 "
                                 "util_test.t4:util_test.t4",
                                 comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        comment = "Test case 5 - diff multiple objects + database - some same"
        res = self.run_test_case(1, cmd_str + "util_test.t3:util_test.t3 "
                                 "util_test.t4:util_test.t4 "
                                 "util_test:util_test --force ",
                                 comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
            
        # execute a diff on the same server to test messages
        
        self.server1.exec_query("CREATE DATABASE util_test1")
        
        comment = "Test case 6 - diff two databases on same server w/server2"
        cmd_str = "mysqldiff.py %s %s " % (s1_conn, s2_conn_dupe)
        res = self.run_test_case(1, cmd_str + "util_test:util_test1 ",
                                 comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
            
        comment = "Test case 7 - diff two databases on same server"
        cmd_str = "mysqldiff.py %s " % s1_conn
        res = self.run_test_case(1, cmd_str + "util_test:util_test1 ",
                                 comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        comment = ("Test case 8 - diff a sample database with weird names "
                   "(backticks)")
        # Set input parameter with appropriate quotes for the OS
        if os.name == 'posix':
            cmd_arg = "'`db``:db`:`db``:db`'"
        else:
            cmd_arg = '"`db``:db`:`db``:db`"'
        cmd_str = "mysqldiff.py %s %s %s" % (s1_conn, s2_conn, cmd_arg)
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        comment = ("Test case 9 - diff a single object with weird names "
                   "(backticks)")
        # Set input parameter with appropriate quotes for the OS
        if os.name == 'posix':
            cmd_arg = ("'`db``:db`.```t``.``export_2`:"
                       "`db``:db`.```t``.``export_2`'")
        else:
            cmd_arg = ('"`db``:db`.```t``.``export_2`:'
                       '`db``:db`.```t``.``export_2`"')
        cmd_str = "mysqldiff.py %s %s %s" % (s1_conn, s2_conn, cmd_arg)
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        # The following are necessary due to changes in character spaces
        # introduced with Python 2.7.X in the difflib.
        
        self.replace_result("+++ util_test.t1", "+++ util_test.t1\n")
        self.replace_result("+++ util_test.t2", "+++ util_test.t2\n")
        self.replace_result("--- util_test.t1", "--- util_test.t1\n")
        self.replace_result("--- util_test.t2", "--- util_test.t2\n")

        return True
          
    def get_result(self):
        return self.compare(__name__, self.results)
    
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
        self.drop_db(self.server1, "util_test")
        self.drop_db(self.server1, "util_test1")
        self.drop_db(self.server2, "util_test")
        self.drop_db(self.server1, 'db`:db')
        self.drop_db(self.server2, 'db`:db')
        return True

    def cleanup(self):
        if self.res_fname:
            os.unlink(self.res_fname)
        return self.drop_all()




