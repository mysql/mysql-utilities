#!/usr/bin/env python

import os
import mysql_test
import mysql.utilities.common.exception

class test(mysql_test.System_test):
    """simple db copy
    This test executes copy database test cases among two servers.
    """

    def check_prerequisites(self):
        # Need at least one server.
        self.server1 = None
        self.server2 = None
        self.need_server = False
        if not self.check_num_servers(2):
            self.need_server = True
        return self.check_num_servers(1)

    def setup(self):
        port1 = int(self.new_port)
        self.server1 = self.server_list[0]
        conn_val = self.get_connection_values(self.server1)
        if self.need_server:
            res = self.start_new_server(self.server1, "copydb1", port1, 10,
                                        conn_val[1])
            if not res[0]:
                return False
            self.server2 = res[0]
        else:
            self.server2 = self.server_list[1]
        data_file = os.path.normpath(self.testdir + "/data/basic_data.sql")
        return self.server1.read_and_exec_SQL(data_file, self.verbose, True)
    
    def run(self):
        self.res_fname = self.testdir + "result.txt"
        
        from_conn = "--source=" + self.build_connection_string(self.server1)
        to_conn = "--destination=" + self.build_connection_string(self.server2)
       
        # Test case 1 - copy a sample database
        cmd = "mysqldbcopy.py %s %s " % (from_conn, to_conn) + \
              " util_test:util_db_clone"
        res = self.exec_util(cmd, self.res_fname)
        self.results.append(res)
        return res == 0
  
    def get_result(self):
        msg = None
        if self.server2 and self.results[0] == 0:
            query = "SHOW DATABASES LIKE 'util_db_clone'"
            try:
                res = self.server2.exec_query(query)
                if res and res[0][0] == 'util_db_clone':
                    return (True, msg)
            except:
                msg = "Copy db failed."
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
        res1, res2 = True, True
        try:
            res1 = self.drop_db(self.server1, "util_test")
        except:
            pass
        if self.server2:
            if self.need_server:
                res2 = self.stop_server(self.server2)
            else:
                res2 = self.drop_db(self.server2, "util_db_clone")
        return res1 and res2


