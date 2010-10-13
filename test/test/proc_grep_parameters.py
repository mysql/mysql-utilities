#!/usr/bin/env python

import os
import mysql_test
import proc_grep
from mysql.utilities.common import MySQLUtilError
from mysql.utilities.common import MUTException

class test(proc_grep.test):
    """Process grep
    This test executes the process grep utility parameters.
    It uses the proc_grep test as a parent for setup and teardown methods.
    """

    def check_prerequisites(self):
        return proc_grep.test.check_prerequisites(self)

    def setup(self):
        return proc_grep.test.setup(self)
        
    def run(self):
        self.res_fname = self.testdir + "result.txt"
        from_conn = self.build_connection_string(self.server1)
        conn_val = self.get_connection_values(self.server1)

        cmd_str = "mysqlprocgrep.py %s " % from_conn
       
        comment = "Test case 1 - do the help"
        res = self.run_test_case(0, cmd_str + "--help", comment)
        if not res:
            raise MUTException("%s: failed" % comment)

        comment = "Test case 2 - do the SQL for a simple search"
        cmd_str = "mysqlprocgrep.py --sql "
        cmd_str += "--match-user='%s' " % conn_val[0]
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTException("%s: failed" % comment)

        self.mask_result("    user LIKE 'root'", "    user LIKE 'root'",
                         "    user LIKE 'XXXX'")
        
        return True
  
    def get_result(self):
        return self.compare(__name__, self.results)
    
    def record(self):
        return self.save_result_file(__name__, self.results)
    
    def cleanup(self):
        return proc_grep.test.cleanup(self)


