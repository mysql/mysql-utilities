#!/usr/bin/env python

import os
import clone_db

class test(clone_db.test):
    """check errors for clone db
    This test ensures the known error conditions are tested. It uses the
    clone_db test as a parent for setup and teardown methods.
    """

    def check_prerequisites(self):
        return clone_db.test.check_prerequisites(self)

    def setup(self):
        return clone_db.test.setup(self)
        
    def run(self):
        self.server1 = self.server_list[0]
        self.res_fname = self.testdir + "result.txt"
       
        from_conn = "--source=" + self.build_connection_string(self.server1)
        to_conn = "--destination=" + self.build_connection_string(self.server1)

        cmd_str = "mysqldbcopy.py %s %s " % (from_conn, to_conn)
        
        cmd_opts = "util_test:util_test"
        comment = "Test case 1 - error: same database"
        res = self.run_test_case(1, cmd_str + cmd_opts, comment)
        if not res:
            return False

        cmd_opts = "NOT_THERE_AT_ALL:util_db_clone"
        comment = "Test case 2 - error: old database doesn't exist"
        res = self.run_test_case(1, cmd_str + cmd_opts, comment)
        if not res:
            return False
        
        try:
            self.server1.exec_query("CREATE DATABASE util_db_clone")
        except:
            return False
        
        cmd_opts = "util_test:util_db_clone"
        comment = "Test case 3 - error: target database already exists"
        res = self.run_test_case(1, cmd_str + cmd_opts, comment)
        if not res:
            return False
        
        return res
  
    def get_result(self):
        return self.compare(__name__, self.results)
    
    def record(self):
        return self.save_result_file(__name__, self.results)
    
    def cleanup(self):
        return clone_db.test.cleanup(self)




