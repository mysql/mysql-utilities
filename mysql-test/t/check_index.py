#!/usr/bin/env python

import os
import mutlib
from mysql.utilities.exception import MUTLibError

class test(mutlib.System_test):
    """check indexes for duplicates and redundancies
    This test executes the check index utility on a single server.
    """

    def check_prerequisites(self):
        return self.check_num_servers(1)

    def setup(self):
        self.server1 = self.servers.get_server(0)
        data_file = "std_data/index_test.sql"
        self.drop_all()
        try:
            res = self.server1.read_and_exec_SQL(data_file, self.debug)
        except MUTLibError, e:
            raise MUTLibError("Failed to read commands from file %s: " % \
                               data_file + e.errmsg)
        return True
    
    def run(self):
        self.res_fname = "result.txt"
        from_conn = "--server=" + self.build_connection_string(self.server1)

        cmd_str = "mysqlindexcheck.py %s " % from_conn

        comment = "Test case 1 - check a table without indexes"
        res = self.run_test_case(0, cmd_str + "util_test_c.t6 -vv", comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        
        comment = "Test case 2 - check a list of tables and databases"
        res = self.run_test_case(0, cmd_str + "util_test_c util_test_a.t1" + \
                                 " util_test_b -vv", comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        
        comment = "Test case 3 - check all tables for a single database"
        res = self.run_test_case(0, cmd_str + "util_test_a -vv", comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        comment = "Test case 4 - check tables for a non-existant database"
        res = self.run_test_case(1, cmd_str + "util_test_X -vv", comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        comment = "Test case 5 - check indexes for a non-existant table"
        res = self.run_test_case(1, cmd_str + "nosuch.nosuch -vv", comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        comment = "Test case 6 - check indexes for a non-existant table " + \
                  "with skip option"
        res = self.run_test_case(0, cmd_str + "nosuch.nosuch -vv --skip",
                                 comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        return True
  
    def get_result(self):
        return self.compare(__name__, self.results)
    
    def record(self):
        return self.save_result_file(__name__, self.results)
    
    def drop_all(self):
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

    def cleanup(self):
        if self.res_fname:
            os.unlink(self.res_fname)
        self.drop_all()
        return True

