#
# Copyright (c) 2010, 2016, Oracle and/or its affiliates. All rights reserved.
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
diff_errors test.
"""

import diff

from mysql.utilities.exception import MUTLibError, UtilError


# Note: The entry util_test.util_test is a valid test. Removed from list
#       of malformed entries.
_ARGUMENTS = ['util_test.t3:util_test', 'util_test:util_test.t3',
              'util_test.t3.t3:util_test.t3', 'util_test.t3:util_test..t4']


class test(diff.test):
    """check errors for diff
    This test executes of conditions to test the errors for the diff utility.
    It uses the diff test as a parent for setup and teardown methods.
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
            self.build_connection_string(self.server2))

        cmd_str = "mysqldiff.py {0} {1} util_test:util_test ".format(s1_conn,
                                                                     s2_conn)

        test_num = 1
        cmd_opts = " --difftype=differ"
        comment = "Test case {0} - Use diff {1}".format(test_num, cmd_opts)
        res = self.run_test_case(1, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        cmd_str = "mysqldiff.py {0} {1} ".format(s1_conn, s2_conn)

        test_num += 1
        cmd_opts = " util_test1:util_test"
        comment = "Test case {0} - database doesn't exist".format(test_num)
        res = self.run_test_case(1, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        cmd_opts = " util_test:util_test2"
        comment = "Test case {0} - database doesn't exist".format(test_num)
        res = self.run_test_case(1, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        cmd_opts = " util_test.t3:util_test.t33"
        comment = "Test case {0} - object doesn't exist".format(test_num)
        res = self.run_test_case(1, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        cmd_opts = " util_test.t31:util_test.t3"
        comment = "Test case {0} - object doesn't exist".format(test_num)
        res = self.run_test_case(1, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        cmd_opts = " util_test.t3:util_test.t33 --force"
        comment = "Test case {0} - doesn't exist force".format(test_num)
        res = self.run_test_case(1, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        cmd_opts = " util_test.t31:util_test.t3 --force"
        comment = "Test case {0} - doesn't exist force".format(test_num)
        res = self.run_test_case(1, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        cmd_opts = (" util_test.t3:util_test.t33 util_test.t1:util_test.t1 "
                    "--force")
        comment = ("Test case {0} - check all existing objects using "
                   "--force").format(test_num)
        res = self.run_test_case(1, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        cmd_opts = (" util_test.t31:util_test.t3 util_test.t1:util_test.t1 "
                    "--force")
        comment = ("Test case {0} - check all existing objects using "
                   "--force").format(test_num)
        res = self.run_test_case(1, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        for arg in _ARGUMENTS:
            test_num += 1
            cmd_opts = " {0}".format(arg)
            comment = "Test case {0} - malformed argument{1} ".format(test_num,
                                                                      cmd_opts)
            res = self.run_test_case(2, cmd_str + cmd_opts, comment)
            if not res:
                raise MUTLibError("{0}: failed".format(comment))

        try:
            self.server1.exec_query("CREATE TABLE util_test.t6 (a int)")
            self.server2.exec_query("CREATE TABLE util_test.t7 (a int)")
        except UtilError:
            raise MUTLibError("Cannot create test tables.")

        test_num += 1
        cmd_opts = " util_test:util_test "
        comment = ("Test case {0} - some objects don't exist in "
                   "dbs".format(test_num))
        res = self.run_test_case(1, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        cmd_opts = " "
        comment = "Test case {0} - no objects specified.".format(test_num)
        res = self.run_test_case(2, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = "Test case {0} - invalid --character-set".format(test_num)
        res = self.run_test_case(1, "{0} util_test:util_test "
                                 "--character-set=unsupported_charset"
                                 "".format(cmd_str),
                                 comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        self.replace_substring("on [::1]", "on localhost")

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        return diff.test.cleanup(self)
