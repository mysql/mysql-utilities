#!/usr/bin/env python

import os
import copy_db

class test(copy_db.test):
    """check errors for copy db
    This test ensures the known error conditions are tested. It uses the
    copy_db test as a parent for setup and teardown methods.
    """

    def check_prerequisites(self):
        return copy_db.test.check_prerequisites(self)

    def setup(self):
        res = copy_db.test.setup(self)
        if not res:
            return res
        # Create users for privilege testing
        res = self.server1.exec_query("CREATE USER 'joe'@'localhost'")
        res = self.server1.exec_query("CREATE USER 'sam'@'localhost'")
        res = self.server1.exec_query("GRANT SELECT ON util_test.* TO " + \
                                      "'joe'@'localhost'")
        res = self.server1.exec_query("GRANT SELECT ON mysql.* TO " + \
                                      "'joe'@'localhost'")
        res = self.server1.exec_query("GRANT SHOW VIEW ON util_test.* TO " + \
                                      "'joe'@'localhost'")

        res = self.server2.exec_query("CREATE USER 'joe'@'localhost'")
        res = self.server2.exec_query("CREATE USER 'sam'@'localhost'")
        res = self.server2.exec_query("GRANT ALL ON util_db_clone.* TO " + \
                                      "'joe'@'localhost' WITH GRANT OPTION")
        res = self.server2.exec_query("GRANT SUPER, CREATE USER ON *.* TO " + \
                                      "'joe'@'localhost'")
        return True
                    
    def run(self):
        self.server1 = self.server_list[0]
        self.res_fname = self.testdir + "result.txt"
       
        from_conn = "--source=" + self.build_connection_string(self.server1)
        to_conn = "--destination=" + self.build_connection_string(self.server2)

        cmd_str = "mysqldbcopy.py %s " % from_conn
        cmd_opts = "util_test:util_db_clone "
        comment = "Test case 1 - error: no destination specified"
        res = self.run_test_case(1, cmd_str + cmd_opts, comment)
        if not res:
            return False

        cmd_str = "mysqldbcopy.py %s %s " % (from_conn, to_conn)
        cmd_opts = " "
        comment = "Test case 2 - error: no database specified"
        res = self.run_test_case(1, cmd_str + cmd_opts, comment)
        if not res:
            return False

        cmd_opts = " wax\t::sad "
        comment = "Test case 3 - error: cannot parse database list"
        res = self.run_test_case(1, cmd_str + cmd_opts, comment)
        if not res:
            return False

        cmd_opts = "NOT_THERE_AT_ALL:util_db_clone"
        comment = "Test case 4 - error: old database doesn't exist"
        res = self.run_test_case(1, cmd_str + cmd_opts, comment)
        if not res:
            return False

        cmd_str = "mysqldbcopy.py %s " % to_conn
        cmd_str += "--source=nope:nada@localhost:3306 "
        cmd_opts = "util_test:util_db_clone "
        comment = "Test case 5 - error: cannot connect to source"
        res = self.run_test_case(1, cmd_str + cmd_opts, comment)
        if not res:
            return False
        
        cmd_str = "mysqldbcopy.py %s " % from_conn
        cmd_str += "--destination=nope:nada@localhost:3306 "
        cmd_opts = "util_test:util_db_clone "
        comment = "Test case 6 - error: cannot connect to destination"
        res = self.run_test_case(1, cmd_str + cmd_opts, comment)
        if not res:
            return False

        from_conn = "--source=joe@localhost:3306 "
        # Watchout for Windows: it doesn't use sockets!
        if os.name == "posix":
            to_conn = "--destination=joe@localhost:%s:%s" % \
                    (self.server2.port, self.server2.socket)
        else:
            to_conn = "--destination=joe@localhost:%s" % (self.server2.port)
        cmd_str = "mysqldbcopy.py %s %s " % (from_conn, to_conn)
        cmd_opts = "util_test:util_db_clone "
        comment = "Test case 7 - users with minimal privileges"
        res = self.run_test_case(0, cmd_str + cmd_opts, comment)
        if not res:
            return False

        from_conn = "--source=sam@localhost:3306 "
        if os.name == "posix":
            to_conn = "--destination=joe@localhost:%s:%s" % \
                      (self.server2.port, self.server2.socket)
        else:
            to_conn = "--destination=joe@localhost:%s" % self.server2.port
        cmd_str = "mysqldbcopy.py %s %s " % (from_conn, to_conn)
        cmd_opts = "util_test:util_db_clone --force"
        comment = "Test case 8 - source user not enough privileges needed"
        res = self.run_test_case(1, cmd_str + cmd_opts, comment)
        if not res:
            return False
        
        # Give Sam some privileges on source and retest until copy works
        res = self.server1.exec_query("GRANT SELECT ON util_test.* TO " + \
                                      "'sam'@'localhost'")
        comment = "Test case 9 - source user has some privileges needed"
        res = self.run_test_case(1, cmd_str + cmd_opts, comment)
        if not res:
            return False
        
        res = self.server1.exec_query("GRANT SELECT ON mysql.* TO " + \
                                      "'sam'@'localhost'")
        comment = "Test case 10 - source user has some privileges needed"
        res = self.run_test_case(1, cmd_str + cmd_opts, comment)
        if not res:
            return False

        res = self.server1.exec_query("GRANT SHOW VIEW ON util_test.* TO " + \
                                      "'sam'@'localhost'")
        comment = "Test case 11 - source user has privileges needed"
        res = self.run_test_case(0, cmd_str + cmd_opts, comment)
        if not res:
            return False

        # Watchout for Windows: it doesn't use sockets!
        if os.name == "posix":
            to_conn = "--destination=sam@localhost:%s:%s" % \
                      (self.server2.port, self.server2.socket)
        else:
            to_conn = "--destination=sam@localhost:%s" % self.server2.port
        cmd_str = "mysqldbcopy.py %s %s " % (from_conn, to_conn)
        cmd_opts = "util_test:util_db_clone --force "
        comment = "Test case 12 - dest user not enough privileges needed"
        res = self.run_test_case(1, cmd_str + cmd_opts, comment)
        if not res:
            return False

        # Give Sam some privileges on source and retest until copy works
        res = self.server2.exec_query("GRANT ALL ON util_db_clone.* TO " + \
                                      "'sam'@'localhost' WITH GRANT OPTION")
        comment = "Test case 13 - dest user has some privileges needed"
        res = self.run_test_case(1, cmd_str + cmd_opts, comment)
        if not res:
            return False

        res = self.server2.exec_query("GRANT CREATE USER ON *.* TO " + \
                                      "'sam'@'localhost'")
        comment = "Test case 14 - dest user has some privileges needed"
        res = self.run_test_case(1, cmd_str + cmd_opts, comment)
        if not res:
            return False

        res = self.server2.exec_query("GRANT SUPER ON *.* TO " + \
                                      "'sam'@'localhost'")
        comment = "Test case 15 - dest user has privileges needed"
        res = self.run_test_case(0, cmd_str + cmd_opts, comment)
        if not res:
            return False

        # Mask socket for destination server
        self.replace_result("# Destination: root@localhost:",
                            "# Destination: root@localhost:[] ... connected\n")
        self.replace_result("# Destination: joe@localhost:",
                            "# Destination: joe@localhost:[] ... connected\n")
        self.replace_result("# Destination: sam@localhost:",
                            "# Destination: sam@localhost:[] ... connected\n")

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
            self.server1.exec_query("DROP USER 'sam'@'localhost'")
        except:
            pass
        res = copy_db.test.cleanup(self)
        return res



