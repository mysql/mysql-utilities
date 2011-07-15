#!/usr/bin/env python

import os
import copy_db
from mysql.utilities.exception import MUTLibError

class test(copy_db.test):
    """check skip objects for copy/clone db
    This test executes a series of copy database operations on two 
    servers using a variety of skip oject parameters. It uses the
    copy_db test as a parent for setup and teardown methods.
    """

    def check_prerequisites(self):
        return copy_db.test.check_prerequisites(self)

    def setup(self):
        return copy_db.test.setup(self)
        
    def run(self):
        self.server1 = self.servers.get_server(0)
        self.res_fname = "result.txt"
       
        from_conn = "--source=" + self.build_connection_string(self.server1)
        to_conn = "--destination=" + self.build_connection_string(self.server2)

        cmd_str = "mysqldbcopy.py %s %s util_test:util_db_clone" % \
                  (from_conn, to_conn)
        
        # In this test, we execute a series of commands saving the results
        # from each run to perform a comparative check.
        
        cmd_opts = "%s --force --skip=grants" % (cmd_str)
        comment = "Test case 1 - no grants"
        res = self.run_test_case(0, cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        self.results.append(self.check_objects(self.server2, "util_db_clone"))

        cmd_opts += ",events"
        comment = "Test case 2 - no events"
        res = self.run_test_case(0, cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        self.results.append(self.check_objects(self.server2, "util_db_clone"))

        cmd_opts += ",functions"
        comment = "Test case 3 - no functions"
        res = self.run_test_case(0, cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        self.results.append(self.check_objects(self.server2, "util_db_clone"))

        cmd_opts += ",procedures"
        comment = "Test case 4 - no procedures"
        res = self.run_test_case(0, cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        self.results.append(self.check_objects(self.server2, "util_db_clone"))

        cmd_opts += ",triggers"
        comment = "Test case 5 - no triggers"
        res = self.run_test_case(0, cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        self.results.append(self.check_objects(self.server2, "util_db_clone"))

        cmd_opts += ",views"
        comment = "Test case 6 - no views"
        res = self.run_test_case(0, cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        self.results.append(self.check_objects(self.server2, "util_db_clone"))

        cmd_opts += ",tables"
        comment = "Test case 7 - no tables"
        res = self.run_test_case(0, cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        self.results.append(self.check_objects(self.server2, "util_db_clone"))
        
        # Create the database to test --skip=create-db
        query = "DROP DATABASE util_db_clone"
        try:
            res = self.server2.exec_query(query)
        except:
            pass
        query = "CREATE DATABASE util_db_clone"
        try:
            res = self.server2.exec_query(query)
        except:
            pass

        # Reset to check only the skip create
        cmd_opts = "%s --skip=create_db" % (cmd_str)
        comment = "Test case 8 - skip create db"
        res = self.run_test_case(0, cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        self.results.append(self.check_objects(self.server2, "util_db_clone"))

        query = "DROP DATABASE util_db_clone"
        try:
            res = self.server2.exec_query(query)
        except:
            pass
        
        # Show possible errors from skip misuse
        cmd_opts = "%s --skip=tables" % (cmd_str)
        comment = "Test case 9 - skip tables only - will fail"
        res = self.run_test_case(1, cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        # Mask socket for destination server
        self.replace_result("# Destination: root@localhost:",
                            "# Destination: root@localhost:[] ... connected\n")

        return True
  
    def get_result(self):
        return self.compare(__name__, self.results)
    
    def record(self):
        return self.save_result_file(__name__, self.results)
    
    def cleanup(self):
        return copy_db.test.cleanup(self)



