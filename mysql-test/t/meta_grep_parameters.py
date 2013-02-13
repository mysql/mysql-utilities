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
import meta_grep
from mysql.utilities.exception import MUTLibError

class test(meta_grep.test):
    """Process grep
    This test executes the meta grep utility parameters.
    It uses the meta_grep test as a parent for setup and teardown methods.
    """

    def check_prerequisites(self):
        return meta_grep.test.check_prerequisites(self)

    def setup(self):
        return meta_grep.test.setup(self)
        
    def run(self):
        self.res_fname = "result.txt"
        from_conn = self.build_connection_string(self.server1)
        conn_val = self.get_connection_values(self.server1)

        cmd_str = "mysqlmetagrep.py --server=%s " % from_conn + \
                  "--database=util_test --format=CSV "
       
        comment = "Test case 1 - do the help"
        res = self.run_test_case(0, cmd_str + "--help", comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        comment = "Test case 2 - do the SQL for a simple search"
        cmd_str = "mysqlmetagrep.py --sql "
        cmd_str += " -Gb --pattern=t2"
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        comment = "Test case 3 - do the SQL for a simple search with type"
        cmd_str = "mysqlmetagrep.py --sql --search-objects=table"
        cmd_str += " -Gb --pattern=t2"
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        self.mask_column_result("root:*@localhost", ",", 1, "root[...]")
        
        return True
  
    def get_result(self):
        return self.compare(__name__, self.results)
    
    def record(self):
        return self.save_result_file(__name__, self.results)
    
    def cleanup(self):
        return meta_grep.test.cleanup(self)


