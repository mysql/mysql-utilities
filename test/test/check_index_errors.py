#!/usr/bin/env python

import os
import check_index
from mysql.utilities.common import MySQLUtilError
from mysql.utilities.common import MUTException

class test(check_index.test):
    """check errors for check index
    This test ensures the known error conditions are tested. It uses the
    check_index test as a parent for setup and teardown methods.
    """

    def check_prerequisites(self):
        return check_index.test.check_prerequisites(self)

    def setup(self):
        return check_index.test.setup(self)
        
    def run(self):
        self.res_fname = self.testdir + "result.txt"

        comment = "Test case 1 - error: no db specified"
        res = self.run_test_case(2, "mysqlindexcheck.py ", comment)
        if not res:
            raise MUTException("%s: failed" % comment)

        comment = "Test case 2 - error: no source specified"
        res = self.run_test_case(1, "mysqlindexcheck.py util_test", comment)
        if not res:
            raise MUTException("%s: failed" % comment)

        comment = "Test case 3 - error: invalid login to server"
        res = self.run_test_case(1, "mysqlindexcheck.py util_test_a "
                                 "--source=nope:nada@localhost:3306", comment)
        if not res:
            raise MUTException("%s: failed" % comment)
         
        comment = "Test case 4 - error: silent and verbose"
        res = self.run_test_case(2, "mysqlindexcheck.py --silent --verbose "
                                 "util_test_a", comment)
        if not res:
            raise MUTException("%s: failed" % comment)
            
        comment = "Test case 5 - error: stats and first=alpha"
        res = self.run_test_case(2, "mysqlindexcheck.py --stats --first=A "
                                 "util_test_a", comment)
        if not res:
            raise MUTException("%s: failed" % comment)
        
        comment = "Test case 6 - error: stats and last=alpha"
        res = self.run_test_case(2, "mysqlindexcheck.py --stats --last=A "
                                 "util_test_a", comment)
        if not res:
            raise MUTException("%s: failed" % comment)
            
        comment = "Test case 7 - error: not stats "
        res = self.run_test_case(2, "mysqlindexcheck.py --first=1 "
                                 "util_test_a", comment)
        if not res:
            raise MUTException("%s: failed" % comment)

        comment = "Test case 8 - error: stats and both first and last "
        res = self.run_test_case(2, "mysqlindexcheck.py --stats --first=1 "
                                 "--last=1 util_test_a", comment)
        if not res:
            raise MUTException("%s: failed" % comment)

        comment = "Test case 9 - error: stats and last=-1"
        res = self.run_test_case(2, "mysqlindexcheck.py --stats --last=-1 "
                                 "util_test_a", comment)
        if not res:
            raise MUTException("%s: failed" % comment)

        comment = "Test case 10 - error: stats and first=-1"
        res = self.run_test_case(2, "mysqlindexcheck.py --stats --first=-1 "
                                 "util_test_a", comment)
        if not res:
            raise MUTException("%s: failed" % comment)

        self.replace_result("Error 1045:", "Error XXXX: Access denied\n")
        self.replace_result("Error 2003:", "Error XXXX: Access denied\n")

        return True
  
    def get_result(self):
        return self.compare(__name__, self.results)
    
    def record(self):
        return self.save_result_file(__name__, self.results)
    
    def cleanup(self):
        return check_index.test.cleanup(self)



