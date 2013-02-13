#
# Copyright (c) 2010, 2013, Oracle and/or its affiliates. All rights reserved.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301 USA
#
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
       
        cmd_str = "mysqldbexport.py --skip-gtid %s " % from_conn
        
        # Conduct format and display combination tests
        # Note: should say it is ignored for --export=data output.

        func = export_parameters_def.test.test_format_and_display_values
        func(self, "%s util_test --export=both --format=" % cmd_str, 1,
             False, False, False, True)
        
        from_conn = "--server=" + self.build_connection_string(self.server3)
        cmd_str = "mysqldbexport.py --skip-gtid %s " % from_conn
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



