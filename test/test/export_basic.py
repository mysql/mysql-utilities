#!/usr/bin/env python

import os
import mysql_test
from mysql.utilities.exception import MySQLUtilError, MUTException

class test(mysql_test.System_test):
    """Export Data
    This test executes the export utility on a single server.
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
        
        from_conn = "--server=%s" % self.build_connection_string(self.server1)
        
        cmd = "mysqlexport.py %s util_test  " % from_conn
       
        comment = "Test case 1 - export metadata only"
        cmd_str = cmd + " --export=definitions --format=SQL --skip=events "
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTException("%s: failed" % comment)
                    
        comment = "Test case 2 - export data only - single rows"
        cmd_str = cmd + " --export=data --format=SQL " 
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTException("%s: failed" % comment)
                    
        comment = "Test case 3 - export data only - bulk insert"
        cmd_str = cmd + " --export=data --format=SQL --bulk-insert" 
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTException("%s: failed" % comment)
                    
        comment = "Test case 4 - export data and metadata"
        cmd_str = cmd + " --export=both --format=SQL --skip=events"
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTException("%s: failed" % comment)
                    
        comment = "Test case 5 - export data and metadata with silent"
        cmd_str = cmd + " --export=both --format=SQL --skip=events --silent"
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTException("%s: failed" % comment)

        comment = "Test case 6 - export data and metadata with debug"
        cmd_str = cmd + " --export=both --format=SQL --skip=events -vvv"
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTException("%s: failed" % comment)

        self.replace_result("Time:", "Time:       XXXXXX\n")

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




