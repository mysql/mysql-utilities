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
copy_user_parameters test.
"""

import copy_user

from mysql.utilities.exception import MUTLibError


class test(copy_user.test):
    """clone user parameter checking
    This test exercises the parameters for the clone user utility. It uses
    the copy_user test as a parent for setup and teardown methods.
    """

    def check_prerequisites(self):
        return copy_user.test.check_prerequisites(self)

    def setup(self):
        return copy_user.test.setup(self)

    def run(self):
        self.res_fname = "result.txt"

        from_conn = "--source={0}".format(
            self.build_connection_string(self.server1))
        to_conn = "--destination={0}".format(
            self.build_connection_string(self.server2))
        cmd_str = "mysqluserclone.py {0} {1} ".format(from_conn, to_conn)

        test_num = 1
        comment = "Test case {0} - show the grant statements".format(test_num)
        res = self.run_test_case(0,
                                 cmd_str + " --dump joe_nopass@user " +
                                 "jack@user john@user jill@user",
                                 comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = "Test case 2 - show the help".format(test_num)
        res = self.run_test_case(0, cmd_str + " --help", comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Remove version information
        self.remove_result_and_lines_after("MySQL Utilities mysqluserclone.py "
                                           "version", 6)

        test_num += 1
        comment = "Test case 3 - use the quiet parameter".format(test_num)
        res = self.run_test_case(0, cmd_str + "joe_nopass@user --force "
                                              "jack@user john@user "
                                              "jill@user --quiet ",
                                 comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        cmd_str = "mysqluserclone.py --source={0}".format(
            self.build_connection_string(self.server2))
        comment = ("Test case {0} - use --dump and --list to show "
                   "all users".format(test_num))
        res = self.run_test_case(0, cmd_str + " --list --dump --format=csv",
                                 comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        self.remove_result("root,")
        self.remove_result("# Dumping grants for user 'root'")
        self.remove_result("GRANT ALL PRIVILEGES ON *.* TO 'root'")
        self.remove_result("GRANT PROXY ON ''@'' TO 'root'")
        self.remove_result("# Cannot show grants for user")

        # The mysql.sys user is only on 5.7.9+
        self.remove_result("mysql.sys,")
        self.remove_result("# Dumping grants for user 'mysql.sys'@'localhost'")
        self.remove_result("GRANT USAGE ON *.* TO 'mysql.sys'@")
        self.remove_result("GRANT TRIGGER ON `sys`.* TO 'mysql.sys'@")
        self.remove_result("GRANT SELECT ON `sys`.`sys_config` TO 'mysql.sys'")

        self.replace_substring("on [::1]", "on localhost")

        # Mask version
        self.replace_result(
            "MySQL Utilities mysqluserclone version",
            "MySQL Utilities mysqluserclone version X.Y.Z\n")

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        return copy_user.test.cleanup(self)
