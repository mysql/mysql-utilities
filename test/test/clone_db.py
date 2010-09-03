#!/usr/bin/env python

import os
import mysql_test

class test(mysql_test.System_test):
    """simple db clone
    This test executes a simple clone of a database on a single server.
    """

    def check_prerequisites(self):
        return self.check_num_servers(1)

    def setup(self):
        self.server1 = self.server_list[0]
        data_file = os.path.normpath(self.testdir + "/data/basic_data.sql")
        return self.server1.read_and_exec_SQL(data_file, self.verbose, True)
    
    def run(self):
        self.server1 = self.server_list[0]
        self.res_fname = self.testdir + "result.txt"
        
        from_conn = "--source=" + self.build_connection_string(self.server1)
        to_conn = "--destination=" + self.build_connection_string(self.server1)
       
        # Test case 1 - clone a sample database
        cmd = "mysqldbcopy.py %s %s " % (from_conn, to_conn) + \
              " util_test:util_db_clone"
        res = self.exec_util(cmd, self.res_fname)
        self.results.append(res)       
        return res == 0
  
    def get_result(self):
        msg = None
        if self.server1 and self.results[0] == 0:
            query = "SHOW DATABASES LIKE 'util_%%'"
            try:
                res = self.server1.exec_query(query)
                if res and res[0][0] == 'util_db_clone':
                    return (True, msg)
            except:
                msg = "Clone db failed."
        return (False, msg)
    
    def record(self):
        # Not a comparative test, returning True
        return True
    
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
    
    def cleanup(self):
        if self.res_fname:
            os.unlink(self.res_fname)
        try:
            res1 = self.drop_db(self.server1, "util_test")
        except:
            pass
        try:
            res2 = self.drop_db(self.server1, "util_db_clone")
        except:
            pass
        return res1 and res2




