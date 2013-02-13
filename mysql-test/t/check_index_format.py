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
import check_index_parameters
from mysql.utilities.exception import MUTLibError

class test(check_index_parameters.test):
    """check format output for the check_index_parameters utility
    This test executes the check index utility parameters on a single server.
    It uses the check_index_parameters test as a parent for setup and
    teardown methods.
    """

    def check_prerequisites(self):
        return check_index_parameters.test.check_prerequisites(self)

    def setup(self):
        return check_index_parameters.test.setup(self)
        
    def run(self):
        self.res_fname = "result.txt"
        from_conn = "--server=" + self.build_connection_string(self.server1)

        cmd_str = "mysqlindexcheck.py %s util_test_a -i  " % from_conn
       
        comment = "Test case 1 - show indexes using default format"
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        comment = "Test case 2 - show indexes using SQL format"
        res = self.run_test_case(0, cmd_str + "--format=sQl", comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        comment = "Test case 3 - show indexes using GRID format"
        res = self.run_test_case(0, cmd_str + "--format=gRId", comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        comment = "Test case 4 - show indexes using TAB format"
        res = self.run_test_case(0, cmd_str + "--format=tab", comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        comment = "Test case 5 - show indexes using CSV format"
        res = self.run_test_case(0, cmd_str + "--format=CSV", comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        comment = "Test case 6 - show indexes using VERTICAL format"
        res = self.run_test_case(0, cmd_str + "--format=VERTICAL", comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        return True
  
    def get_result(self):
        return self.compare(__name__, self.results)
    
    def record(self):
        return self.save_result_file(__name__, self.results)
    
    def cleanup(self):
        return check_index_parameters.test.cleanup(self)


