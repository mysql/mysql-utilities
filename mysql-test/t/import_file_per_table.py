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
import import_basic
from mysql.utilities.exception import MUTLibError, UtilError


class test(import_basic.test):
    """check file-per-table option for import utility
    This test executes a series of import database operations on a single
    server with the --file-per-table option from the export. It uses the
    import_basic test as a parent for setup and teardown methods.
    """

    def check_prerequisites(self):
        self.check_gtid_unsafe()
        return import_basic.test.check_prerequisites(self)

    def setup(self):
        res = import_basic.test.setup(self)
        if not res:
            return False

        data_file = os.path.normpath("./std_data/basic_data.sql")
        try:
            self.server2.read_and_exec_SQL(data_file, self.debug)
        except MUTLibError as err:
            raise MUTLibError("Failed to read commands from file "
                              "{0}: {1}".format(data_file, err.errmsg))

        # Remove the tables with foreign key checks to simplify test.
        try:
            self.server1.exec_query("SET foreign_key_checks = OFF")
            self.server1.exec_query("DROP TABLE util_test.t3")
            self.server1.exec_query("DROP TABLE util_test.t4")
            self.server2.exec_query("SET foreign_key_checks = OFF")
            self.server2.exec_query("DROP TABLE util_test.t3")
            self.server2.exec_query("DROP TABLE util_test.t4")
        except UtilError:
            raise MUTLibError("Cannot drop tables t3,t4 (setup).")

        return True

    def run(self):
        self.res_fname = "result.txt"

        from_conn = "--server={0}".format(
            self.build_connection_string(self.server1))
        to_conn = "--server={0}".format(
            self.build_connection_string(self.server2))

        _FORMAT_DISPLAY = ("sql", "grid", "csv", "tab", "vertical")

        exp_cmd_str = ("mysqldbexport.py util_test --export=data --skip-gtid "
                       "--file-per-table {0} --quiet "
                       "--format=".format(from_conn))
        imp_cmd_str = ("mysqldbimport.py --import=data {0} "
                       "--format=".format(to_conn))
        starting_case_num = 1

        for format_ in _FORMAT_DISPLAY:
            cmd_variant = exp_cmd_str + format_
            comment = ("Test case {0} - {1} format with "
                       "--file-per-table".format(starting_case_num, format_))
            res = self.run_test_case(0, cmd_variant, comment)
            if not res:
                raise MUTLibError("{0}: failed".format(comment))
            starting_case_num += 1

            # Now check the output for the correct files and delete them.
            self.results.append("# Testing file-per-table import:\n")
            for i in [1, 2, 5]:  # List of tables to be tested
                self.delete_data("util_test.t{0}".format(i))

                file_name = "util_test.t{0}.{1}".format(i, format_.lower())
                cmd_variant = "{0}{1} {2}".format(imp_cmd_str, format_,
                                                  file_name)

                comment = "Running import..."
                res = self.run_test_case(0, cmd_variant, comment)
                if not res:
                    raise MUTLibError("{0}: failed".format(comment))

                try:
                    res = self.server2.exec_query("SELECT * FROM "
                                                  "util_test.t{0}".format(i))
                    self.results.append("# Data from util_test.t{0}:\n".format(
                        i))
                    for row in res:
                        str_ = ""
                        for col in row:
                            # Handle None values
                            if col:
                                str_ = "{0}{1} ".format(str_, col)
                            else:
                                str_ = "{0}NULL ".format(str_)
                        self.results.append(str_ + "\n")

                except UtilError:
                    raise MUTLibError("Cannot get rows from "
                                      "util_test.t{0}".format(i))

                os.unlink(file_name)

        return True

    def delete_data(self, tbl):
        try:
            self.server2.exec_query("SET foreign_key_checks = OFF")
            self.server2.exec_query("DELETE FROM {0}".format(tbl))
        except UtilError:
            raise MUTLibError("Cannot delete rows from {0}".format(tbl))

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        return import_basic.test.cleanup(self)
