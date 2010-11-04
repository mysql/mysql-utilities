import unittest

from mysql.utilities.common.options import parse_connection
from mysql.utilities.exception import MySQLUtilError

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

valid_specifiers = [
    ('mats@localhost', 'mats@localhost:3306'),
    ('mats@localhost:3307', 'mats@localhost:3307'), 
    ('mats:foo@localhost', 'mats:foo@localhost:3306'),
    'mats:foo@localhost:3308',
    'mats@localhost:3308:/usr/var/mysqld.sock',
]

invalid_specificers = [
    'mats', 'mats@', '@localhost',
    'mats:@localhost',
]

class TestParseConnection(unittest.TestCase):
    def testValid(self):
        for spec in valid_specifiers:
            if isinstance(spec, tuple):
                source, expected = spec
            else:
                expected = spec
                source = spec
            self.assertEqual(expected, _spec(parse_connection(source)))

    def testInvalid(self):
        for spec in invalid_specificers:
            self.assertRaises(MySQLUtilError, parse_connection, spec)
 
def test_suite():
    return unittest.makeSuite(TestParseConnection, 'test')
