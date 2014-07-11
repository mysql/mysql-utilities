#
# Copyright (c) 2010, 2014, Oracle and/or its affiliates. All rights reserved.
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

"""
diff test.
"""

import os

import mutlib

from mysql.utilities.exception import MUTLibError, UtilError


class test(mutlib.System_test):
    """simple db diff
    This test executes a simple diff of two databases on separate servers.
    """

    server1 = None
    server2 = None
    need_server = False

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
                raise MUTLibError("Cannot spawn needed servers: "
                                  "{0}".format(err.errmsg))
        self.server2 = self.servers.get_server(1)
        self.drop_all()
        data_file = os.path.normpath("./std_data/basic_data.sql")
        try:
            self.server1.read_and_exec_SQL(data_file, self.debug)
            self.server2.read_and_exec_SQL(data_file, self.debug)
        except UtilError as err:
            raise MUTLibError("Failed to read commands from file {0}: "
                              "{1}".format(data_file, err.errmsg))
        try:
            # Now do some alterations...
            self.server2.exec_query("ALTER TABLE util_test.t1 ADD "
                                    "COLUMN b int")
            self.server2.exec_query("ALTER TABLE util_test.t2 ENGINE = MEMORY")
            # Event has time in its definition. Remove for deterministic return
            self.server1.exec_query("USE util_test;")
            self.server1.exec_query("DROP EVENT util_test.e1")
            self.server2.exec_query("USE util_test;")
            self.server2.exec_query("DROP EVENT util_test.e1")
        except UtilError as err:
            raise MUTLibError("Failed to execute query: "
                              "{0}".format(err.errmsg))

        # Create backtick database (with weird names)
        data_file_backticks = os.path.normpath(
            "./std_data/db_compare_backtick.sql")
        try:
            self.server1.read_and_exec_SQL(data_file_backticks, self.debug)
            self.server2.read_and_exec_SQL(data_file_backticks, self.debug)
        except UtilError as err:
            raise MUTLibError("Failed to read commands from file {0}: "
                              "{1}".format(data_file_backticks, err.errmsg))

        # Add some data to server1 to change AUTO_INCREMENT value.
        try:
            for _ in range(5):
                self.server1.exec_query("INSERT INTO "
                                        "`db_diff_test`.`table-dash` "
                                        "VALUES (NULL)")
        except UtilError as err:
            raise MUTLibError("Failed to insert data on server1: "
                              "{0}".format(err.errmsg))

        return True

    def run(self):
        self.mask_global = False  # Turn off global masks
        self.server1 = self.servers.get_server(0)
        self.res_fname = "result.txt"

        s1_conn = "--server1={0}".format(
            self.build_connection_string(self.server1))
        s2_conn = "--server2={0}".format(
            self.build_connection_string(self.server2))
        s2_conn_dupe = "--server2={0}".format(
            self.build_connection_string(self.server1))

        cmd_base = "mysqldiff.py {0} {1} ".format(s1_conn, s2_conn)

        test_num = 1
        comment = "Test case {0} - diff a sample database".format(test_num)
        cmd = "{0} util_test:util_test".format(cmd_base)
        res = self.run_test_case(1, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - diff a single object - not "
                   "same".format(test_num))
        cmd = "{0} util_test.t2:util_test.t2".format(cmd_base)
        res = self.run_test_case(1, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - diff a single object - is "
                   "same".format(test_num))
        cmd = "{0} util_test.t3:util_test.t3".format(cmd_base)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - diff multiple objects - are "
                   "same".format(test_num))
        cmd = ("{0} util_test.t3:util_test.t3 "
               "util_test.t4:util_test.t4".format(cmd_base))
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - diff multiple objects + database - some "
                   "same".format(test_num))
        cmd = ("{0} util_test.t3:util_test.t3 util_test.t4:util_test.t4 "
               "util_test:util_test --force".format(cmd_base))
        res = self.run_test_case(1, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # execute a diff on the same server to test messages

        self.server1.exec_query("CREATE DATABASE util_test1")

        test_num += 1
        comment = ("Test case {0} - diff two databases on same server "
                   "w/server2".format(test_num))
        cmd = ("mysqldiff.py {0} {1} "
               "util_test:util_test1".format(s1_conn, s2_conn_dupe))
        res = self.run_test_case(1, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - diff two databases on same "
                   "server".format(test_num))
        cmd = "mysqldiff.py {0} util_test:util_test1".format(s1_conn)
        res = self.run_test_case(1, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - diff a sample database with weird names "
                   "(backticks)".format(test_num))
        # Set input parameter with appropriate quotes for the OS
        if os.name == 'posix':
            cmd_arg = "'`db.``:db`:`db.``:db`'"
        else:
            cmd_arg = '"`db.``:db`:`db.``:db`"'
        cmd = "mysqldiff.py {0} {1} {2}".format(s1_conn, s2_conn, cmd_arg)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - diff a single object with weird names "
                   "(backticks)".format(test_num))
        # Set input parameter with appropriate quotes for the OS
        if os.name == 'posix':
            cmd_arg = ("'`db.``:db`.```t``.``export_2`:"
                       "`db.``:db`.```t``.``export_2`'")
        else:
            cmd_arg = ('"`db.``:db`.```t``.``export_2`:'
                       '`db.``:db`.```t``.``export_2`"')
        cmd = "mysqldiff.py {0} {1} {2}".format(s1_conn, s2_conn, cmd_arg)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - diff a sample database containing tables "
                   "with weird names (no backticks) and different table "
                   "options.".format(test_num))
        cmd_arg = "db_diff_test:db_diff_test"
        cmd = "mysqldiff.py {0} {1} {2}".format(s1_conn, s2_conn, cmd_arg)
        res = self.run_test_case(1, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - diff a sample database containing tables "
                   "with weird names (no backticks) and skipping "
                   "table options.".format(test_num))
        cmd_arg = "db_diff_test:db_diff_test --skip-table-options"
        cmd = "mysqldiff.py {0} {1} {2}".format(s1_conn, s2_conn, cmd_arg)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Diff databases with objects of different type with the same name

        # Create the same PROCEDURE on each server with the same name of an
        # already existing TABLE (i.e., ```t``export_1`).
        self.server1.exec_query(
            "CREATE PROCEDURE `db.``:db`.```t``export_1`() "
            "SELECT 1")
        self.server2.exec_query(
            "CREATE PROCEDURE `db.``:db`.```t``export_1`() "
            "SELECT 1")
        if os.name == 'posix':
            cmd_arg = "'`db.``:db`:`db.``:db`'"
        else:
            cmd_arg = '"`db.``:db`:`db.``:db`"'
            # Execute test (no differences expected)
        test_num += 1
        comment = ("Test case {0} - diff a database with objects of "
                   "different types with the same name "
                   "(no differences)".format(test_num))
        cmd = "mysqldiff.py {0} {1} {2}".format(s1_conn, s2_conn, cmd_arg)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Replace the PROCEDURE previously created on one of the servers by a
        # different one.
        self.server2.exec_query("DROP PROCEDURE `db.``:db`.```t``export_1`")
        self.server2.exec_query(
            "CREATE PROCEDURE `db.``:db`.```t``export_1`() "
            "SELECT 2")
        # Execute test (differences expected)
        test_num += 1
        comment = ("Test case {0} - diff a database with objects of "
                   "different types with the same name "
                   "(with differences)".format(test_num))
        cmd = "mysqldiff.py {0} {1} {2}".format(s1_conn, s2_conn, cmd_arg)
        res = self.run_test_case(1, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Set input parameter with appropriate quotes for the OS
        if os.name == 'posix':
            cmd_arg = ("'`db.``:db`.```t``export_1`:"
                       "`db.``:db`.```t``export_1`'")
        else:
            cmd_arg = ('"`db.``:db`.```t``export_1`:'
                       '`db.``:db`.```t``export_1`"')
            # Execute test for specific objects (differences expected)
        test_num += 1
        comment = ("Test case {0} - diff specific objects of "
                   "different types with the same name "
                   "(with differences)".format(test_num))
        cmd = "mysqldiff.py {0} {1} {2}".format(s1_conn, s2_conn, cmd_arg)
        res = self.run_test_case(1, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # The following are necessary due to changes in character spaces
        # introduced with Python 2.7.X in the difflib.

        self.replace_result("+++ util_test.t1", "+++ util_test.t1\n")
        self.replace_result("+++ util_test.t2", "+++ util_test.t2\n")
        self.replace_result("--- util_test.t1", "--- util_test.t1\n")
        self.replace_result("--- util_test.t2", "--- util_test.t2\n")

        self.replace_substring("on [::1]", "on localhost")

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def drop_all(self):
        """Drops all databases and users created.
        """
        self.drop_db(self.server1, "util_test")
        self.drop_db(self.server1, "util_test1")
        self.drop_db(self.server2, "util_test")
        self.drop_db(self.server1, 'db.`:db')
        self.drop_db(self.server2, 'db.`:db')
        self.drop_db(self.server1, 'db_diff_test')
        self.drop_db(self.server2, 'db_diff_test')

        drop_user = ["DROP USER 'joe'@'user'", "DROP USER 'joe_wildcard'@'%'"]
        for drop in drop_user:
            try:
                self.server1.exec_query(drop)
                self.server2.exec_query(drop)
            except UtilError:
                pass
        return True

    def cleanup(self):
        if self.res_fname:
            os.unlink(self.res_fname)
        return self.drop_all()
