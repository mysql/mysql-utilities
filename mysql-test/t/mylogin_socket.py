#
# Copyright (c) 2016, Oracle and/or its affiliates. All rights reserved.
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
mylogin_socket test.
"""

import mutlib
import os
from mysql.utilities.exception import FormatError

from mysql.utilities.common.ip_parser import parse_connection
from mysql.utilities.common.options import parse_user_password


class test(mutlib.System_test):
    """Test the login-path authentication mechanism.
    This module tests the access to the .mylogin.cnf file and the use of the
    parse_connection method when specifying a login-path (instead of the user,
    password and localhost in plain text).
    """

    def check_prerequisites(self):
        # Check if the required tools are accessible
        self.check_mylogin_requisites()
        if os.name != "posix":
            raise MUTLibError("Test requires Posix machines.")
        # Check the required number of servers
        return self.check_num_servers(0)

    def setup(self):
        self.create_login_path_data('test_mylogin', 'test_user', 'localhost')
        self.create_login_path_data('test-hyphen1234#', 'test_user2',
                                    'localhost')
        self.create_login_path_data("test' \\\"-hyphen", 'test_user3',
                                    'localhost')
        return True

    def run(self):
        # Test parse_connection with login-paths
        con_tests = ["test_user@localhost:1000:/my.socket",
                     "test_mylogin:1000:/my.socket",
                     "test_user@localhost:3306:/my.socket",
                     "test_mylogin:3306:/my.socket",
                     "test-hyphen1234#:13000:my.socket",
                     "test' \\\"-hyphen:3306:my.socket",
                     "test' \\\"-hyphen:13001:my.socket",
                     "rpl:'L5!w1Sj40(p?tF@(_@:z(HXc'@'localhost':3308:sock1"]

        for test_ in con_tests:
            con_dic = parse_connection(test_, options={"charset": "utf8"})
            # Sort the keys to fix the issue where the keys are printed in
            # different order on linux and windows.
            self.results.append(sorted(con_dic.iteritems()))

        # Test parse_user_password with login-paths
        user_pass_tests = ["test_user", "test_mylogin", "test_user:",
                           "user_x:", "user_x:pass_y",
                           "rpl:'L5!w1SJzVuj40(p?tF@(9Y70_@:z(HXc'"]
        for test_ in user_pass_tests:
            try:
                user_pass = parse_user_password(test_)
                self.results.append(user_pass)
            except FormatError as err:
                self.results.append(err)

        # Transform list of dictionaries into list of strings
        self.results = ["{0!s}\n".format(con_dic) for con_dic in self.results]

        # remove socket information from posix systems to have same output
        # on both posix and and windows systems
        self.replace_substring_portion(", ('unix_socket'", ".socket')", '')

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        self.remove_login_path_data('test_mylogin')
        self.remove_login_path_data('test-hyphen1234#')
        self.remove_login_path_data("test' \\\"-hyphen")
        return True
