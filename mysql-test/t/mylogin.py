#
# Copyright (c) 2013 Oracle and/or its affiliates. All rights reserved.
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

import mutlib

from mysql.utilities.common.options import parse_connection
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

        # Check the required number of servers
        return self.check_num_servers(0)

    def setup(self):
        self.create_login_path_data('test_mylogin', 'test_user', 'localhost')
        return True

    def run(self):
        # Test parse_connection with login-paths
        con_tests = ["test_user@localhost", "test_mylogin",
                     "test_user@localhost:1000", "test_mylogin:1000",
                     "test_user@localhost:1000:/my.socket",
                     "test_mylogin:1000:/my.socket",
                     "test_user@localhost:/my.socket",
                     "test_mylogin:/my.socket"]
        for test in con_tests:
            con_dic = parse_connection(test)
            self.results.append(con_dic)

        # Test parse_user_password with login-paths
        user_pass_tests = ["test_user", "test_mylogin",
                           "test_user:", "user_x:", "user_x:pass_y"]
        for test in user_pass_tests:
            user_pass = parse_user_password(test)
            self.results.append(user_pass)
        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        self.remove_login_path_data('test_mylogin')
        return True
