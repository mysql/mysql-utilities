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
from mysql.utilities.exception import MUTLibError, UtilError

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
        try:
            # Runs analyze table to ensure determinism in the list of indexes
            # returned by the these tests
            self.server1.exec_query("ANALYZE NO_WRITE_TO_BINLOG TABLE "
                                    "employees.departments,"
                                    "employees.dept_emp,"
                                    "employees.dept_manager,"
                                    "employees.employees,"
                                    "employees.salaries")
        except UtilError as err:
            raise MUTLibError("Error Executing ANALYZE TABLE:"
                              "{0}".format(err.errmsg))
        return True

    def run(self):
        self.res_fname = "result.txt"
        from_conn = "--server=" + self.build_connection_string(self.server1)

        cmd_str = "mysqlindexcheck.py %s employees.dept_emp " % from_conn
        cmd_str += " --format=csv "

        test_num = 1
        comment = "Test case {0} - show best indexes".format(test_num)
        cmd = "{0}--stats -vv --best=5".format(cmd_str)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = "Test case {0} - show worst indexes".format(test_num)
        cmd = "{0}--stats -vv --worst=5".format(cmd_str)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = "Test case {0} - show only best index".format(test_num)
        cmd = "{0}--stats -vv --best=1".format(cmd_str)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed" .format(comment))

        test_num += 1
        comment = "Test case {0} - show only worst index".format(test_num)
        cmd = "{0}--stats -vv --worst=1".format(cmd_str)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
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


