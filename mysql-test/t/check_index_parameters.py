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

import check_index
from mysql.utilities.exception import MUTLibError


class test(check_index.test):
    """check parameters for the check_index utility
    This test executes the check index utility parameters on a single server.
    It uses the check_index test as a parent for setup and teardown methods.
    """

    def check_prerequisites(self):
        return check_index.test.check_prerequisites(self)

    def setup(self):
        return check_index.test.setup(self)

    def run(self):
        self.res_fname = "result.txt"
        from_conn = "--server={0}".format(
            self.build_connection_string(self.server1))

        cmd_str = "mysqlindexcheck.py {0}".format(from_conn)

        test_num = 1
        comment = "Test case {0} - do the help".format(test_num)
        cmd = "{0} --help".format(cmd_str)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Remove version information
        self.remove_result_and_lines_after("MySQL Utilities mysqlindexcheck.py"
                                           " version", 6)

        test_num += 1
        comment = ("Test case {0} - show drops for a table with dupe (-vv) "
                   "indexes".format(test_num))
        cmd = "{0} util_test_a.t1 --show-drops -vv".format(cmd_str)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - show drops for a table with dupe "
                   "indexes".format(test_num))
        cmd = "{0} util_test_a.t1 -d".format(cmd_str)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - show drops for a table without dupe (-vv) "
                   "indexes".format(test_num))
        cmd = "{0} util_test_c.t6 --show-drops -vv".format(cmd_str)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - same as test case 2 but "
                   "quiet".format(test_num))
        cmd = "{0} util_test_a.t1 --show-drops".format(cmd_str)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - same as test case 4 but "
                   "quiet".format(test_num))
        cmd = "{0} util_test_c.t6 -d".format(cmd_str)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = "Test case {0} - show indexes".format(test_num)
        cmd = "{0} util_test_a.t1 --show-indexes".format(cmd_str)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = "Test case {0} - show indexes with -i".format(test_num)
        cmd = "{0} util_test_a.t1 -i".format(cmd_str)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - find redundancy with the clustered "
                   "index (InnoDB)".format(test_num))
        cmd = "{0} util_test_d.cluster_idx -d -i --stats -vvv".format(cmd_str)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - not find redundancy with the clustered "
                   "index (not InnoDB)".format(test_num))
        cmd = "{0} util_test_d.no_cluster_idx -d -i --stats -vvv".format(
            cmd_str)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - find various redundancies (and duplicates)"
                   " with the clustered index (InnoDB)".format(test_num))
        cmd = ("{0} util_test_d.various_cluster_idx -d -i --stats "
               "-vvv".format(cmd_str))
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Mask known source host name.
        self.replace_result("# Source on ",
                            "# Source on XXXX-XXXX: ... connected.\n")

        # Mask version
        self.replace_result(
                "MySQL Utilities mysqlindexcheck version",
                "MySQL Utilities mysqlindexcheck version X.Y.Z "
                "(part of MySQL Workbench ... XXXXXX)\n"
        )

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        return check_index.test.cleanup(self)
