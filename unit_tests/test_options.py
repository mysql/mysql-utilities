#
# Copyright (c) 2010, 2013, Oracle and/or its affiliates. All rights reserved.
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

from mysql.utilities.common.options import parse_connection
from mysql.utilities.exception import FormatError

def _spec(info):
    """Create a server specification string from an info structure."""
    result = [info['user']]
    if info.get('passwd', None):
        result.append(':' + info['passwd'])
    result.append('@' + info['host'])
    if 'port' in info:
        result.append(':' + str(info['port']))
    if "unix_socket" in info:
        result.append(":" + info["unix_socket"])
    return ''.join(result)

class TestParseConnection(unittest.TestCase):
    """Test that parsing connection strings work correctly.
    """
    # This list consists of input specifier and expected output
    # specifier. If the element is a simple string, the input is
    # expected as output.
    valid_specifiers = [
        ('mats@localhost', 'mats@localhost:3306'),
        ('mats@localhost:3307', 'mats@localhost:3307'), 
        ('mats:foo@localhost', 'mats:foo@localhost:3306'),
        ('mats:foo@localhost:3308', 'mats:foo@localhost:3308'),
        ('mats@localhost:3308:/usr/var/mysqld.sock', 'mats@localhost:3308:/usr/var/mysqld.sock'),
        ('mats:@localhost', 'mats@localhost:3306'),
        # IPv6 strings
        ("cbell@3ffe:1900:4545:3:200:f8ff:fe21:67cf", "cbell@3ffe:1900:4545:3:200:f8ff:fe21:67cf:3306"),
        ("cbell@fe80:0000:0000:0000:0202:b3ff:fe1e:8329", "cbell@fe80:0000:0000:0000:0202:b3ff:fe1e:8329:3306"),
        ("cbell@fe80:0:0:0:202:b3ff:fe1e:8329", "cbell@fe80:0:0:0:202:b3ff:fe1e:8329:3306"),
        ("cbell@'fe80::202:b3ff:fe1e:8329'", "cbell@fe80::202:b3ff:fe1e:8329:3306"),
        ("cbell@'fe80::0202:b3ff:fe1e:8329'", "cbell@fe80::0202:b3ff:fe1e:8329:3306"),
        ('cbell@"FE80::0202:B3FF:FE1E:8329"', "cbell@FE80::0202:B3FF:FE1E:8329:3306"),
        ('cbell@1:2:3:4:5:6:7:8', 'cbell@1:2:3:4:5:6:7:8:3306'),
        ("cbell@'E3D7::51F4:9BC8:192.168.100.32'", 'cbell@E3D7::51F4:9BC8:192.168.100.32:3306'),
        ("cbell@'E3D7::51F4:9BC8'", 'cbell@E3D7::51F4:9BC8:3306'),
        ]

    # These specifiers are invalid and should generate a FormatError.
    invalid_specificers = [
        'mats@', '@localhost', 'cbell@what:is::::this?',
        'cbell@1:2:3:4:5:6:192.168.1.110',
        'cbell@E3D7::51F4:9BC8:192.168.100.32',
        ]
    
    def test_valid(self):
        """Test parsing valid versions of connection strings.
        """
        for source, expected in self.valid_specifiers:
            result = _spec(parse_connection(source))
            frm = "{0}: was {1}, expected {2}"
            msg = frm.format(source, result, expected)
            self.assertEqual(expected, result, msg)

    def test_invalid(self):
        """Test parsing invalid versions of connection strings.

        If the connection string is invalid, a FormatError should be thrown.
        """
        for spec in self.invalid_specificers:
            try:
                parse_connection(spec)
            except FormatError:
                pass
            except:
                self.fail("Unexpected exception thrown.")
            else:
                self.fail("Exception not thrown for: '%s'." % spec)
 
if __name__ == '__main__':
    unittest.main()
