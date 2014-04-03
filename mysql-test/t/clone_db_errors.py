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
clone_db_errors test.
"""

import os

import clone_db

from mysql.utilities.exception import MUTLibError, UtilDBError, UtilError


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

        from_conn = "--source={0}".format(
            self.build_connection_string(self.server1))
        to_conn = "--destination={0}".format(
            self.build_connection_string(self.server1))

        cmd_str = "mysqldbcopy.py --skip-gtid {0} {1} ".format(from_conn,
                                                               to_conn)

        test_num = 1
        cmd_opts = "util_test:util_test"
        comment = "Test case {0} - error: same database".format(test_num)
        res = self.run_test_case(1, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        cmd_opts = "NOT_THERE_AT_ALL:util_db_clone"
        comment = ("Test case {0} - error: old database doesn't "
                   "exist".format(test_num))
        res = self.run_test_case(1, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        try:
            self.server1.exec_query("CREATE DATABASE util_db_clone")
        except UtilDBError as err:
            raise MUTLibError("{0}: failed: {1}".format(comment, err.errmsg))

        test_num += 1
        cmd_opts = "util_test:util_db_clone"
        comment = ("Test case {0} - error: target database already "
                   "exists".format(test_num))
        res = self.run_test_case(1, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        try:
            self.server1.exec_query("CREATE USER 'joe'@'localhost'")
        except UtilDBError as err:
            raise MUTLibError("{0}: failed: {1}".format(comment, err.errmsg))

        if os.name == "posix" and self.server1.socket is not None:
            from_conn = "--source=joe@localhost:{0}:{1}".format(
                self.server1.port, self.server1.socket)
        else:
            from_conn = "--source=joe@localhost:{0}".format(self.server1.port)

        cmd_str = "mysqldbcopy.py --skip-gtid {0} {1} ".format(from_conn,
                                                               to_conn)
        cmd_opts = "util_test:util_db_clone --drop-first"
        test_num += 1
        comment = ("Test case {0} - error: user with % - not "
                   "enough permissions".format(test_num))
        res = self.run_test_case(1, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        try:
            self.server1.exec_query("GRANT ALL ON util_test.* TO 'joe'@'%'")
        except UtilDBError as err:
            raise MUTLibError("{0}: failed: {1}".format(comment, err.errmsg))
        try:
            self.server1.exec_query("GRANT SELECT ON mysql.* TO 'joe'@'%'")
        except UtilDBError as err:
            raise MUTLibError("{0}: failed: {1}".format(comment, err.errmsg))

        test_num += 1
        comment = ("Test case {0} - No error: user with % "
                   "- has permissions".format(test_num))
        res = self.run_test_case(0, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        try:
            self.server1.exec_query("CREATE USER 'will'@'127.0.0.1'")
        except UtilDBError as err:
            raise MUTLibError("{0}: failed: {1}".format(comment, err.errmsg))
        try:
            self.server1.exec_query("GRANT ALL ON *.* TO 'will'@'127.0.0.1'")
        except UtilDBError as err:
            raise MUTLibError("{0}: failed: {1}".format(comment, err.errmsg))

        cmd_str = ("mysqldbcopy.py --source=rocks_rocks_rocks "
                   "{0} ".format(to_conn))
        cmd_str += "util_test:util_db_clone --drop-first "
        test_num += 1
        comment = "Test case {0} - cannot parse --source".format(test_num)
        res = self.run_test_case(2, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        cmd_str = ("mysqldbcopy.py --destination=rocks_rocks_rocks "
                   "{0} ".format(from_conn))
        cmd_str += "util_test:util_db_clone --drop-first "
        test_num += 1
        comment = "Test case {0} - cannot parse --destination".format(test_num)
        res = self.run_test_case(2, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        cmd_str = "mysqldbcopy.py --source=rocks_rocks_rocks "
        cmd_str += "util_test:util_db_clone --drop-first "
        test_num += 1
        comment = "Test case {0} - no destination specified".format(test_num)
        res = self.run_test_case(2, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        cmd_str = "mysqldbcopy.py {0} {1} ".format(to_conn, from_conn)
        cmd_str += " "
        test_num += 1
        comment = "Test case {0} - no database specified".format(test_num)
        res = self.run_test_case(2, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        from_conn = "--source={0}".format(
            self.build_connection_string(self.server1))
        to_conn = "--destination={0}".format(
            self.build_connection_string(self.server1))

        cmd_str = "mysqldbcopy.py {0} {1} --all".format(to_conn, from_conn)
        test_num += 1
        comment = "Test case {0} - clone with --all".format(test_num)
        res = self.run_test_case(1, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Mask known source and destination host name.
        self.replace_result("# Source on ",
                            "# Source on XXXX-XXXX: ... connected.\n")
        self.replace_result("# Destination on ",
                            "# Destination on XXXX-XXXX: ... connected.\n")

        # Ignore GTID messages (skipping GTIDs in this test)
        self.remove_result("# WARNING: The server supports GTIDs")

        # Replace connection errors
        self.replace_result("mysqldbcopy: error: Source connection "
                            "values invalid",
                            "mysqldbcopy: error: Source connection "
                            "values invalid\n")
        self.replace_result("mysqldbcopy: error: Destination connection "
                            "values invalid",
                            "mysqldbcopy: error: Destination connection "
                            "values invalid\n")

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        try:
            self.server1.exec_query("DROP USER 'joe'@'localhost'")
        except UtilError:
            pass
        try:
            self.server1.exec_query("DROP USER 'joe'")
        except UtilError:
            pass
        try:
            self.server1.exec_query("DROP USER 'joe'@'%'")
        except UtilError:
            pass
        try:
            self.server1.exec_query("DROP USER 'will'@'127.0.0.1'")
        except UtilError:
            pass
        return clone_db.test.cleanup(self)
