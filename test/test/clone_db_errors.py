#!/usr/bin/env python

import os
import clone_db
from mysql.utilities.common import MySQLUtilError

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
        self.server1 = self.servers.get_server(0)
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

        try:
            self.server1.exec_query("CREATE USER 'joe'@'localhost'")
        except MySQLUtilError, e:
            return False

        if os.name == "posix" and self.server1.socket is not None:
            from_conn = "--source=joe@localhost:%s:%s" % \
                        (self.server1.port, self.server1.socket)
        else:
            from_conn = "--source=joe@localhost:%s" % self.server1.port

        cmd_str = "mysqldbcopy.py %s %s " % (from_conn, to_conn)
        cmd_opts = "util_test:util_db_clone --force"
        comment = "Test case 4 - error: user with % - not enough permissions"
        res = self.run_test_case(1, cmd_str + cmd_opts, comment)
        if not res:
            return False
                
        try:
            self.server1.exec_query("GRANT ALL ON util_test.* TO 'joe'@'%%'")
        except MySQLUtilError, e:
            return False
        try:
            self.server1.exec_query("GRANT SELECT ON mysql.* TO 'joe'@'%%'")
        except MySQLUtilError, e:
            return False
        
        comment = "Test case 5 - No error: user with % - has permissions"
        res = self.run_test_case(0, cmd_str + cmd_opts, comment)
        if not res:
            return False
        
        try:
            self.server1.exec_query("CREATE USER 'will'@'127.0.0.1'")
        except MySQLUtilError, e:
            return False
        try:
            self.server1.exec_query("GRANT ALL ON *.* TO 'will'@'127.0.0.1'")
        except MySQLUtilError, e:
            return False
        
        if os.name == "posix" and self.server1.socket is not None:
            from_conn = "--source=will@127.0.0.1:%s:%s" % \
                        (self.server1.port, self.server1.socket)
        else:
            from_conn = "--source=will@127.0.0.1:%s" % self.server1.port

        cmd_str = "mysqldbcopy.py %s %s " % (from_conn, to_conn)
        cmd_opts = "util_test:util_db_clone --force"
        comment = "Test case 6 - show user@127.0.0.1 works"
        res = self.run_test_case(0, cmd_str + cmd_opts, comment)
        if not res:
            return False
             
        return res
  
    def get_result(self):
        return self.compare(__name__, self.results)
    
    def record(self):
        return self.save_result_file(__name__, self.results)
    
    def cleanup(self):
        try:
            self.server1.exec_query("DROP USER 'joe'@'localhost'")
        except:
            pass
        try:
            self.server1.exec_query("DROP USER 'joe'")
        except:
            pass
        try:
            self.server1.exec_query("DROP USER 'will'@'127.0.0.1'")
        except:
            pass
        return clone_db.test.cleanup(self)




