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

from mysql.utilities.common.tools import requires_encoding, encode
from mysql.utilities.common.tools import requires_decoding, decode

class TestDecodeEncode(unittest.TestCase):
    """Test that decode and encode strings work correctly.
    """
    # This list consists of decoded string and expected encoded string
    test_cases = [
        ('this.has.periods', 'this@002ehas@002eperiods'),
        ('me.too.periods', 'me@002etoo@002eperiods'),
        ('abc.kk-d.e-f', 'abc@002ekk@002dd@002ee@002df'),
        # sanity check to show this does not need encoding/decoding
        ('sanity$che_ck', 'sanity$che_ck'),
    ]

    def test_decode_encode(self):
        """Test valid encode/decode conversions of strings.
        """
        for enc_str, dec_str in self.test_cases:
            frm = "{0}: was {1}, expected {2}"
            # First, do encode
            result = encode(enc_str)
            msg = frm.format(enc_str, result, dec_str)
            self.assertEqual(dec_str, result, msg)
            # Now, do decode
            result = decode(dec_str)
            msg = frm.format(enc_str, result, dec_str)
            self.assertEqual(enc_str, result, msg)

if __name__ == '__main__':
    unittest.main()
