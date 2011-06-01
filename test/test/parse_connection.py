#!/usr/bin/env python

import os
import mysql_test
from mysql.utilities.exception import MySQLUtilError, MUTException, FormatError

_TEST_RESULTS = [
    # (comment, input, expected result, fail_ok)
    ('check an IP address', '192.168.1.198', '192.168.1.198', False),
    ('check a FQDN address 1 part', 'm1', 'm1', False),
    ('check a FQDN address 2 parts', 'm1.m2', 'm1.m2', False),
    ('check a FQDN address 3 parts', 'm1.m2.m3', 'm1.m2.m3', False),
    ('check a FQDN address 4 parts', 'm1.m2.m3.m4', 'm1.m2.m3.m4', False),
    ('check a host name with hyphen', 'host-hyphen', 'host-hyphen', False),
    ('check a host name with extra characters', 'a!(*%(*$*', 'a', False),
    ('check a host name with invalid characters', '-test', 'FAIL', True),
    ('check invalid host name #1', '-.ola--123-', 'FAIL', True),
    ('check invalid host name #2', '.ola--123-', 'FAIL', True),
    ('check invalid host name #3', '...ola--123-', 'FAIL', True),
    ('check invalid host name #4', '......this.is.an.invalid.host.name',
     'FAIL', True),
    # check for:
    # 1. labels ending with a number (valid)
    # 2. labels starting with a number (valid)
    # 3. labels with one hyphen (valid)
    # 4. labels with more than one hyphen in the name (valid)
    # 5. labels formatted with CamelCase 
    ('check invalid host name #5', 'label1.2label.label-3.label--4.LaBeL5.com', 'label1.2label.label-3.label--4.LaBeL5.com', False),
    ('check valid host name #6', '1m23','1m23', False),
    # according to rfc1123:
    # "However, a valid host name can never have the dotted-decimal form #.#.#.#, since at least the
    # highest-level component label will be alphabetic."
    # Thus the following must fail
    ('check invalid host name #7', '123', 'FAIL', True),
    #    ('check valid host name #7', '::192.0.2.128', '::192.0.2.128', False),
    
    # we leave out
    #   - 192.168.2.1.2.3 -- i.e. IPs with more than 4 labels
    #   - invalid IPs (256.256.256.256)
    #   - IPv6
]

class test(mysql_test.System_test):
    """check parse_connection()
    This test attempts to use parse_connection method for correctly parsing
    the connection parameters.
    """
    
    def check_prerequisites(self):
        return self.check_num_servers(0)
    
    def setup(self):
        return True
    
    def test_connection(self, test_num, test_data):
        from mysql.utilities.common.options import parse_connection
    
        if self.debug:
          print "\nTest case %s - %s" % (test_num+1, test_data[0])
      
        try:
            self.conn_vals = parse_connection("root@%s:3306" % test_data[1])
        except FormatError, e:
            if test_data[3]:
                # This expected. 
                self.results.append("FAIL")
            else:
                raise MUTException("Test Case %s: Parse failed! Error: %s" % \
                                   (test_num+1, e))
        else:
            if test_data[3]:            
                raise MUTException("Test Case %s: Parse should have failed. " \
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
