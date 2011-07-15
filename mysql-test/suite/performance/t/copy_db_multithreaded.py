#!/usr/bin/env python

import os
import mutlib

class test(mutlib.System_test):
    """simple db copy
    This test executes copy database test cases among two servers using
    multiple threads.
    """

    def is_long(self):
        # This test is a long running test
        return True

    def check_prerequisites(self):
        # Need non-Windows platform
        if os.name == "nt":
            raise MUTLibError("Test requires a non-Windows platform.")
        # Need at least one server.
        self.server1 = self.servers.get_server(0)
        self.server2 = None
        self.need_server = False
        if not self.check_num_servers(2):
            self.need_server = True
        res = self.check_num_servers(1)
        rows = []
        try:
            rows = self.server1.exec_query("SHOW DATABASES LIKE 'employees'")
        except:
            pass
        if len(rows) == 0:
            raise MUTLibError("Need employees database loaded on %s" % \
                               self.server1.role)
        return res

    def setup(self):
        if self.need_server:
            self.servers.spawn_new_servers(2)
        self.server2 = self.servers.get_server(1)
        self.drop_all()
        return True

    
    def run(self):
        self.res_fname = "result.txt"
        
        from_conn = "--source=" + self.build_connection_string(self.server1)
        to_conn = "--destination=" + self.build_connection_string(self.server2)
       
        comment = "Test case 1 - copy a sample database"
        cmd = "mysqldbcopy.py %s %s " % (from_conn, to_conn) + \
              " employees:emp_mt --force --threads=3 "
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

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
        return self.drop_db(self.server2, "emp_mt")
            
    def cleanup(self):
        if self.res_fname:
            os.unlink(self.res_fname)
        return self.drop_all()


