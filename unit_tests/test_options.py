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
        ]

    # These specifiers are invalid and should generate a FormatError.
    invalid_specificers = [
        'mats', 'mats@', '@localhost', 'mats:@localhost',
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
            self.assertRaises(FormatError, parse_connection, spec)
 
if __name__ == '__main__':
    unittest.main()
