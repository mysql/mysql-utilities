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
import sys
import unittest

from mysql.utilities.common.tools import check_connector_python

def connector_python_found():
    try:
        import mysql.connector
    except Exception:
        return True
    return False


@unittest.skipUnless(connector_python_found(),
                     "This test requires C/Py to be inaccessible. "
                     "Please run the test again without C/Py.")
class TestConnectorPython(unittest.TestCase):
    """Test that detection of Connector/Python is working.
    """
    def test_check_connector_python(self):
        """Test valid detection of missing connector/python.
        """
        res = check_connector_python(False)
        self.assertEqual(False, res, "Test found connector/python when it "
                         "should not have!")

if __name__ == '__main__':
    unittest.main()
