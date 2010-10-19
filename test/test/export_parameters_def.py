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
        
        cmd_opts = "util_test --help"
        comment = "Test case 1 - help"
        res = self.run_test_case(0, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTException("%s: failed" % comment)
            
        # Now test the skips

        cmd_opts = "%s util_test --skip=grants" % (cmd_str)
        comment = "Test case 2 - no grants"
        res = self.run_test_case(0, cmd_opts, comment)
        if not res:
            raise MUTException("%s: failed" % comment)

        cmd_opts += ",events"
        comment = "Test case 3 - no events"
        res = self.run_test_case(0, cmd_opts, comment)
        if not res:
            raise MUTException("%s: failed" % comment)

        cmd_opts += ",functions"
        comment = "Test case 4 - no functions"
        res = self.run_test_case(0, cmd_opts, comment)
        if not res:
            raise MUTException("%s: failed" % comment)

        cmd_opts += ",procedures"
        comment = "Test case 5 - no procedures"
        res = self.run_test_case(0, cmd_opts, comment)
        if not res:
            raise MUTException("%s: failed" % comment)

        cmd_opts += ",triggers"
        comment = "Test case 6 - no triggers"
        res = self.run_test_case(0, cmd_opts, comment)
        if not res:
            raise MUTException("%s: failed" % comment)

        cmd_opts += ",views"
        comment = "Test case 7 - no views"
        res = self.run_test_case(0, cmd_opts, comment)
        if not res:
            raise MUTException("%s: failed" % comment)

        cmd_opts += ",tables"
        comment = "Test case 8 - no tables"
        res = self.run_test_case(0, cmd_opts, comment)
        if not res:
            raise MUTException("%s: failed" % comment)        

        cmd_opts += ",create_db"
        comment = "Test case 9 - no create_db"
        res = self.run_test_case(0, cmd_opts, comment)
        if not res:
            raise MUTException("%s: failed" % comment)        

        cmd_opts += ",data"
        comment = "Test case 10 - no data"
        res = self.run_test_case(0, cmd_opts, comment)
        if not res:
            raise MUTException("%s: failed" % comment)
            
        self.replace_result("CREATE EVENT `e1` ON SCHEDULE EVERY 1 YEAR STARTS",
                            "CREATE EVENT `e1` ON SCHEDULE EVERY 1 YEAR "
                            "STARTS XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX\n")

        return True
  
    def get_result(self):
        return self.compare(__name__, self.results)
    
    def record(self):
        return self.save_result_file(__name__, self.results)
    
    def cleanup(self):
        return export_basic.test.cleanup(self)



