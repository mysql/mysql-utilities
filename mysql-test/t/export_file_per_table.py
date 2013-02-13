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
    """check file-per-table option for export utility
    This test executes a series of export database operations on a single
    server with the --file-per-table option. It uses the export_parameters_def
    test as a parent for setup and teardown methods.
    """

    def check_prerequisites(self):
        return export_parameters_def.test.check_prerequisites(self)

    def setup(self):
        res = export_parameters_def.test.setup(self)
        if not res:
            return False
        return True

    def run(self):
        self.res_fname = "result.txt"

        from_conn = "--server=" + self.build_connection_string(self.server1)

        self.server1.exec_query("CREATE DATABASE IF NOT EXISTS util_test_mt")

        cmd_str = "mysqldbexport.py %s util_test_mt --export=definitions " \
                  "--file-per-table --skip-gtid " % from_conn 
        comment = "Test case 1 - warning: def only with --file-per-table"
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        try:
            self.server1.exec_query("DROP DATABASE util_test_mt")
        except:
            raise MUTLibError("Cannot drop database for test case 1.")

        _FORMAT_DISPLAY = ("sql","grid","csv","tab","vertical")

        cmd_str = "mysqldbexport.py util_test --export=data --skip-gtid " \
                  "--file-per-table %s --quiet --format=" % from_conn
        starting_case_num = 2

        for format in _FORMAT_DISPLAY:
            cmd_variant = cmd_str + format
            comment = "Test case %s - %s format with --file-per-table" % \
                      (starting_case_num, format)
            res = self.run_test_case(0, cmd_variant, comment)
            starting_case_num += 1
            if not res:
                raise MUTLibError("%s: failed" % comment)

            # Now check the output for the correct files and delete them.
            self.results.append("# Checking for file-per-table creation:\n")
            for i in range(1,5):
                file_name = "util_test.t%d.%s" % (i, format.lower())
                if os.path.exists(file_name):
                    self.results.append("# %22s ................. [PASS]\n" % \
                                        file_name)
                    os.unlink(file_name)
                else:
                    self.results.append("# %22s ................. [FAIL]\n" % \
                                        file_name)
                    raise MUTLibError("File from export missing: %s" % \
                                       file_name)
            self.results.append("\n")

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        return export_parameters_def.test.cleanup(self)
