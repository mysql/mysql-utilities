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
import os
import mutlib
from mysql.utilities.exception import MUTLibError, FormatError
from mysql.utilities.common.options import parse_connection

_TEST_RESULTS = [
    # (comment, input, expected result, fail_ok)
    
    # Quoted hostname tests
    ('check quoted host name #1', "'mysql.com'", 'mysql.com', False),
    ('check quoted host name #2', "'mysql.com':socket", 'mysql.com', False),
    ('check quoted host name #3', '"mysql.com"' , 'mysql.com', False),
    ('check quoted host name #4',
         '"bk-internal.mysql.com"', 'bk-internal.mysql.com', False),
    
    # IPv4 positive tests
    # check for:
    # 1. labels ending with a number (valid)
    # 2. labels starting with a number (valid)
    # 3. labels with one hyphen (valid)
    # 4. labels with more than one hyphen in the name (valid)
    # 5. labels formatted with CamelCase 
    ('check an IP address', '192.168.1.198', '192.168.1.198', False),
    ('check a FQDN address 1 part', 'm1', 'm1', False),
    ('check a FQDN address 2 parts', 'm1.m2', 'm1.m2', False),
    ('check a FQDN address 3 parts', 'm1.m2.m3', 'm1.m2.m3', False),
    ('check a FQDN address 4 parts', 'm1.m2.m3.m4', 'm1.m2.m3.m4', False),
    ('check a host name with hyphen', 'host-hyphen', 'host-hyphen', False),
    ('check a host name with extra characters', 'a!(*%(*$*', 'a', False),
    ('check valid host name #1', '1m23','1m23', False),
    ('check valid host name #2',
        'label1.2label.label-3.label--4.LaBeL5.com',
        'label1.2label.label-3.label--4.LaBeL5.com', False),
    
    # IPv4 negative tests
    ('check a host name with invalid characters', '-test', 'FAIL', True),
    ('check invalid host name #1', '-.ola--123-', 'FAIL', True),
    ('check invalid host name #2', '.ola--123-', 'FAIL', True),
    ('check invalid host name #3', '...ola--123-', 'FAIL', True),
    # according to rfc1123:
    # "However, a valid host name can never have the dotted-decimal
    # form #.#.#.#, since at least the highest-level component label
    # will be alphabetic." Thus the following must fail:
    ('check invalid host name #4',
        '......this.is.an.invalid.host.name', 'FAIL', True),
    ('check invalid host name #5', '123', 'FAIL', True),
    
    # IPv6 positive tests
    ('check valid IPv6 #1',
        "3ffe:1900:4545:3:200:f8ff:fe21:67cf",
        "3ffe:1900:4545:3:200:f8ff:fe21:67cf", False),

    # normal
    ('check valid IPv6 #2',
        "fe80:0000:0000:0000:0202:b3ff:fe1e:8329",
        "fe80:0000:0000:0000:0202:b3ff:fe1e:8329", False),

    # removing leading zeros
    ('check valid IPv6 #3',
        "fe80:0:0:0:202:b3ff:fe1e:8329",
        "fe80:0:0:0:202:b3ff:fe1e:8329", False),

    # collapsed - need to quote these
    ('check valid IPv6 #4',
        "'fe80::202:b3ff:fe1e:8329'", "fe80::202:b3ff:fe1e:8329", False),

    ('check valid IPv6 #5',
        "'fe80::0202:b3ff:fe1e:8329'", "fe80::0202:b3ff:fe1e:8329", False),

    ('check valid IPv6 #6',
        '"FE80::0202:B3FF:FE1E:8329"', "FE80::0202:B3FF:FE1E:8329", False),
    
    ('check valid IPv6 #7',
        '1:2:3:4:5:6:7:8', '1:2:3:4:5:6:7:8', False),

    # IPv6 negative tests
    ('check invalid IPv6 #1', '::192.0.2.128', '::192', False), # truncation

    ('check invalid IPv6 #2',
        'what:is::::this?', 'FAIL', True),

    ('check invalid IPv6 #3',
        '::0:WHAT:1.2.3.4', '::0', False), # truncation
    
    ('check invalid IPv6 #4',
        '1:2:3:4:5:6:192.168.1.110', 'FAIL', True),
    
    # Show we can do mixed only with quoted string
    ('check valid IPv6 - mixed #1',
        'E3D7::51F4:9BC8:192.168.100.32', 'FAIL', True),

    ('check valid IPv6 - mixed #2',
        "'E3D7::51F4:9BC8:192.168.100.32'",
        'E3D7::51F4:9BC8:192.168.100.32', False),

    ('check valid IPv6 - mixed #3 (without IPv4 suffix)',
        "'E3D7::51F4:9BC8'", 'E3D7::51F4:9BC8', False),

    # we leave out
    #   - 192.168.2.1.2.3 -- i.e. IPs with more than 4 labels
    #   - invalid IPs (256.256.256.256)
    #   - collapsed IPv6 but can be quoted.
]

class test(mutlib.System_test):
    """check parse_connection()
    This test attempts to use parse_connection method for correctly parsing
    the connection parameters.
    """
    
    def check_prerequisites(self):
        return self.check_num_servers(0)
    
    def setup(self):
        return True
    
    def test_connection(self, test_num, test_data):
    
        if self.debug:
          print "\nTest case %s - %s" % (test_num+1, test_data[0])
      
        try:
            self.conn_vals = parse_connection("root@%s:3306" % test_data[1])
        except FormatError, e:
            if test_data[3]:
                # This expected. 
                self.results.append("FAIL")
            else:
                raise MUTLibError("Test Case %s: Parse failed! Error: %s" % \
                                   (test_num+1, e))
        else:
            if test_data[3]:            
                raise MUTLibError("Test Case %s: Parse should have failed. " \
                                   "Got this instead: %s" % \
                                   (test_num+1, self.conn_vals['host']))
            else:
                self.results.append(self.conn_vals['host'])
        
    def run(self):
        for i in range(0,len(_TEST_RESULTS)):
            self.test_connection(i, _TEST_RESULTS[i])
            if self.debug:
                print "Comparing result for test case %s: %s == %s" % \
                      (i+1, _TEST_RESULTS[i][2], self.results[i])
                if _TEST_RESULTS[i][3]:
                    print "Test case is expected to fail."
        #try:
        #    self.conn_vals = parse_connection("root:pass@'mysql.com':3306:/socketfile")
        #    print "HERE:", self.conn_vals
        #except FormatError, e:
        #    raise MUTLibError("Test Case XX: Parse failed! Error: %s" % \
        #                       (99, e))
        #
        return True
    
    def get_result(self):
        if len(self.results) != len(_TEST_RESULTS):
            return (False, ("Invalid number of test case results."))
    
        for i in range(0, len(_TEST_RESULTS)):
            if not self.results[i] == _TEST_RESULTS[i][2]:
                return (False, ("Got wrong result for test case %s." % (i+1) + \
                                " Expected: %s, got: %s." % \
                                (_TEST_RESULTS[i][2], self.results[i])))
        
        return (True, None)
    
    def record(self):
        return True
    
    def cleanup(self):
        return True
