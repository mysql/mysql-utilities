#
# Copyright (c) 2013, 2014 Oracle and/or its affiliates. All rights reserved.
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

import os
import unittest

from mysql.utilities.common.console import _WIN_COMMAND_KEY
from mysql.utilities.command.utilitiesconsole import UtilitiesConsole


_BASE_DIR, _ = os.path.split(os.path.abspath(os.path.dirname(__file__)))
_UTIL_DIR = os.path.join(_BASE_DIR, "scripts")

class TestUtilitiesConsole(unittest.TestCase):
    """Test Case class for the Utilities Console"""

    def setUp(self):
        options = {
            'verbosity': False,
            'quiet': False,
            'width': 80,
            'utildir': _UTIL_DIR,
            'variables': [],
            'prompt': '>',
            'welcome': "",
            'goodbye': "",
            'commands': [],
            'custom': True,
            'hide_util': False,
            'add_util': []
        }
        self.util_con = UtilitiesConsole(options)

    def test_strange_keyboard_input(self):
        test_cases = {'R': "INSERT_KEY", 'G': 'HOME_KEY', 'O': 'END_KEY',
                      'I': 'PAGE_UP_KEY', 'Q': 'PAGE_DOWN_KEY'}

        for key in test_cases:
            self.assertEqual(_WIN_COMMAND_KEY.get(key), None)

    def test_backspace_beginning(self):
        """Test console response to BACKSPACE KEY when the cursor
        is at the beginning of the line.
        """

        test_cases = ['BACKSPACE_POSIX', 'BACKSPACE_WIN']
        self.util_con.cmd_line.command = "12345"
        self.util_con.cmd_line.length = 5
        self.util_con.cmd_line.position = 0
        for key in test_cases:
            self.util_con._process_command_keys(key)
            self.assertEqual("12345", self.util_con.cmd_line.command)

    def test_backspace_middle(self):
        """Test console response to BACKSPACE KEY when the cursor
        is in the middle of the line.
        """

        self.util_con.cmd_line.command = "12345"
        self.util_con.cmd_line.length = 5
        self.util_con.cmd_line.position = 3
        self.util_con._process_command_keys('BACKSPACE_POSIX')
        self.assertEqual("1245", self.util_con.cmd_line.command)
        self.util_con._process_command_keys('BACKSPACE_WIN')
        self.assertEqual("145", self.util_con.cmd_line.command)

    def test_backspace_end(self):
        """Test console response to BACKSPACE KEY when the cursor
        is in the end of the line.
        """

        self.util_con.cmd_line.command = "12345"
        self.util_con.cmd_line.length = 5
        self.util_con.cmd_line.position = 5
        self.util_con._process_command_keys('BACKSPACE_POSIX')
        self.assertEqual("1234", self.util_con.cmd_line.command)
        self.util_con._process_command_keys('BACKSPACE_WIN')
        self.assertEqual("123", self.util_con.cmd_line.command)

if __name__ == '__main__':
    unittest.main()
