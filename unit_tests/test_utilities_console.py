#
# Copyright (c) 2013, Oracle and/or its affiliates. All rights reserved.
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

import unittest

from mysql.utilities.common.console import _WIN_COMMAND_KEY


class TestUtilitiesConsole(unittest.TestCase):
    """Test Case class for the Utilities Console"""

    def test_strange_keyboard_input(self):
        test_cases = {'R':"INSERT_KEY", 'G':'HOME_KEY', 'O':'END_KEY',
                      'I':'PAGE_UP_KEY', 'Q':'PAGE_DOWN_KEY'}

        for key in test_cases:
            self.assertEqual(_WIN_COMMAND_KEY.get(key), None)

if __name__ == '__main__':
    unittest.main()
