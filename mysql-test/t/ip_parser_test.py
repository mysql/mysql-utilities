#Copyright (c) 2013, 2014, Oracle and/or its affiliates. All rights reserved.
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
ip_parser_test test.
"""

import os
import re

import mutlib

from mysql.utilities.exception import MUTLibError
from mysql.utilities.exception import FormatError

import mysql.utilities.common.ip_parser as ip_parser


EXCEPTION_MSG_UNPARSED = "not parsed completely"
EXCEPTION_MSG_CANNOT_PARSE = "cannot be parsed"

_PARSED = re.compile(""".*[',"](.*?)[',"].*[',"](.*)[',"].*""", re.VERBOSE)

_NONE = False

_IPv4_TEST_CASES = (("127.0.0.1", (_NONE, "127.0.0.1", None, None)),
                    ("127.0.0.1:3306", (_NONE, "127.0.0.1", "3306", None)),
                    ("0.0.0.1", (_NONE, "0.0.0.1", None, None)),
                    ("0.0.0.1:3306", (_NONE, "0.0.0.1", "3306", None)),
                    )

_IPv6_TEST_CASES = (
    ("0:1:2:3:4:5:6:7", (_NONE, "[0:1:2:3:4:5:6:7]", None, None)),
    ("[0:1:2:3:4:5:6:7]", (_NONE, "[0:1:2:3:4:5:6:7]", None, None)),
    ("0:1:2:3:4:5:6:7:3306", (_NONE, "[0:1:2:3:4:5:6:7]", "3306", None)),
    ("[0:1:2:3:4:5:6:7]:3306", (_NONE, "[0:1:2:3:4:5:6:7]", "3306", None)),
    ("0:1:2:3:4:5:6:7:3306:/a/b/mysql.socket",
     (_NONE, "[0:1:2:3:4:5:6:7]", "3306", "/a/b/mysql.socket")),
    ("[0:1:2:3:4:5:6:7]:3306:/a/b/mysql.socket",
     (_NONE, "[0:1:2:3:4:5:6:7]", "3306", "/a/b/mysql.socket")),
    ("0::7", (_NONE, "[0::7]", None, None)),
    ("::7", (_NONE, "[::7]", None, None)),
    ("::", (_NONE, "[::]", None, None)),
    ("[::1]", (_NONE, "[::1]", None, None)),
    ("[::1]:", (_NONE, "[::1]", None, None,)),
    ("[::1]:3306", (_NONE, "[::1]", "3306", None)),
    ("[::1]:/a/b/mysql.socket", (_NONE, "[::1]", '', "/a/b/mysql.socket")),
    ("[::1]:3306:/a/b/mysql.socket",
     (_NONE, "[::1]", "3306", "/a/b/mysql.socket")),

    ("2001:db8::1:2", (_NONE, "[2001:db8::1:2]", None, None)),
    ("2001:db8::1:2:3306", (_NONE, "[2001:db8::1:2:3306]", None, None)),
    ("[0001:0002:0003:0004:0005:0006:0007:0008]:3306",
     (_NONE, "[0001:0002:0003:0004:0005:0006:0007:0008]", "3306", None)),
    ("0001:0002:0003:0004:0005:0006:0007:0008:3306",
     (_NONE, "[0001:0002:0003:0004:0005:0006:0007:0008]", "3306", None)),
    ("[001:2:3:4:5:6:7:8]:3306", (_NONE, "[001:2:3:4:5:6:7:8]", "3306", None)),
    ("001:2:3:4:5:6:7:8:3306", (_NONE, "[001:2:3:4:5:6:7:8]", "3306", None)),
    ("[2001:db8::1:2]:3306", (_NONE, "[2001:db8::1:2]", "3306", None)),
    ("1234:abcd:abcd:abcd:abcd:abcd:abcd:abcd",
     (_NONE, "[1234:abcd:abcd:abcd:abcd:abcd:abcd:abcd]", None, None)),
    ("fedc:abcd:abcd:abcd:abcd:abcd:abcd:abcd",
     (_NONE, "[fedc:abcd:abcd:abcd:abcd:abcd:abcd:abcd]", None, None)),
    ("fedc::abcd", (_NONE, "[fedc::abcd]", None, None)),
    ("0a:b:c::d", (_NONE, "[0a:b:c::d]", None, None)),
    ("abcd:abcd::abcd", (_NONE, "[abcd:abcd::abcd]", None, None)),
    ("[0a:b:c::d]", (_NONE, "[0a:b:c::d]", None, None)),
    ("[abcd:abcd::abcd]", (_NONE, "[abcd:abcd::abcd]", None, None)),
    ("[0:1:2:3:4:5:6:7]:3306", (_NONE, "[0:1:2:3:4:5:6:7]", "3306", None)),
    ("[0:1:2:3:4:5::7]:3306", (_NONE, "[0:1:2:3:4:5::7]", "3306", None)),
    ("[0:1:2:3:4::6:7]:3306", (_NONE, "[0:1:2:3:4::6:7]", "3306", None)),
    ("[0:1:2:3::5:6:7]:3306", (_NONE, "[0:1:2:3::5:6:7]", "3306", None)),
    ("[0:1:2::4:5:6:7]:3306", (_NONE, "[0:1:2::4:5:6:7]", "3306", None)),
    ("[0:1::3:4:5:6:7]:3306", (_NONE, "[0:1::3:4:5:6:7]", "3306", None)),
    ("[0::2:3:4:5:6:7]:3306", (_NONE, "[0::2:3:4:5:6:7]", "3306", None)),
    ("[fe80::202:b3ff:fe1e:8329]:3306",
     (_NONE, "[fe80::202:b3ff:fe1e:8329]", "3306", None)),
    ("fe80::202:b3ff:fe1e:8329",
     (_NONE, "[fe80::202:b3ff:fe1e:8329]", None, None)),
    ("[0:1:2:3:4::7]:3306", (_NONE, "[0:1:2:3:4::7]", "3306", None)),
    ("[0:1:2:3::7]:3306", (_NONE, "[0:1:2:3::7]", "3306", None)),
    ("[0:1:2::7]:3306", (_NONE, "[0:1:2::7]", "3306", None)),
    ("[0:1::7]:3306", (_NONE, "[0:1::7]", "3306", None)),
    ("[0::7]:3306", (_NONE, "[0::7]", "3306", None))
)

_BAD_IPv4_TEST_CASES = (
    ("127.0.0", (EXCEPTION_MSG_CANNOT_PARSE, None, None, None)),
    ("1234.0.0.1:3306", (EXCEPTION_MSG_CANNOT_PARSE, None, None, None)),
    ("0.0.0.a", (EXCEPTION_MSG_CANNOT_PARSE, None, None, None)),
    ("0.b.0.1:3306", (EXCEPTION_MSG_CANNOT_PARSE, None, None, None)),
    ("0.0.c.1:3306", (EXCEPTION_MSG_CANNOT_PARSE, None, None, None)),
    ("012.345.678.910",
     (EXCEPTION_MSG_CANNOT_PARSE, "012.345.678.910", None, None)),
)

_BAD_IPv6_TEST_CASES = (
    ("127::2::1", (EXCEPTION_MSG_CANNOT_PARSE, None, None, None)),
    ("1234.12345::0.1:3306", (EXCEPTION_MSG_CANNOT_PARSE, None, None, None)),
    ("1:2:3:4.0", (EXCEPTION_MSG_CANNOT_PARSE, None, None, None)),
    ("1:abcdf::g", (EXCEPTION_MSG_CANNOT_PARSE, None, None, None)),
    ("[g:b:c:d:e:f]", (EXCEPTION_MSG_CANNOT_PARSE, None, None, None)),
)

_HN_TEST_CASES = (
    ("localhost", (_NONE, "localhost", None, None)),
    ("localhost:3306", (_NONE, "localhost", "3306", None)),
    ("localhost:3306:/var/lib/mysql.sock",
     (_NONE, "localhost", "3306", "/var/lib/mysql.sock")),
    ("oracle.com", (_NONE, "oracle.com", None, None)),
    ("oracle.com:3306", (_NONE, "oracle.com", "3306", None)),
    ("www.oracle.com:3306", (_NONE, "www.oracle.com", "3306", None)),
    ("this-is-mysite.com",
     (_NONE, "this-is-mysite.com", None, None)),
    ("w-w.this-site.com-com:3306",
     (_NONE, "w-w.this-site.com-com", "3306", None)),
    ("0DigitatBegining", (_NONE, "0DigitatBegining", None, None)),
    ("0DigitatBegining:3306", (_NONE, "0DigitatBegining", "3306", None)),
    ("0-w-w.this-site.c-om", (_NONE, "0-w-w.this-site.c-om", None, None)),
    ("0-w-w.this-site.c-om:3306",
     (_NONE, "0-w-w.this-site.c-om", "3306", None)),
    ("ww..this-site.com",
     (_NONE, "ww", "", "..this-site.com", "..this-site.com")),
)

_BAD_HN_TEST_CASES = (
    ("local#host:3306",
     (EXCEPTION_MSG_UNPARSED, "local", None, "#host", ":3306")),
    ("local#host:3306:/var/lib/mysql.sock",
     (EXCEPTION_MSG_UNPARSED, "local", None, "#host",
      ":3306:/var/lib/mysql.sock")),
    ("oracle.com/mysql:3306",
     (EXCEPTION_MSG_UNPARSED, "oracle.com", None, "/mysql", ":3306")),
    ("yo@oracle.com:3306",
     (EXCEPTION_MSG_UNPARSED, "yo", None, None, "@oracle.com:3306")),
    ("yo:pass@127.0.0.1",
     (EXCEPTION_MSG_UNPARSED, "yo", None, "pass", "@127.0.0.1")),
    ("-no this-mysite.com", (EXCEPTION_MSG_CANNOT_PARSE, None, None, None)),
)

_ANY_LIKE_TEST_CASES = (
    ("%", (_NONE, "%", None, None)),
    ("dataserver%33066mysql.sock",
     (_NONE, "dataserver%", "33066", "mysql.sock",)),
    ("dataserver%:3306", (_NONE, "dataserver%", "3306", None)),
    ("dataserver%:3306:/folder/mysql.sock",
     (_NONE, "dataserver%", "3306", "/folder/mysql.sock",)),
)

_BAD_ANY_LIKE_TEST_CASES = (
    ("dataserver%.com/mysql:3306",
     (EXCEPTION_MSG_UNPARSED, "dataserver%", None, ".com/mysql", ":3306")),
    ("data%server%:3306:/folder/mysql.sock",
     (EXCEPTION_MSG_UNPARSED, "data%", None, "server",
      "%:3306:/folder/mysql.sock")),
    ("dat?%:3306:/folder/mysql.sock",
     (EXCEPTION_MSG_UNPARSED, "dat", None, None,
      "?%:3306:/folder/mysql.sock",)),
)


class test(mutlib.System_test):
    """check the correct parsing of IPv4, IPV6 and domain names.
    """

    def check_prerequisites(self):
        return True

    def setup(self):
        return True

    def run_test_cases(self):
        """Run test cases.
        """
        test_number = 0
        for test_case in _IPv4_TEST_CASES:
            test_number += 1
            self.run_test_case(ip_parser.ipv4, test_case, test_number)

        test_number = 0
        for test_case in _IPv6_TEST_CASES:
            test_number += 1
            self.run_test_case(ip_parser.ipv6, test_case, test_number)

        test_number = 0
        for test_case in _BAD_IPv4_TEST_CASES:
            test_number += 1
            self.run_test_case("BAD {0}".format(ip_parser.ipv4), test_case,
                               test_number)

        test_number = 0
        for test_case in _BAD_IPv6_TEST_CASES:
            test_number += 1
            self.run_test_case("BAD {0}".format(ip_parser.ipv6), test_case,
                               test_number)

        test_number = 0
        for test_case in _HN_TEST_CASES:
            test_number += 1
            self.run_test_case(ip_parser.HN, test_case, test_number)

        test_number = 0
        for test_case in _BAD_HN_TEST_CASES:
            test_number += 1
            self.run_test_case("BAD {0}".format(ip_parser.HN), test_case,
                               test_number)

        test_number = 0
        for test_case in _ANY_LIKE_TEST_CASES:
            test_number += 1
            self.run_test_case(ip_parser.ANY_LIKE, test_case, test_number)

        test_number = 0
        for test_case in _BAD_ANY_LIKE_TEST_CASES:
            test_number += 1
            self.run_test_case("BAD {0}".format(ip_parser.ANY_LIKE), test_case,
                               test_number)

    # pylint: disable=W0221
    def run_test_case(self, test_type, test_case, test_number):
        comment = "Test case {0} - check {1} as type {2} ".format(
            test_number, test_case[0], test_type)

        # Get an Exception is OK unless is not expected.
        expected_exception = test_case[1][0]
        expected_host = str(test_case[1][1])
        expected_port = str(test_case[1][2])
        expected_socket = str(test_case[1][3])

        exception_found = False
        parse_conn = ip_parser.parse_server_address
        try:
            host, port, socket, add_type = parse_conn(test_case[0])
            if add_type != test_type:
                reason = (" ".join(
                    ["\n", "expecting:", "type:", test_type, "but", "found:",
                     str(add_type), "instead"]))
                raise MUTLibError("{0}: failed\n {1}".format(comment, reason))

            if str(host) != expected_host:
                reason = (" ".join(
                    ["\n", "expecting:", "host:", expected_host, "but",
                     "found:", str(host), "instead"]))
                raise MUTLibError("{0}: failed\n {1}".format(comment, reason))

            if str(port) != expected_port:
                reason = (" ".join(
                    ["\n", "expecting:", "port:", expected_port, "but",
                     "found:", str(port), "instead"]))
                raise MUTLibError("%s: failed\n %s" % (comment, reason))

            if str(socket) != expected_socket:
                reason = (" ".join(
                    ["\n", "expecting:", "socket:", expected_socket, "but",
                     "found:", str(socket), "instead"]))
                raise MUTLibError("{0}: failed\n {1}".format(comment, reason))

        except FormatError as err:
            # Verify the exception messages:
            if expected_exception and expected_exception in str(err):
                if expected_exception == EXCEPTION_MSG_UNPARSED:
                    result = _PARSED.match(str(err))
                    if (result and len(test_case[1]) == 5 and
                            result.groups()[1] == test_case[1][4]):
                        exception_found = True
                else:
                    if (expected_exception == EXCEPTION_MSG_CANNOT_PARSE and
                            test_case[0] in str(err)):
                        exception_found = True
            else:
                reason = ("An unexpected FormatError exception found:\n "
                          "{0!r}".format(err))
                raise MUTLibError("{0}: failed\n {1}".format(comment, reason))
        if expected_exception and not exception_found:
            reason = ("An expected FormatError exception not"
                      " found as expected :\n {0!r}".format(test_case))
            self.results.append("{0}: failed\n {1}\n".format(comment, reason))
            raise MUTLibError("{0}: failed\n {1}".format(comment, reason))

    def run(self):
        self.res_fname = "result.txt"
        with open(self.res_fname, 'w'):
            self.run_test_cases()
            self.results.append("Pass\n")
        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        if self.res_fname:
            os.unlink(self.res_fname)
        return True
