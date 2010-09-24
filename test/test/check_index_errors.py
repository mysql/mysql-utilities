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

        comment = "Test case 1 - error: no login user"
        res = self.run_test_case(1, "mysqlindexcheck.py util_test_a", comment)
        if not res:
            raise MUTException("%s: failed" % comment)

        comment = "Test case 2 - error: invalid login to server"
        res = self.run_test_case(1, "mysqlindexcheck.py util_test_a "
                                 "--source=nope:nada@localhost:3306", comment)
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



