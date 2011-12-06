#!/usr/bin/env python

import os
import mutlib
from mysql.utilities.exception import UtilError, MUTLibError, FormatError
from mysql.utilities.common.server import get_connection_dictionary, connect_servers

_TEST_CASES = [
    # (comment, input, fail)
    ('Good connection string but cannot connect',
     'root:pass@hostname.com:3306:/my.sock', True),
    ('Bad connection string', 'DAS*!@#MASD&UKKLKDA)!@#', True),
    ('Good dictionary but cannot connect',
     {'user':'root', 'passwd':'pass', 'host':'localhost', 'port':'3306',
      'unix_socket':'/my.sock'}, True),
    ('Bad dictionary', {'something':'else'}, True),
]

class test(mutlib.System_test):
    """check connection_values()
    This test attempts to use the connect_servers method for using multiple
    parameter types for connection (dictionary, connection string, class).
    """
    
    def check_prerequisites(self):
        return self.check_num_servers(1)
    
    def setup(self):
        self.server0 = self.servers.get_server(0)
        _TEST_CASES.append(("Valid connection string.",
                            self.build_connection_string(self.server0),
                            False))
        _TEST_CASES.append(("Valid dictionary.",
                            self.servers.get_connection_values(self.server0),
                            False))
        _TEST_CASES.append(("Valid class.", self.server0, False))
        _TEST_CASES.append(("Wrong type passed.", 11, True))
        _TEST_CASES.append(("Wrong string passed.", "Who's there?", True))
        _TEST_CASES.append(("Wrong class passed.", self, True))
        return True
    
    def run(self):
        for i in range(0,len(_TEST_CASES)):
            if self.debug:
              print "\nTest case %s - %s" % (i+1, _TEST_CASES[i][0])
            try:
                src_val = get_connection_dictionary(_TEST_CASES[i][1])
                server_options = {
                    'quiet'     : True,
                    'version'   : None,
                    'src_name'  : "test",
                    'dest_name' : None,
                }
                s = connect_servers(src_val, None, server_options)
            except UtilError, e:
                self.results.append((True, e.errmsg))
            except FormatError, e:
                self.results.append((True, e))
            else:
                self.results.append((False, ''))
            if self.debug:
                print "Test results:", self.results[i][0], self.results[i][1]

        return True
    
    def get_result(self):
        if len(self.results) != len(_TEST_CASES):
            return (False, ("Invalid number of test case results."))
    
        for i in range(0, len(_TEST_CASES)):
            if not self.results[i][0] == _TEST_CASES[i][2]:
                msg = "Got wrong result for test case %s." % (i+1) + \
                      " Expected: %s, got: %s." % (_TEST_CASES[i][2],
                       self.results[i][0])
                if self.results[i][1] == '':
                    errors = (msg)
                else:
                    errors = (msg, "\nException: %s." % self.results[i][1])
                return (False, errors)
        
        return (True, None)
    
    def record(self):
        return True
    
    def cleanup(self):
        return True
