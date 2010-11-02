#!/usr/bin/env python

import os
import import_basic
from mysql.utilities.exception import MySQLUtilError, MUTException

class test(import_basic.test):
    """Import Data
    This test executes the import utility on a single server.
    It tests the error conditions for importing data.
    It uses the import_basic test for setup and teardown methods.
    """

    def check_prerequisites(self):
        return import_basic.test.check_prerequisites(self)

    def setup(self):
        return import_basic.test.setup(self)
    
    def run(self):
        self.server1 = self.servers.get_server(0)
        self.res_fname = self.testdir + "result.txt"
        
        from_conn = "--server=%s" % self.build_connection_string(self.server1)
        to_conn = "--server=%s" % self.build_connection_string(self.server2)

        _FORMATS = ("CSV", "TAB", "GRID", "VERTICAL")
        test_num = 1
        for format in _FORMATS:
            try:
                comment = "Test Case %d : Testing import with " % test_num
                comment += "%s format and NAMES display"
                # We test DEFINITIONS and DATA only in other tests
                self.run_import_test(1, from_conn, to_conn,
                                     format, "BOTH", comment,
                                     " --display=NAMES")
            except MUTException, e:
                raise e
            self.drop_db(self.server2, "util_test")
            test_num += 1
        return True
          
    def get_result(self):
        return self.compare(__name__, self.results)
    
    def record(self):
        return self.save_result_file(__name__, self.results)
    
    def cleanup(self):
        return import_basic.test.drop_all(self)




