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
from mysql.utilities.exception import UtilError, MUTLibError


class test(mutlib.System_test):
    """Test the login-path authentication mechanism.
    This module tests the access to the .mylogin.cnf file and the use of the
    parse_connection method when specifying a login-path (instead of the user,
    password and localhost in plain text).
    """

    def check_prerequisites(self):
        # Check server version
        if not self.servers.get_server(0).check_version_compat(5, 6, 11):
            raise MUTLibError("Test requires server version >= 5.6.11")

        # Check if the required tools are accessible
        self.check_mylogin_requisites()

        # Check the required number of servers
        return self.check_num_servers(0)

    def setup(self):
        self.create_login_path_data('test_user_only', 'test_user', None,
                                    None, None)
        self.create_login_path_data('test_host_only', None, 'localhost',
                                    None, None)
        self.create_login_path_data("test_port_only", None, None, 13000, None)
        self.create_login_path_data("test_socket_only", None, None, None,
                                    "/does/not/exist/mysql.sock")
        return True

    def run(self):
        # Test parse_connection with login-paths missing parameters.
        con_tests = ["test_user_only", "test_host_only", "test_port_only",
                     "test_user_only:3306", "test_host_only:3306",
                     "test_host_only:3306:/does/not/exist/mysql.sock",
                     "test_port_only:3306"]

        for test_ in con_tests:
            try:
                parse_connection(test_)
            except UtilError as err:
                self.results.append("{0}\n".format(err.errmsg))

        # Test login-paths only with socket information separately
        # and change the output to be the same on both Windows and Posix
        # operating systems.

        # Missing username
        try:
            if os.name == "posix":
                parse_connection("test_socket_only")
            else:
                parse_connection("test_host_only:3306")
        except UtilError as err:
                self.results.append("{0}\n".format(err.errmsg))

        # on posix systems if we use socket, and there is no hostname,
        # hostname is assumed to be "localhost". So it is equivalent
        # to have a host and a port on windows systems.
        try:
            if os.name == "posix":
                parse_connection("test_port_only:/does/not/exist/mysql.sock")
            else:
                parse_connection("test_host_only:3306")
        except UtilError as err:
                self.results.append("{0}\n".format(err.errmsg))

        # remove socket warnings to have same output
        # on both posix and windows operating systems.
        self.replace_substring_portion("port or ", "socket", "port")
        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        self.remove_login_path_data('test_user_only')
        self.remove_login_path_data('test_host_only')
        self.remove_login_path_data('test_port_only')
        self.remove_login_path_data('test_socket_only')
        return True
