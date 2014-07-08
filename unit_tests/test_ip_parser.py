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
"""
This file contains unit tests for the ip_parser module.
"""
import os
import unittest

from mysql.utilities.common.ip_parser import parse_connection
from mysql.utilities.exception import UtilError

_TEST_UNKNOWN_LOGIN_PATH = 'unknown_login_path'


class TestIpParser(unittest.TestCase):

    def test_parse_connection(self):
        # Set invalid environment variable to fail locating '.mylogin.cnf'.
        # For safety, store the HOME or APPDATA (to be restored at the end).
        if os.name == 'posix':
            env_home = os.environ['HOME']
            os.environ['HOME'] = 'invalid_home'
        else:
            env_appdata = os.environ['APPDATA']
            os.environ['APPDATA'] = 'invalid_appdata'
        try:
            # Error: file .mylogin.cnf not found.
            self.assertRaises(UtilError, parse_connection,
                              _TEST_UNKNOWN_LOGIN_PATH)
        finally:
            # Restore the HOME or APPDATA (previously stored).
            if os.name == 'posix':
                os.environ['HOME'] = env_home
            else:
                os.environ['APPDATA'] = env_appdata

if __name__ == "__main__":
    unittest.main()
