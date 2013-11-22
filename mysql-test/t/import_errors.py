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
    """Import Data
    This test executes the import utility on a single server.
    It tests the error conditions for importing data.
    It uses the import_basic test for setup and teardown methods.
    """

    def check_prerequisites(self):
        return import_basic.test.check_prerequisites(self)

    def setup(self):
        return import_basic.test.setup(self)

    def run(self):
        self.res_fname = "result.txt"

        from_conn = "--server={0}".format(
            self.build_connection_string(self.server1))
        to_conn = "--server={0}".format(
            self.build_connection_string(self.server2))

        _FORMATS = ("CSV", "TAB", "GRID", "VERTICAL")
        test_num = 1
        for frmt in _FORMATS:
            comment = ("Test Case {0} : Testing import with "
                       "{1} format and NAMES display".format(test_num, frmt))
            # We test DEFINITIONS and DATA only in other tests
            self.run_import_test(1, from_conn, to_conn, 'util_test', frmt,
                                 "BOTH", comment, " --display=NAMES")
            self.drop_db(self.server2, "util_test")
            test_num += 1

        export_cmd = ("mysqldbexport.py {0} util_test --export=BOTH "
                      "--format=SQL --skip-gtid > "
                      "{1}".format(from_conn, self.export_import_file))

        # First run the export to a file.
        res = self.run_test_case(0, export_cmd, "Running export...")
        if not res:
            raise MUTLibError("EXPORT: {0}: failed".format(comment))

        import_cmd = "mysqldbimport.py {0} ".format(to_conn)

        comment = "Test case {0} - no file specified ".format(test_num)
        cmd_str = import_cmd + " --import=BOTH --format=SQL"
        res = self.run_test_case(2, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        test_num += 1

        import_cmd += "{0} --import=BOTH --format=SQL".format(
            self.export_import_file)

        comment = "Test case {0} - bad --skip values".format(test_num)
        cmd_str = import_cmd + " --skip=events,wiki-waki,woo-woo "
        res = self.run_test_case(1, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        test_num += 1

        comment = "Test case {0} - exporting data and skipping data".format(
            test_num)
        cmd_str = import_cmd + " --skip=data --import=data"
        res = self.run_test_case(1, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        test_num += 1

        cmd_str = "mysqldbimport.py --server=rocks_rocks_rocks {0} ".format(
            self.export_import_file)
        comment = "Test case {0} - cannot parse --server".format(test_num)
        res = self.run_test_case(2, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        test_num += 1

        cmd_str = ("mysqldbimport.py {0} --server=nope:nada@localhost:"
                   "{1}".format(self.export_import_file, self.server0.port))
        comment = "Test case {0} - error: cannot connect to server".format(
            test_num)
        res = self.run_test_case(1, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        test_num += 1

        self.server2.exec_query("CREATE USER 'joe'@'localhost'")

        # Watchout for Windows: it doesn't use sockets!
        if os.name == "posix":
            joe_conn = "--server=joe@localhost:{0}".format(self.server2.port)
            if self.server2.socket is not None:
                joe_conn = "{0}:{1}".format(joe_conn, self.server2.socket)
        else:
            joe_conn = "--server=joe@localhost:{0} ".format(self.server2.port)

        cmd_str = "mysqldbimport.py {0} {1} ".format(
            joe_conn, self.export_import_file)
        comment = "Test case {0} - error: not enough privileges".format(
            test_num)
        res = self.run_test_case(1, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        test_num += 1

        cmd_str = "mysqldbimport.py {0} {1} --import=definitions".format(
            joe_conn, self.export_import_file)
        comment = "Test case {0} - error: not enough privileges".format(
            test_num)
        res = self.run_test_case(1, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        test_num += 1

        bad_sql_file = os.path.normpath("./std_data/bad_sql.sql")

        cmd_str = "mysqldbimport.py {0} {1} --import=definitions".format(
            to_conn, bad_sql_file)
        comment = "Test case {0} - error: bad SQL statements".format(test_num)
        res = self.run_test_case(1, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        test_num += 1

        self.drop_db(self.server2, "util_test")

        # Skipping create and doing the drop should be illegal.
        cmd_str = ("{0} {1} --skip=create_db --format=sql --import=data "
                   "--drop-first ".format(import_cmd, self.export_import_file))
        comment = ("Test case {0} - error: --skip=create_db & "
                   "--drop-first".format(test_num))
        res = self.run_test_case(1, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        test_num += 1

        self.drop_db(self.server2, "util_test")

        import_cmd = "mysqldbimport.py {0} ".format(to_conn)
        cmd_str = ("{0} {1} --skip-blobs --format=sql --import=definitions "
                   "".format(import_cmd, self.export_import_file))
        comment = "Test case {0} - warning: --skip-blobs".format(test_num)
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        test_num += 1

        cmd_str = ("{0} {1} --skip=data --format=sql --import=data "
                   "".format(import_cmd, self.export_import_file))

        comment = "Test case {0} - error: --skip=data & --import=data".format(
            test_num)
        res = self.run_test_case(1, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        test_num += 1

        bad_csv_file = os.path.normpath("./std_data/bad_object.csv")

        cmd_str = "{0} {1} --format=csv --import=both ".format(import_cmd,
                                                               bad_csv_file)

        comment = "Test case {0} - error: bad object definition".format(
            test_num)
        res = self.run_test_case(1, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        test_num += 1

        # Test database with backticks
        _FORMATS_BACKTICKS = ("CSV", "TAB")
        for frmt in _FORMATS_BACKTICKS:
            comment = ("Test Case {0} : Testing import with {1} format and "
                       "NAMES display (using backticks)".format(test_num,
                                                                frmt))
            self.run_import_test(1, from_conn, to_conn, '`db``:db`', frmt,
                                 "BOTH", comment, " --display=NAMES")
            self.drop_db(self.server2, '`db``:db`')
            test_num += 1

        cmd_str = ("mysqldbimport.py {0} {1} "
                   "--character-set=unsupported_charset"
                   "".format(self.export_import_file, to_conn))
        comment = "Test case {0} - invalid --character-set".format(test_num)
        res = self.run_test_case(1, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        if os.name != "posix":
            self.replace_result("# Importing definitions and data from "
                                "std_data\\bad_object.csv",
                                "# Importing definitions and data from "
                                "std_data/bad_object.csv.\n")
            self.replace_result("# Importing definitions from "
                                "std_data\\bad_sql.sql",
                                "# Importing definitions from "
                                "std_data/bad_sql.sql.\n")

        # Mask known source and destination host name.
        self.replace_substring("on localhost", "on XXXX-XXXX")
        self.replace_substring("on [::1]", "on XXXX-XXXX")

        self.replace_result("ERROR: Query failed.", "ERROR: Query failed.\n")

        self.replace_substring("1045 (28000)", "1045")

        self.replace_substring(" (28000)", "")
        self.replace_result("ERROR: Query failed.", "ERROR: Query failed.\n")

        self.replace_substring("1045 (28000)", "1045")

        self.replace_result("mysqldbimport.py: error: Server connection "
                            "values invalid",
                            "mysqldbimport.py: error: Server connection "
                            "values invalid\n")

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        try:
            self.server2.exec_query("DROP USER 'joe'@'localhost'")
        except UtilError:
            pass
        return import_basic.test.drop_all(self)




