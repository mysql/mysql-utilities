#!/usr/bin/env python

import os
import mysql_test
from mysql.utilities.exception import MySQLUtilError, MUTException

class test(mysql_test.System_test):
    """Process grep
    This test executes the process grep tool on a single server.
    """

    def check_prerequisites(self):
        return self.check_num_servers(1)

    def setup(self):
        self.server1 = self.servers.get_server(0)
        data_file = os.path.normpath(self.testdir + "/data/basic_data.sql")
        self.drop_all()
        try:
            res = self.server1.read_and_exec_SQL(data_file, self.verbose)
        except MySQLUtilError, e:
            raise MUTException("Failed to read commands from file %s: " % \
                               data_file + e.errmsg)
        return True
    
    def run(self):
        self.server1 = self.servers.get_server(0)
        self.res_fname = self.testdir + "result.txt"
        
        from_conn = self.build_connection_string(self.server1)
        conn_val = self.get_connection_values(self.server1)
        
        cmd = "mysqlprocgrep.py %s " % from_conn
       
        comment = "Test case 1 - find processes for current user"
        cmd += "--match-user='%s' " % conn_val[0]
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTException("%s: failed" % comment)
            
        self.mask_column_result("| %s:*@" % conn_val[0], "|", 3, "XXXXX ")
        self.mask_result("| %s:*@" % conn_val[0], "| %s:*@" % conn_val[0],
                         "| XXXXXXXXXXXXXXXXXXXXX")
        
        return True
          
    def get_result(self):
        return self.compare(__name__, self.results)
    
    def record(self):
        return self.save_result_file(__name__, self.results)
    
    def drop_db(self, server, db):
        # Check before you drop to avoid warning
        try:
            res = server.exec_query("SHOW DATABASES LIKE 'util_%%'")
        except:
            return True # Ok to exit here as there weren't any dbs to drop
        try:
            res = server.exec_query("DROP DATABASE %s" % db)
        except:
            return False
        return True
    
    def drop_all(self):
        try:
            self.drop_db(self.server1, "util_test")
        except:
            return False
        return True

    def cleanup(self):
        if self.res_fname:
            os.unlink(self.res_fname)
        return self.drop_all()




