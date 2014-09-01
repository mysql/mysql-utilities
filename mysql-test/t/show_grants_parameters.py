#
# Copyright (c) 2014, Oracle and/or its affiliates. All rights reserved.
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
priv_show parameters test.
"""

import os

import show_grants

from mysql.utilities.exception import MUTLibError


class test(show_grants.test):
    """Test mysqlpriv with different parameters.

    This test inherits from priv_show base test and shares the same
    prerequisites and setup"""

    def run(self):

        cmd_base = 'mysqlgrants.py --server={0}'.format(
            self.build_connection_string(self.server1))

        test_num = 1
        comment = ("Test case {0} - Show help".format(test_num))
        cmd = ("{0} --help".format(cmd_base))
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - Privilege inheritance with "
                   "--show=raw".format(test_num))
        cmd = ("{0} --show=raw util_test util_test.t3 util_test.t2 "
               "util_test.t1 util_test.p1 util_test.f1".format(cmd_base))
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - Privilege inheritance with "
                   "--show=user_grants".format(test_num))
        cmd = ("{0} --show=user_grants util_test util_test.t3 util_test.t2 "
               "util_test.t1 util_test.p1 util_test.f1".format(cmd_base))
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - Privilege inheritance with "
                   "--show=raw and --privilege=ALL".format(test_num))
        cmd = ("{0} --show=raw --privileges=ALL util_test util_test.t3 "
               "util_test.t2 util_test.t1 util_test.p1 "
               "util_test.f1".format(cmd_base))
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - Privilege inheritance with "
                   "--show=user_grants and --privilege=ALL".format(test_num))
        cmd = ("{0} --show=user_grants --privileges=ALL util_test "
               "util_test.t3 util_test.t2 util_test.t1 util_test.p1 "
               "util_test.f1".format(cmd_base))
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - Privilege inheritance with "
                   "--show=users and --privileges".format(test_num))
        cmd = ("{0} --show=users --privileges=SELECT,INSERT,EXECUTE "
               "util_test util_test.t3 util_test.t2 util_test.p1 "
               "util_test.t1 util_test.f1".format(cmd_base))
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - Privilege inheritance with "
                   "--show=users, --privileges and verbose".format(test_num))
        cmd = ("{0} --show=users --privileges=SELECT,INSERT,EXECUTE "
               "util_test util_test.t3 util_test.t2 util_test.p1 "
               "util_test.t1 util_test.f1 -vvv".format(cmd_base))
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - Privilege inheritance with "
                   "--show=user_grants and --privileges".format(test_num))
        cmd = ("{0} --show=user_grants --privileges=SELECT,INSERT,EXECUTE "
               "util_test util_test.t3 util_test.t2 util_test.p1 "
               "util_test.t1 util_test.f1".format(cmd_base))
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - Privilege inheritance with "
                   "--show=raw and --privileges".format(test_num))
        cmd = ("{0} --show=raw --privileges=SELECT,INSERT,EXECUTE util_test "
               "util_test.t3 util_test.t2 util_test.p1 util_test.t1 "
               "util_test.f1".format(cmd_base))
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - Test --show=raw in objects with and "
                   "without backticks with --show=raw".format(test_num))

        if os.name == 'posix':
            cmd_arg = ("'`db``:db`' '`db``:db`.```t``.``export_2`' "
                       "'`db``:db`.`fu``nc`' '`db``:db`.`pr````oc`' ")
        else:
            cmd_arg = ('"`db``:db`" "`db``:db`.```t``.``export_2`" '
                       '"`db``:db`.`fu``nc`" "`db``:db`.`pr````oc`" ')
        cmd = ("{0} --show=raw util_test util_test.t1 util_test.t2 "
               "util_test.does_not_exist util_test.v1 db_does_not_exist "
               "util_test.t3 {1}".format(cmd_base, cmd_arg))
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - Test --show=raw in objects with and "
                   "without backticks with "
                   "--show=user_grants".format(test_num))

        if os.name == 'posix':
            cmd_arg = ("'`db``:db`' '`db``:db`.```t``.``export_2`' "
                       "'`db``:db`.`fu``nc`' '`db``:db`.`pr````oc`' ")
        else:
            cmd_arg = ('"`db``:db`" "`db``:db`.```t``.``export_2`" '
                       '"`db``:db`.`fu``nc`" "`db``:db`.`pr````oc`" ')
        cmd = ("{0} --show=user_grants util_test util_test.t1 util_test.t2 "
               "util_test.does_not_exist util_test.v1 db_does_not_exist "
               "util_test.t3 {1}".format(cmd_base, cmd_arg))
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - show grantees, only databases with non "
                   "existing database for warning".format(test_num))
        cmd_arg = "'`db``:db`'" if os.name == 'posix' else '"`db``:db`'
        cmd = "{0} util_test non_existing_db {1}".format(cmd_base, cmd_arg)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - show grantees, only tables with non "
                   "existing table and an object that is not supported."
                   "".format(test_num))
        if os.name == 'posix':
            cmd_arg = "'`db``:db`.```t``.``export_2`'"
        else:
            cmd_arg = '"`db``:db`.```t``.``export_2`"'
        cmd = ("{0} util_test.t1 util_test.t2 util_test.does_not_exist "
               "util_test.v1 {1}".format(cmd_base, cmd_arg))
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - show grantees, only stored routines "
                   "(procedures and functions).".format(test_num))
        cmd = "{0} util_test.f1 util_test.p1".format(cmd_base)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        self.do_masks()
        return True

    def do_masks(self):
        """Mask non deterministic output"""

        show_grants.test.do_masks(self)
        self.remove_many_result([
            "GRANT ALL PRIVILEGES ON *.* TO 'root'@'",
            "# - For 'root'@'",
        ])
        self.replace_result("MySQL Utilities mysqlgrants version",
                            "MySQL Utilities mysqlgrants version XXXX\n")
        self.replace_substring_portion(", 'root'@'", '\n', '\n')

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)
