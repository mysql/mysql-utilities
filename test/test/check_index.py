#!/usr/bin/env python

import os
import mysql_test

class test(mysql_test.System_test):
    """check indexes for duplicates and redundancies
    This test executes the check index utility on a single server.
    """

    def check_prerequisites(self):
        return self.check_num_servers(1)

    def setup(self):
        self.server1 = self.server_list[0]
        data_file = self.testdir + "data/index_test.sql"
        return self.server1.read_and_exec_SQL(data_file, self.verbose, True)
    
    def run(self):
        self.res_fname = self.testdir + "result.txt"
        from_conn = "--source=" + self.build_connection_string(self.server1)

        cmd_str = "mysqlindexcheck.py %s " % from_conn
       
        comment = "Test case 1 - check a table without indexes"
        res = self.run_test_case(0, cmd_str + "util_test_c.t6", comment)
        if not res:
            return False
        
        comment = "Test case 2 - check a list of tables and databases"
        res = self.run_test_case(0, cmd_str + "util_test_c util_test_a.t1" + \
                                 " util_test_b", comment)
        if not res:
            return False

        comment = "Test case 3 - check all tables for a single database"
        res = self.run_test_case(0, cmd_str + "util_test_a", comment)
        if not res:
            return False

        comment = "Test case 4 - check tables for a non-existant database"
        res = self.run_test_case(1, cmd_str + "util_test_X -v", comment)
        if not res:
            return False

        comment = "Test case 5 - check indexes for a non-existant table"
        res = self.run_test_case(1, cmd_str + "nosuch.nosuch -v", comment)
        if not res:
            return False

        comment = "Test case 6 - check indexes for a non-existant table " + \
                  "with skip option"
        res = self.run_test_case(0, cmd_str + "nosuch.nosuch -v --skip",
                                 comment)
        if not res:
            return False

        return True
  
    def get_result(self):
        return self.compare(__name__, self.results)
    
    def record(self):
        return self.save_result_file(__name__, self.results)
    
    def cleanup(self):
        if self.res_fname:
            os.unlink(self.res_fname)
        try:
            self.server1.exec_query("DROP DATABASE util_test_a")
        except:
            pass
        try:
            self.server1.exec_query("DROP DATABASE util_test_b")
        except:
            pass
        try:
            self.server1.exec_query("DROP DATABASE util_test_c")
        except:
            pass
        return True

