#
# Copyright (c) 2016 Oracle and/or its affiliates. All rights reserved.
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
This files contains unit tests for parsing the server version.
"""
import unittest

from mysql.utilities.common.tools import parse_mysqld_version

version_list = [
    ("mysqld  Ver 5.5.49 for Linux on x86_64 (Source distribution)",
     ('5','5','49')),
    ("mysqld  Ver 5.6.30 for Linux on x86_64 (Source distribution)",
     ('5','6','30')),
    ("mysqld  Ver 5.7.13-0ubuntu0.16.04.2 for Linux on x86_64 ((Ubuntu))",
     ('5','7','13')),
    ("mysqld  Ver 5.7.16-enterprise-commercial-advanced for linux-glibc2.5"
     " on x86_64 (MySQL Enterprise Server - Advanced Edition (Commercial))",
     ('5','7','16')),
]


class TestServerVersion(unittest.TestCase):

    def test_valid(self):
        for version in version_list:
            result = parse_mysqld_version(version[0])
            frmt = u"{0}: was {1}, expected {2}"
            msg = frmt.format(version[0], result, version[1])
            self.assertEqual(version[1], result, msg)

if __name__ == "__main__":
    unittest.main()
