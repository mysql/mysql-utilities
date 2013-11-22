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

import clone_db

from mysql.utilities.exception import MUTLibError

# List of database objects for enumeration
(DATABASE, TABLE, VIEW, TRIGGER, PROC, FUNC, EVENT, GRANT) = (
    "DATABASE", "TABLE", "VIEW", "TRIGGER", "PROCEDURE", "FUNCTION", "EVENT",
    "GRANT")


class test(clone_db.test):
    """check parameters for clone db
    This test executes a series of clone database operations on a single
    server using a variety of parameters. It uses the clone_db test
    as a parent for setup and teardown methods.
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

        cmd_base = "mysqldbcopy.py --skip-gtid {0} {1}".format(from_conn,
                                                               to_conn)

        # In this test, we execute a series of commands saving the results
        # from each run to perform a comparative check.

        test_num = 1
        comment = "Test case {0} - normal run".format(test_num)
        cmd_opts = "util_test:util_db_clone"
        cmd = "{0} {1}".format(cmd_base, cmd_opts)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - operation fails - "
                   "need force".format(test_num))
        res = self.run_test_case(1, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = "Test case {0} - help".format(test_num)
        cmd_opts = "--help"
        cmd = "{0} {1}".format(cmd_base, cmd_opts)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Remove version information
        self.remove_result_and_lines_after("MySQL Utilities mysqldbcopy.py "
                                           "version", 6)

        # We exercise --force here to ensure skips don't interfere
        test_num += 1
        comment = "Test case {0} - no data".format(test_num)
        cmd_opts = "--force --skip=data util_test:util_db_clone"
        cmd = "{0} {1}".format(cmd_base, cmd_opts)
        res = self.run_test_case(0, cmd, comment)
        self.results.append(self.check_objects(self.server1, "util_db_clone"))
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = "Test case {0} - quiet clone".format(test_num)
        cmd_opts = "--force --skip=data --quiet util_test:util_db_clone"
        cmd = "{0} {1}".format(cmd_base, cmd_opts)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        # Drop cloned database to issue drop warnings in verbose mode.
        self.drop_db(self.server1, "util_db_clone")
        # Test clone in verbose mode.
        comment = ("Test case {0} - verbose clone "
                   "with drop warnings.".format(test_num))
        cmd_opts = "--force --verbose util_test:util_db_clone"
        cmd = "{0} {1}".format(cmd_base, cmd_opts)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Mask known platform-dependent lines
        self.replace_result("# Reading the file", "# Reading data file.\n")

        # Mask known source and destination host name.
        self.replace_result("# Source on ",
                            "# Source on XXXX-XXXX: ... connected.\n")
        self.replace_result("# Destination on ",
                            "# Destination on XXXX-XXXX: ... connected.\n")

        # Mask non deterministic data for event creation (definer and date).
        self.replace_substring_portion("CREATE", "EVENT `e1`",
                                       "CREATE DEFINER=`user`@`host` "
                                       "EVENT `e1`")
        self.replace_substring_portion("ON SCHEDULE EVERY 1 YEAR STARTS ",
                                       " ON COMPLETION",
                                       "ON SCHEDULE EVERY 1 YEAR STARTS "
                                       "'YYYY-MM-DD HH:MI:SS' ON COMPLETION")

        self.replace_result(
                "MySQL Utilities mysqldbcopy version",
                "MySQL Utilities mysqldbcopy version X.Y.Z "
                "(part of MySQL Workbench ... XXXXXX)\n"
        )

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        return clone_db.test.cleanup(self)
