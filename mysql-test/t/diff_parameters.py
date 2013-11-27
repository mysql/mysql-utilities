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
import diff
from mysql.utilities.exception import MUTLibError

_FORMATS = ['unified', 'context', 'differ']
_DIRECTIONS = ['server1', 'server2']


class test(diff.test):
    """check parameters for diff
    This test executes a series of diff database operations on two
    servers using a variety of parameters. It uses the diff test
    as a parent for setup and teardown methods.
    """

    def check_prerequisites(self):
        return diff.test.check_prerequisites(self)

    def setup(self):
        return diff.test.setup(self)

    def run(self):
        self.server1 = self.servers.get_server(0)
        self.res_fname = "result.txt"

        s1_conn = "--server1={0}".format(
            self.build_connection_string(self.server1))
        s2_conn = "--server2={0}".format(
            self.build_connection_string(self.server2)
        )

        cmd_base = "mysqldiff.py {0} {1} util_test:util_test".format(
            s1_conn, s2_conn
        )

        test_num = 1
        cmd_opts = "--help"
        comment = "Test case {0} - Use {1} ".format(test_num, cmd_opts)
        cmd = "{0} {1}".format(cmd_base, cmd_opts)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        for frmt in _FORMATS:
            test_num += 1
            cmd_opts = "--difftype={0}".format(frmt)
            comment = "Test case {0} - Use diff {1}".format(test_num, cmd_opts)
            cmd = "{0} {1}".format(cmd_base, cmd_opts)
            res = self.run_test_case(1, cmd, comment)
            if not res:
                raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        cmd_opts = "--force"
        comment = "Test case {0} - Use {1} ".format(test_num, cmd_opts)
        cmd = "{0} {1}".format(cmd_base, cmd_opts)
        res = self.run_test_case(1, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        cmd_opts = "--quiet"
        comment = "Test case {0} - Use {1} ".format(test_num, cmd_opts)
        cmd = "{0} {1}".format(cmd_base, cmd_opts)
        res = self.run_test_case(1, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        cmd_opts = "--width=65"
        comment = "Test case {0} - Use {1} ".format(test_num, cmd_opts)
        cmd = "{0} {1}".format(cmd_base, cmd_opts)
        res = self.run_test_case(1, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        cmd_opts = "--width=55"
        comment = "Test case {0} - Use {1} ".format(test_num, cmd_opts)
        cmd = "{0} {1}".format(cmd_base, cmd_opts)
        res = self.run_test_case(1, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        cmd_opts = "-vvv"
        comment = "Test case {0} - Use {1} ".format(test_num, cmd_opts)
        cmd = "{0} {1}".format(cmd_base, cmd_opts)
        res = self.run_test_case(1, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Test --changes-for and reverse
        for direct in _DIRECTIONS:
            test_num += 1
            cmd_opts = "--changes-for={0} ".format(direct)
            comment = "Test case {0} - Use {1} ".format(test_num, cmd_opts)
            cmd = "{0} {1}".format(cmd_base, cmd_opts)
            res = self.run_test_case(1, cmd, comment)
            if not res:
                raise MUTLibError("{0}: failed".format(comment))
                # now with reverse
            test_num += 1
            cmd_opts = "--changes-for={0} --show-reverse".format(direct)
            comment = "Test case {0} - Use {1} ".format(test_num, cmd_opts)
            cmd = "{0} {1}".format(cmd_base, cmd_opts)
            res = self.run_test_case(1, cmd, comment)
            if not res:
                raise MUTLibError("{0}: failed".format(comment))

        # Test use of --skip-table-options (different AUTO_INCREMENT)
        difftype_options = ['', '--difftype=context', '--difftype=sql']
        cmd_base = ("mysqldiff.py {0} {1} "
                    "db_diff_test:db_diff_test".format(s1_conn, s2_conn))
        for difftype_opt in difftype_options:
            for direct in _DIRECTIONS:
                test_num += 1
                comment = ("Test case {0}a - Changes for {1} {2} (not "
                           "skipping table options).".format(test_num, direct,
                                                             difftype_opt))
                cmd = "{0} --changes-for={1} {2}".format(cmd_base, direct,
                                                         difftype_opt)
                res = self.run_test_case(1, cmd, comment)
                if not res:
                    raise MUTLibError("{0}: failed".format(comment))
                comment = ("Test case {0}b - Changes for {1} {2} (skipping "
                           "table options).".format(test_num, direct,
                                                    difftype_opt))
                cmd = ("{0} --changes-for={1} {2} "
                       "--skip-table-options".format(cmd_base, direct,
                                                     difftype_opt))
                res = self.run_test_case(0, cmd, comment)
                if not res:
                    raise MUTLibError("{0}: failed".format(comment))

        # The following are necessary due to changes in character spaces
        # introduced with Python 2.7.X in the difflib.
        self.replace_result("+++ util_test.t1", "+++ util_test.t1\n")
        self.replace_result("+++ util_test.t2", "+++ util_test.t2\n")
        self.replace_result("--- util_test.t1", "--- util_test.t1\n")
        self.replace_result("--- util_test.t2", "--- util_test.t2\n")
        self.replace_result("*** util_test.t1", "*** util_test.t1\n")
        self.replace_result("*** util_test.t2", "*** util_test.t2\n")
        self.replace_substring("on [::1]", "on localhost")

        # Mask version
        self.replace_result(
                "MySQL Utilities mysqldiff version",
                "MySQL Utilities mysqldiff version X.Y.Z "
                "(part of MySQL Workbench ... XXXXXX)\n"
        )

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        return diff.test.cleanup(self)
