#!/usr/bin/env python

import os
import copy_db
from mysql.utilities.common import MySQLUtilError
from mysql.utilities.common import MUTException

class test(copy_db.test):
    """check parameters for clone db
    This test executes a series of clone database operations on a single
    server using a variety of parameters. It uses the copy_db test
    as a parent for setup and teardown methods.
    """

    def check_prerequisites(self):
        return copy_db.test.check_prerequisites(self)

    def setup(self):
        return copy_db.test.setup(self)
         
    def run(self):
        self.server1 = self.servers.get_server(0)
        self.res_fname = self.testdir + "result.txt"
       
        from_conn = "--source=" + self.build_connection_string(self.server1)
        to_conn = "--destination=" + self.build_connection_string(self.server2)
       
        cmd_str = "mysqldbcopy.py %s %s " % (from_conn, to_conn)
        
        # In this test, we execute a series of commands saving the results
        # from each run to perform a comparative check.
        
        cmd_opts = "util_test:util_db_clone"
        comment = "Test case 1 - normal run"
        res = self.run_test_case(0, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTException("%s: failed" % comment)

        comment = "Test case 2 - operation fails - need overwrite"
        res = self.run_test_case(1, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTException("%s: failed" % comment)

        cmd_opts = "--help"
        comment = "Test case 3 - help"
        res = self.run_test_case(0, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTException("%s: failed" % comment)

        # We exercise --force here to ensure skips don't interfere
        cmd_opts = "--force --skip-data util_test:util_db_clone"
        comment = "Test case 4 - no data"
        res = self.run_test_case(0, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTException("%s: failed" % comment)
        self.results.append(self.check_objects(self.server1, "util_db_clone"))

        cmd_opts = "--force --skip-data --silent util_test:util_db_clone"
        comment = "Test case 5 - silent copy"
        res = self.run_test_case(0, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTException("%s: failed" % comment)

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



