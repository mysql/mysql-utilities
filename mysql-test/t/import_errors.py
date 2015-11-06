#
# Copyright (c) 2010, 2015, Oracle and/or its affiliates. All rights reserved.
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

"""
import_errors test.
"""

import os
import subprocess

import import_basic

from mysql.utilities.exception import MUTLibError, UtilError


class test(import_basic.test):
    """Import Data
    This test executes the import utility on a single server.
    It tests the error conditions for importing data.
    It uses the import_basic test for setup and teardown methods.
    """

    perms_test_file = "not_readable.sql"

    def check_prerequisites(self):
        return import_basic.test.check_prerequisites(self)

    def setup(self):
        return import_basic.test.setup(self)

    def run(self):
        self.res_fname = "result.txt"

        from_conn = "--server={0}".format(
            self.build_connection_string(self.server1)
        )
        to_conn = "--server={0}".format(
            self.build_connection_string(self.server2)
        )

        _FORMATS = ("CSV", "TAB", "GRID", "VERTICAL")
        test_num = 1
        for frmt in _FORMATS:
            comment = ("Test Case {0} : Testing import with "
                       "{1} format and NAMES display").format(test_num, frmt)
            # We test DEFINITIONS and DATA only in other tests
            self.run_import_test(1, from_conn, to_conn, ['util_test'], frmt,
                                 "BOTH", comment, " --display=NAMES")
            self.drop_db(self.server2, "util_test")
            test_num += 1

        export_cmd = ("mysqldbexport.py {0} util_test --export=BOTH "
                      "--format=SQL --skip-gtid  > "
                      "{1}").format(from_conn, self.export_import_file)

        # First run the export to a file.
        comment = "Running export..."
        res = self.run_test_case(0, export_cmd, comment)
        if not res:
            raise MUTLibError("EXPORT: {0}: failed".format(comment))

        import_cmd = "mysqldbimport.py {0}".format(to_conn)

        comment = "Test case {0} - no file specified ".format(test_num)
        cmd_str = "{0} --import=BOTH --format=SQL".format(import_cmd)
        res = self.run_test_case(2, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        import_cmd = ("{0} {1} --import=BOTH "
                      "--format=SQL").format(import_cmd,
                                             self.export_import_file)

        test_num += 1
        comment = "Test case {0} - bad --skip values".format(test_num)
        cmd_str = "{0} --skip=events,wiki-waki,woo-woo".format(import_cmd)
        res = self.run_test_case(1, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - exporting data and skipping "
                   "data").format(test_num)
        cmd_str = "{0} --skip=data --import=data".format(import_cmd)
        res = self.run_test_case(1, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = "Test case {0} - cannot parse --server".format(test_num)
        cmd_str = ("mysqldbimport.py --server=rocks_rocks_rocks "
                   "{0}").format(self.export_import_file)
        res = self.run_test_case(2, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - error: cannot connect to "
                   "server").format(test_num)
        cmd_str = ("mysqldbimport.py --server=nope:nada@localhost:{0} "
                   "{1}").format(self.server0.port, self.export_import_file)
        res = self.run_test_case(1, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        self.server2.exec_query("CREATE USER 'joe'@'localhost'")

        # Watchout for Windows: it doesn't use sockets!
        joe_conn = "--server=joe@localhost:{0}".format(self.server2.port)
        if os.name == "posix" and self.server2.socket is not None:
            joe_conn = "{0}:{1}".format(joe_conn, self.server2.socket)

        test_num += 1
        comment = ("Test case {0} - error: not enough "
                   "privileges").format(test_num)
        cmd_str = "mysqldbimport.py {0} {1}".format(joe_conn,
                                                    self.export_import_file)
        res = self.run_test_case(1, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - error: not enough "
                   "privileges").format(test_num)
        cmd_str = ("mysqldbimport.py {0} {1} "
                   "--import=definitions").format(joe_conn,
                                                  self.export_import_file)
        res = self.run_test_case(1, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = "Test case {0} - error: bad SQL statements".format(test_num)
        bad_sql_file = os.path.normpath("./std_data/bad_sql.sql")
        cmd_str = ("mysqldbimport.py {0} {1} "
                   "--import=definitions").format(to_conn, bad_sql_file)
        res = self.run_test_case(1, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        self.drop_db(self.server2, "util_test")

        # Skipping create and doing the drop should be illegal.
        test_num += 1
        comment = ("Test case {0} - error: --skip=create_db & "
                   "--drop-first").format(test_num)
        cmd_str = ("{0} {1} --skip=create_db --format=sql --import=data "
                   "--drop-first ").format(import_cmd, self.export_import_file)
        res = self.run_test_case(1, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        self.drop_db(self.server2, "util_test")

        import_cmd = "mysqldbimport.py {0}".format(to_conn)

        test_num += 1
        comment = "Test case {0} - warning: --skip-blobs".format(test_num)
        cmd_str = ("{0} --skip-blobs --format=sql --import=definitions "
                   "{1}").format(import_cmd, self.export_import_file)
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - error: --skip=data & "
                   "--import=data").format(test_num)
        cmd_str = ("{0} --skip=data --format=sql --import=data "
                   "{1}").format(import_cmd, self.export_import_file)
        res = self.run_test_case(1, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - error: bad object "
                   "definition").format(test_num)
        bad_csv_file = os.path.normpath("./std_data/bad_object.csv")
        cmd_str = ("{0} --format=csv --import=both "
                   "{1}").format(import_cmd, bad_csv_file)
        res = self.run_test_case(1, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        # Test database with backticks
        _FORMATS_BACKTICKS = ("CSV", "TAB")
        for frmt in _FORMATS_BACKTICKS:
            comment = ("Test Case {0} : Testing import with {1} format and "
                       "NAMES display (using backticks)").format(test_num,
                                                                 frmt)
            self.run_import_test(1, from_conn, to_conn, ['`db``:db`'],
                                 frmt, "BOTH", comment, " --display=NAMES")
            self.drop_db(self.server2, '`db``:db`')
            test_num += 1

        comment = "Test case {0} - invalid --character-set".format(test_num)
        cmd_str = ("mysqldbimport.py {0} {1} "
                   "--character-set=unsupported_charset"
                   "".format(self.export_import_file, to_conn))
        res = self.run_test_case(1, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Run export to re-create the export file.
        comment = "Running export to {0}...".format(self.export_import_file)
        res = self.run_test_case(0, export_cmd, comment)
        if not res:
            raise MUTLibError("EXPORT: {0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - error: invalid multiprocess "
                   "value.").format(test_num)
        cmd_str = ("{0} --format=sql --import=both --multiprocess=0.5 "
                   "{1}").format(import_cmd, self.export_import_file)
        res = self.run_test_case(2, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - error: multiprocess value smaller than "
                   "zero.").format(test_num)
        cmd_str = ("{0} --format=sql --import=both --multiprocess=-1 "
                   "{1}").format(import_cmd, self.export_import_file)
        res = self.run_test_case(2, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - error: invalid max bulk insert "
                   "value.").format(test_num)
        cmd_str = ("{0} --format=sql --import=both --max-bulk-insert=2.5 "
                   "{1}").format(import_cmd, self.export_import_file)
        res = self.run_test_case(2, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - error: max bulk insert value not greater "
                   "than one.").format(test_num)
        cmd_str = ("{0} --format=sql --import=both --max-bulk-insert=1 "
                   "{1}").format(import_cmd, self.export_import_file)
        res = self.run_test_case(2, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        self.drop_db(self.server2, "util_test")

        test_num += 1
        comment = ("Test case {0} - warning: max bulk insert ignored without "
                   "bulk insert option.").format(test_num)
        cmd_str = ("{0} --format=sql --import=both --max-bulk-insert=10000 "
                   "{1}").format(import_cmd, self.export_import_file)
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - error: Use --drop-first to drop the "
                   "database before importing.").format(test_num)
        data_file = os.path.normpath("./std_data/basic_data.sql")
        cmd_str = ("{0} --format=sql --import=both "
                   "{1}").format(import_cmd, data_file)
        res = self.run_test_case(1, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - error: Is not a valid path to a file."
                   "").format(test_num)
        cmd_str = ("{0} --format=sql --import=both not_exist.sql"
                   "").format(import_cmd)
        res = self.run_test_case(2, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - error: Without permission to read a file."
                   "").format(test_num)
        cmd_str = ("{0} --format=sql --import=both {1}"
                   "").format(import_cmd, self.perms_test_file)

        # Create file without read permission.
        with open(self.perms_test_file, "w"):
            pass
        if os.name == "posix":
            os.chmod(self.perms_test_file, 0200)
        else:
            proc = subprocess.Popen(["icacls", self.perms_test_file, "/deny",
                                     "everyone:(R)"], stdout=subprocess.PIPE)
            proc.communicate()

        res = self.run_test_case(2, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Handle message with path (replace '\' by '/').
        if os.name != "posix":
            self.replace_result("# Importing definitions and data from "
                                "std_data\\bad_object.csv",
                                "# Importing definitions and data from "
                                "std_data/bad_object.csv.\n")
            self.replace_result("# Importing definitions from "
                                "std_data\\bad_sql.sql",
                                "# Importing definitions from "
                                "std_data/bad_sql.sql.\n")
            self.replace_result("# Importing definitions and data from "
                                "std_data\\basic_data.sql.",
                                "# Importing definitions and data from "
                                "std_data/basic_data.sql.\n")

        # Mask known source and destination host name.
        self.replace_substring("on localhost", "on XXXX-XXXX")
        self.replace_substring("on [::1]", "on XXXX-XXXX")

        self.replace_substring(" (28000)", "")
        self.replace_result("ERROR: Query failed.", "ERROR: Query failed.\n")

        self.replace_substring("Error 1045 (28000):", "Error")
        self.replace_substring("Error 1045:", "Error")

        self.replace_result("mysqldbimport: error: Server connection "
                            "values invalid",
                            "mysqldbimport: error: Server connection "
                            "values invalid\n")

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        try:
            if os.path.exists(self.perms_test_file):
                if os.name != "posix":
                    # Add write permission to the permissions test file so
                    # that its deletion is possible when using MS Windows.
                    proc = subprocess.Popen(["icacls", self.perms_test_file,
                                             "/grant", "everyone:(W)"],
                                            stdout=subprocess.PIPE)
                    proc.communicate()
                os.unlink(self.perms_test_file)
        except OSError:
            pass
        try:
            self.server2.exec_query("DROP USER 'joe'@'localhost'")
        except UtilError:
            pass
        return import_basic.test.drop_all(self)
