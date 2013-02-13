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
import mutlib
from mysql.utilities.exception import MUTLibError

class test(mutlib.System_test):
    """check indexes for duplicates and redundancies
    This test executes the check index utility on a single server displaying
    the best and worst indexes from a large database - employees.
    """

    def check_prerequisites(self):
        # Need non-Windows platform
        if os.name == "nt":
            raise MUTLibError("Test requires a non-Windows platform.")
        res = self.check_num_servers(1)
        self.server1 = self.servers.get_server(0)
        rows = []
        try:
            rows = self.server1.exec_query("SHOW DATABASES LIKE 'employees'")
        except:
            pass
        if len(rows) == 0:
            raise MUTLibError("Need employees database loaded on %s" % \
                               self.server1.role)
        return res

    def setup(self):
        return True   # No setup needed
        
    def run(self):
        self.res_fname = "result.txt"
        from_conn = "--server=" + self.build_connection_string(self.server1)

        cmd_str = "mysqlindexcheck.py %s employees.dept_emp " % from_conn
        cmd_str += " --format=csv "
        
        comment = "Test case 1 - show best indexes"
        res = self.run_test_case(0, cmd_str + "--stats -vv --best=5", comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        comment = "Test case 2 - show worst indexes"
        res = self.run_test_case(0, cmd_str + "--stats -vv --worst=5", comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        # Mask the output
        self.mask_column_result("employees", ",", 7, 'NNNNNNN')
        self.mask_column_result("employees", ",", 8, 'NNNNNNN')
        self.mask_column_result("employees", ",", 9, 'NNNNNNN')

        return True
  
    def get_result(self):
        return self.compare(__name__, self.results)
    
    def record(self):
        return self.save_result_file(__name__, self.results)
    
    def cleanup(self):
        return True    # No cleanup needed


