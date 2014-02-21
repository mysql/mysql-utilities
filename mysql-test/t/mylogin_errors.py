#
# Copyright (c) 2014 Oracle and/or its affiliates. All rights reserved.
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
import os

from mysql.utilities.common.ip_parser import parse_connection
from mysql.utilities.exception import UtilError


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
        self.create_login_path_data('test_no_host', 'test_user', None)
        self.create_login_path_data('test_no_user', None, 'localhost')

        return True

    def run(self):
        # Test parse_connection with login-paths missing parameters.
        con_tests = ["test_no_host", "test_no_user", "test_no_host:3333",
                     "test_no_user:3333",
                     "test_no_user:3306:/does/not/exist/mysql.sock",
                     "test_no_host:3333"]

        for test_ in con_tests:
            try:
                parse_connection(test_, options={"charset": "utf8"})
            except UtilError as err:
                self.results.append("{0}\n".format(err.errmsg))

        # remove socket information to have same output
        # on both posix and and windows operating systems.
        self.replace_substring_portion("port or ", "socket", "port")

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        self.remove_login_path_data('test_no_user')
        self.remove_login_path_data('test_no_host')
        return True
