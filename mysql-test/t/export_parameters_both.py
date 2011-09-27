#!/usr/bin/env python

import os
import export_parameters_def
from mysql.utilities.exception import MUTLibError

class test(export_parameters_def.test):
    """check parameters for export utility
    This test executes a series of export database operations on a single
    server using a variety of parameters. It uses the export_parameters_def
    test as a parent for setup and teardown methods.
    """

    def check_prerequisites(self):
        return export_parameters_def.test.check_prerequisites(self)

    def setup(self):
        return export_parameters_def.test.setup(self)
         
    def run(self):
        self.res_fname = "result.txt"
       
        from_conn = "--server=" + self.build_connection_string(self.server1)
       
        cmd_str = "mysqldbexport.py %s " % from_conn
        
        # Conduct format and display combination tests
        # Note: should say it is ignored for --export=data output.

        func = export_parameters_def.test.test_format_and_display_values
        func(self, "%s util_test --export=both --format=" % cmd_str, 1,
             False, False, False, True)
        
        from_conn = "--server=" + self.build_connection_string(self.server3)
        cmd_str = "mysqldbexport.py %s " % from_conn
        cmd_opts = "--skip=grants,events --all --export=both"
        comment = "Test case 13 - copy all databases"
        res = self.run_test_case(0, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        return True
  
    def get_result(self):
        return self.compare(__name__, self.results)
    
    def record(self):
        return self.save_result_file(__name__, self.results)
    
    def cleanup(self):
        return export_parameters_def.test.cleanup(self)



