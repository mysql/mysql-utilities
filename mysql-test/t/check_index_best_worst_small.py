#!/usr/bin/env python

import os
import check_index_parameters
from mysql.utilities.exception import MUTLibError

class test(check_index_parameters.test):
    """check for best and worst indexes for the check_index_parameters utility
    This test executes the check index utility parameters on a single server.
    It uses the check_index_parameters test as a parent for setup and
    teardown methods.
    """

    def check_prerequisites(self):
        res = check_index_parameters.test.check_prerequisites(self)
        return res

    def setup(self):
        return check_index_parameters.test.setup(self)
        
    def run(self):
        self.res_fname = "result.txt"
        from_conn = "--server=" + self.build_connection_string(self.server1)

        cmd_str = "mysqlindexcheck.py %s util_test_a " % from_conn
       
        comment = "Test case 1 - show best indexes on small database"
        res = self.run_test_case(0, cmd_str + "--stats -v --best=5", comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        comment = "Test case 2 - show worst indexes on small database"
        res = self.run_test_case(0, cmd_str + "--stats -v --worst=5", comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        
        return True
  
    def get_result(self):
        return self.compare(__name__, self.results)
    
    def record(self):
        return self.save_result_file(__name__, self.results)
    
    def cleanup(self):
        return check_index_parameters.test.cleanup(self)


