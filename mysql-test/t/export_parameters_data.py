#!/usr/bin/env python

import os
import export_parameters_def
from mysql.utilities.exception import MUTLibError, UtilDBError

class test(export_parameters_def.test):
    """check parameters for export utility
    This test executes a series of export database operations on a single
    server using a variety of parameters. It uses the export_parameters_def
    test as a parent for setup and teardown methods.
    """

    def check_prerequisites(self):
        return export_parameters_def.test.check_prerequisites(self)

    def setup(self):
        res = export_parameters_def.test.setup(self)
        if not res:
            return False

        try:
            self.server1.exec_query("ALTER TABLE util_test.t2 ADD COLUMN "
                                    " x_blob blob")
        except UtilDBError, e:
            raise MUTLibError("Cannot alter table: %s" % e.errmsg)
            
        try:
            self.server1.exec_query("UPDATE util_test.t2 SET x_blob = "
                                    "'This is a blob.' ")

        except UtilDBError, e:
            raise MUTLibError("Cannot update rows: %s" % e.errmsg)

        return True
         
    def run(self):
        self.res_fname = "result.txt"
       
        from_conn = "--server=" + self.build_connection_string(self.server1)
       
        cmd_str = "mysqldbexport.py %s " % from_conn
        
        cmd_opts = "%s util_test --format=SQL --export=data" % cmd_str
        comment = "Test case 1 - SQL single rows"
        res = self.run_test_case(0, cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        comment = "Test case 2 - SQL bulk insert"
        res = self.run_test_case(0, cmd_opts + " --bulk-insert", comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        
        comment = "Test case 3 - skip blobs"
        res = self.run_test_case(0, cmd_opts + " --skip-blobs", comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        
        # Conduct format and display combination tests
        # Note: should say it is ignored for --export=data output.

        func = export_parameters_def.test.test_format_and_display_values
        func(self, "%s util_test --export=data --format=" % cmd_str, 4)

        self.server1.exec_query("ALTER TABLE util_test.t2 ADD COLUMN "
                                 " y_blob blob")
        self.server1.exec_query("UPDATE util_test.t2 SET y_blob = "
                                "'This is yet another blob.' ")

        comment = "Test case 31 - multiple blobs"
        res = self.run_test_case(0, cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        return True
  
    def get_result(self):
        return self.compare(__name__, self.results)
    
    def record(self):
        return self.save_result_file(__name__, self.results)
    
    def cleanup(self):
        return export_parameters_def.test.cleanup(self)



