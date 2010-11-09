#!/usr/bin/env python

import os
import mysql_test
from mysql.utilities.exception import MySQLUtilError, MUTException

class test(mysql_test.System_test):
    """check indexes for duplicates and redundancies
    This test executes the check index utility on a single server displaying
    the best and worst indexes from a large database - employees.
    """

    def check_prerequisites(self):
        # Need non-Windows platform
        if os.name == "nt":
            raise MUTException("Test requires a non-Windows platform.")
        res = self.check_num_servers(1)
        self.server1 = self.servers.get_server(0)
        rows = []
        try:
            rows = self.server1.exec_query("SHOW DATABASES LIKE 'employees'")
        except:
            pass
        if len(rows) == 0:
            raise MUTException("Need employees database loaded on %s" % \
                               self.server1.role)
        return res

    def setup(self):
        return True   # No setup needed
        
    def run(self):
        self.res_fname = self.testdir + "result.txt"
        from_conn = "--source=" + self.build_connection_string(self.server1)

        cmd_str = "mysqlindexcheck.py %s employees.dept_emp " % from_conn
        cmd_str += " --index-format=CSV "
        
        comment = "Test case 1 - show best indexes"
        res = self.run_test_case(0, cmd_str + "--stats --first=5", comment)
        if not res:
            raise MUTException("%s: failed" % comment)

        comment = "Test case 2 - show worst indexes"
        res = self.run_test_case(0, cmd_str + "--stats --last=5", comment)
        if not res:
            raise MUTException("%s: failed" % comment)

        # Mask the output
        self.mask_column_result("employees", ",", 7, 'NNNNNNN')
        self.mask_column_result("employees", ",", 8, 'NNNNNNN')
        self.mask_column_result("employees", ",", 9, 'NNNNNNN')

        return True
  
    def get_result(self):
        return self.compare(__name__, self.results)
    
    def record(self):
        return self.save_result_file(__name__, self.results)
    
    def cleanup(self):
        return True    # No cleanup needed


