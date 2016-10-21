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
connection_values test.
"""

import os
import mutlib

from mysql.utilities.exception import (ConnectionValuesError, UtilError,
                                       FormatError, MUTLibError)
from mysql.utilities.common.server import (get_connection_dictionary,
                                           connect_servers,
                                           check_hostname_alias)

# List of tuples (comment, input, fail)
_TEST_CASES = [
    ('Good connection string but cannot connect',
     'root:pass@hostname.com:3306:/my.sock', True),
    ('Bad connection string', 'DAS*!@#MASD&UKKLKDA)!@#', True),
    ('Good dictionary but cannot connect',
     {'user': 'root', 'passwd': 'pass', 'host': 'localhost',
      'port': '3306', 'unix_socket': '/my.sock'}, True),
    ('Bad dictionary', {'something': 'else'}, True),
]


class test(mutlib.System_test):
    """check connection_values()
    This test attempts to use the connect_servers method for using multiple
    parameter types for connection (dictionary, connection string, class).
    """

    server0 = None
    server1 = None
    server2 = None

    def check_prerequisites(self):
        if os.name == 'nt':
            raise MUTLibError("Test requires a non-Windows platform.")
        return self.check_num_servers(1)

    def setup(self):
        self.server0 = self.servers.get_server(0)
        # Check if the required tools are accessible
        self.check_mylogin_requisites()

        self.servers.spawn_new_servers(2)
        self.server1 = self.servers.get_server(0)
        self.server2 = self.servers.get_server(1)
        server1_socket = self.server1.show_server_variable('socket')
        try:
            self.server1.exec_query("DROP USER 'root_me'@'localhost'")
        except:
            pass   # Ok if user doesn't exist
        self.server1.exec_query("CREATE USER 'root_me'@'localhost'")
        self.server1.exec_query("GRANT ALL ON *.* TO 'root_me'@'localhost'")
        self.create_login_path_data('test_server1', 'root_me',
                                    'localhost', None,
                                    "'{0}'".format(server1_socket[0][1]))
        server2_socket = self.server2.show_server_variable('socket')
        try:
            self.server2.exec_query("DROP USER 'root_me'@'localhost'")
        except:
            pass   # Ok if user doesn't exist
        self.server2.exec_query("CREATE USER 'root_me'@'localhost'")

        self.server2.exec_query("GRANT ALL ON *.* TO 'root_me'@'localhost'")
        self.create_login_path_data('test_server2', 'root_me',
                                    'localhost', None,
                                    "'{0}'".format(server2_socket[0][1]))

        _TEST_CASES.append(("Valid connection string.",
                            self.build_connection_string(self.server1),
                            False))
        _TEST_CASES.append(("Valid dictionary.",
                            self.servers.get_connection_values(self.server1),
                            False))
        _TEST_CASES.append(("Valid class.", self.server1, False))
        _TEST_CASES.append(("Wrong type passed.", 11, True))
        _TEST_CASES.append(("Wrong string passed.", "Who's there?", True))
        _TEST_CASES.append(("Wrong class passed.", self, True))
        _TEST_CASES.append(("Use .login-path with socket only", "test_server1",
                            False))
        return True

    def run(self):
        for i in range(0, len(_TEST_CASES)):
            if self.debug:
                print "\nTest case {0} - {1}".format(i + 1, _TEST_CASES[i][0])
            try:
                src_val = get_connection_dictionary(_TEST_CASES[i][1])
                server_options = {'quiet': True, 'version': None,
                                  'src_name': "test", 'dest_name': None, }
                connect_servers(src_val, None, server_options)
            except UtilError as err:
                self.results.append((True, err.errmsg))
            except ConnectionValuesError as err:
                self.results.append((True, err.errmsg))
            except FormatError as err:
                self.results.append((True, err))
            else:
                self.results.append((False, ''))
            if self.debug:
                print "Test results:", self.results[i][0], self.results[i][1]

        test_num = len(_TEST_CASES) + 1
        comment = "Compare dictionaries with socket only"

        if self.debug:
            print "\nTest case {0} - {1}".format(test_num, comment)
        server1_vals = get_connection_dictionary("test_server1")
        server1_vals['port'] = None
        server2_vals = get_connection_dictionary("test_server2")
        server2_vals['port'] = None
        res = check_hostname_alias(server1_vals, server2_vals)
        # Add test case so that results match.
        _TEST_CASES.append((comment, "test_server1", False))
        self.results.append((res, ''))

        if self.debug:
            print "Test results:", res, False

        self.remove_login_path_data('test_server1')
        self.remove_login_path_data('test_server2')

        return True

    def get_result(self):
        if len(self.results) != len(_TEST_CASES):
            return False, "Invalid number of test case results."

        for i in range(0, len(_TEST_CASES)):
            if self.results[i][0] != _TEST_CASES[i][2]:
                msg = ("Got wrong result for test case {0}. "
                       "Expected: {1}, got: {2}.".format(
                           i + 1, _TEST_CASES[i][2], self.results[i][0]))
                if self.results[i][1] == '':
                    errors = (msg, '')
                else:
                    errors = (msg, "\nException: {0}.".format(
                        self.results[i][1]))
                return False, errors

        return True, None

    def record(self):
        return True

    def cleanup(self):
        # Kill all spawned servers.
        if self.server1:
            self.server1.exec_query("DROP USER 'root_me'@'localhost'")
        if self.server2:
            self.server2.exec_query("DROP USER 'root_me'@'localhost'")
        return True
