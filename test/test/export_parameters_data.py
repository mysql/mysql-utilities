#!/usr/bin/env python

import os
import export_basic
from mysql.utilities.exception import MySQLUtilError, MUTException

class test(export_basic.test):
    """check parameters for export utility
    This test executes a series of export database operations on a single
    server using a variety of parameters. It uses the export_basic test
    as a parent for setup and teardown methods.
    """

    def check_prerequisites(self):
        return export_basic.test.check_prerequisites(self)

    def setup(self):
        return export_basic.test.setup(self)
         
    def run(self):
        self.server1 = self.servers.get_server(0)
        self.res_fname = self.testdir + "result.txt"
       
        from_conn = "--server=" + self.build_connection_string(self.server1)
       
        cmd_str = "mysqlexport.py %s " % from_conn
        
        # Now test the skips

        cmd_opts = "%s util_test --format=SQL --export=data" % (cmd_str)
        comment = "Test case 1 - SQL single rows"
        res = self.run_test_case(0, cmd_opts, comment)
        if not res:
            raise MUTException("%s: failed" % comment)

        comment = "Test case 2 - SQL bulk insert"
        res = self.run_test_case(0, cmd_opts + " --bulk-insert", comment)
        if not res:
            raise MUTException("%s: failed" % comment)

        cmd_opts = "%s util_test --format=CSV --export=data" % (cmd_str)
        comment = "Test case 3 - CSV format"
        res = self.run_test_case(0, cmd_opts, comment)
        if not res:
            raise MUTException("%s: failed" % comment)

        cmd_opts = "%s util_test --format=TAB --export=data" % (cmd_str)
        comment = "Test case 4 - TAB format"
        res = self.run_test_case(0, cmd_opts, comment)
        if not res:
            raise MUTException("%s: failed" % comment)

        cmd_opts = "%s util_test --format=GRID --export=data" % (cmd_str)
        comment = "Test case 4 - GRID format"
        res = self.run_test_case(0, cmd_opts, comment)
        if not res:
            raise MUTException("%s: failed" % comment)

        cmd_opts = "%s util_test --format=VERTICAL --export=data" % (cmd_str)
        comment = "Test case 5 - VERTICAL format"
        res = self.run_test_case(0, cmd_opts, comment)
        if not res:
            raise MUTException("%s: failed" % comment)

        return True
  
    def get_result(self):
        return self.compare(__name__, self.results)
    
    def record(self):
        return self.save_result_file(__name__, self.results)
    
    def cleanup(self):
        return export_basic.test.cleanup(self)



