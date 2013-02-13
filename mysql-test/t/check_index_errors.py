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
import check_index
from mysql.utilities.exception import MUTLibError

class test(check_index.test):
    """check errors for check index
    This test ensures the known error conditions are tested. It uses the
    check_index test as a parent for setup and teardown methods.
    """

    def check_prerequisites(self):
        return check_index.test.check_prerequisites(self)

    def setup(self):
        return check_index.test.setup(self)
        
    def run(self):
        self.res_fname = "result.txt"
        from_conn = "--server=" + self.build_connection_string(self.server1)

        comment = "Test case 1 - error: no db specified"
        res = self.run_test_case(2, "mysqlindexcheck.py ", comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        comment = "Test case 2 - error: invalid source specified"
        res = self.run_test_case(1, "mysqlindexcheck.py util_test "
                                 "--server=nope:nada@nohost", comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        comment = "Test case 3 - error: invalid login to server"
        res = self.run_test_case(1, "mysqlindexcheck.py util_test_a "
                                 "--server=nope:nada@localhost:3306", comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
         
        comment = "Test case 4 - error: stats and best=alpha"
        res = self.run_test_case(2, "mysqlindexcheck.py --stats --best=A "
                                 "util_test_a", comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        
        comment = "Test case 5 - error: stats and worst=alpha"
        res = self.run_test_case(2, "mysqlindexcheck.py --stats --worst=A "
                                 "util_test_a", comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
            
        comment = "Test case 6 - error: not stats "
        res = self.run_test_case(2, "mysqlindexcheck.py --best=1 "
                                 "util_test_a", comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        comment = "Test case 7 - error: stats and both best and worst "
        res = self.run_test_case(2, "mysqlindexcheck.py --stats --best=1 "
                                 "--worst=1 util_test_a", comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        comment = "Test case 8 - error: stats and worst=-1"
        res = self.run_test_case(2, "mysqlindexcheck.py --stats --worst=-1 "
                                 "util_test_a", comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        comment = "Test case 9 - error: stats and best=-1"
        res = self.run_test_case(2, "mysqlindexcheck.py --stats --best=-1 "
                                 "util_test_a", comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        self.replace_result("Error 1045", "Error XXXX: Access denied\n")
        self.replace_result("Error 2003", "Error XXXX: Access denied\n")

        return True
  
    def get_result(self):
        return self.compare(__name__, self.results)
    
    def record(self):
        return self.save_result_file(__name__, self.results)
    
    def cleanup(self):
        return check_index.test.cleanup(self)



