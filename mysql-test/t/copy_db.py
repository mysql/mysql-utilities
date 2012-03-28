#!/usr/bin/env python

import os
import mutlib
from mysql.utilities.exception import MUTLibError, UtilDBError

class test(mutlib.System_test):
    """simple db copy
    This test executes copy database test cases among two servers.
    """

    def check_prerequisites(self):
        self.check_gtid_unsafe()
        # Need at least one server.
        self.server1 = None
        self.server2 = None
        self.need_server = False
        if not self.check_num_servers(2):
            self.need_server = True
        return self.check_num_servers(1)

    def setup(self):
        self.server1 = self.servers.get_server(0)
        if self.need_server:
            try:
                self.servers.spawn_new_servers(2)
            except MUTLibError, e:
                raise MUTLibError("Cannot spawn needed servers: %s" % \
                                   e.errmsg)
        self.server2 = self.servers.get_server(1)
        self.drop_all()
        data_file = os.path.normpath("./std_data/basic_data.sql")
        try:
            res = self.server1.read_and_exec_SQL(data_file, self.debug)
        except MUTLibError, e:
            raise MUTLibError("Failed to read commands from file %s: " % \
                               data_file + e.errmsg)
        return True

    
    def run(self):
        self.res_fname = "result.txt"
        
        from_conn = "--source=" + self.build_connection_string(self.server1)
        to_conn = "--destination=" + self.build_connection_string(self.server2)
       
        comment = "Test case 1 - copy a sample database X:Y"
        cmd = "mysqldbcopy.py %s %s " % (from_conn, to_conn)
        res = self.exec_util(cmd + " util_test:util_db_clone", self.res_fname)
        self.results.append(res)
        if res != 0:
            raise MUTLibError("%s: failed" % comment)

        comment = "Test case 2 - copy a sample database X"
        res = self.exec_util(cmd + " util_test", self.res_fname)
        self.results.append(res)
        if res != 0:
            raise MUTLibError("%s: failed" % comment)
            
        comment = "Test case 3 - copy using different engine"
        cmd += " util_test:util_db_clone --force --new-storage-engine=MEMORY"
        res = self.exec_util(cmd, self.res_fname)
        self.results.append(res)
        if res != 0:
            raise MUTLibError("%s: failed" % comment)

        return True
  
    def get_result(self):
        msg = None
        if self.server2 and self.results[0] == 0:
            query = "SHOW DATABASES LIKE 'util_db_clone'"
            try:
                res = self.server2.exec_query(query)
                if res and res[0][0] == 'util_db_clone':
                    return (True, msg)
            except UtilDBError, e:
                raise MUTLibError(e.errmsg)
            query = "SHOW DATABASES LIKE 'util_test'"
            try:
                res = self.server2.exec_query(query)
                if res and res[0][0] == 'util_test':
                    return (True, msg)
            except UtilDBError, e:
                raise MUTLibError(e.errmsg)
        return (False, ("Result failure.\n", "Database copy not found.\n"))
    
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
    
    def drop_all(self):
        res1, res2, res3 = True, True, True
        try:
            self.drop_db(self.server1, "util_test")
        except:
            res1 = False
        try:
            self.drop_db(self.server2, "util_test")
        except:
            res2 = False
        try:
            self.drop_db(self.server2, "util_db_clone")
        except:
            res3 = False
        try:
            self.server1.exec_query("DROP USER 'joe'@'user'")
        except:
            pass
        try:
            self.server2.exec_query("DROP USER 'joe'@'user'")
        except:
            pass
        return res1 and res2
            
    def cleanup(self):
        if self.res_fname:
            os.unlink(self.res_fname)
        return self.drop_all()


