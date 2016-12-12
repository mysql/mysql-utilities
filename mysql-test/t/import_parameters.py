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
import_parameters test.
"""

import os
import sys

import import_basic

from mysql.utilities.command.dbcompare import database_compare
from mysql.utilities.exception import MUTLibError, UtilDBError, UtilError


class test(import_basic.test):
    """check parameters for import utility
    This test executes a basic check of parameters for mysqldbimport.
    It uses the import_basic test as a parent for setup and teardown methods.
    """

    def check_prerequisites(self):
        return import_basic.test.check_prerequisites(self)

    def setup(self):
        return import_basic.test.setup(self)

    def do_skip_test(self, cmd_str, comment, expected_res=0):
        """Do skip test.

        cmd_str[in]        Command string.
        comment[in]        Comment.
        expected_res[in]   Expected result.
        """
        # Precheck: check db and save the results.
        self.results.append("BEFORE:\n")
        self.results.append(self.check_objects(self.server2, "util_test"))

        res = self.run_test_case(expected_res, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Now, check db and save the results.
        self.results.append("AFTER:\n")
        res = self.server2.exec_query("SHOW DATABASES LIKE 'util_test'")
        if res == () or res == []:
            self.results.append("Database was NOT created.\n")
        else:
            self.results.append("Database was created.\n")
        self.results.append(self.check_objects(self.server2, "util_test"))

        self.drop_db(self.server2, "util_test")

    def run(self):
        self.res_fname = "result.txt"
        s1_conn_str = self.build_connection_string(self.server1)
        s2_conn_str = self.build_connection_string(self.server2)
        from_conn = "--server={0}".format(s1_conn_str)
        to_conn = "--server={0}".format(s2_conn_str)
        cmp_options = {"no_checksum_table": False,
                       "run_all_tests": True,
                       "quiet": True}
        cmd = ("mysqldbimport.py {0} --import=definitions "
               "{1}").format(to_conn, self.export_import_file)

        case_num = 1
        comment = "Test case {0} - help".format(case_num)
        cmd_opts = " --help"
        cmd_str = "{0} {1}".format(cmd, cmd_opts)
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Remove version information
        self.remove_result_and_lines_after("MySQL Utilities mysqldbimport.py "
                                           "version", 6)

        # Now test the skips

        # Note: data and blobs must be done separately
        _SKIPS = ("grants", "events", "triggers", "views", "procedures",
                  "functions", "tables", "create_db")
        _FORMATS = ("CSV", "SQL")

        case_num += 1
        for frmt in _FORMATS:
            # Create an import file
            export_cmd = ("mysqldbexport.py {0} util_test --export=BOTH "
                          "--skip-gtid --format={1} --display=BRIEF > "
                          "{2}").format(from_conn, frmt,
                                        self.export_import_file)
            comment = "Generating import file"
            res = self.run_test_case(0, export_cmd, comment)
            if not res:
                raise MUTLibError("{0}: failed".format(comment))

            cmd_opts = "{0} --format={1} --skip=".format(cmd, frmt)
            for skip in _SKIPS:
                if case_num != 2 and case_num != 2 + len(_SKIPS):
                    cmd_opts = "{0},".format(cmd_opts)
                cmd_opts = "{0}{1}".format(cmd_opts, skip)
                comment = "Test case {0} - no {1}".format(case_num, skip)
                self.do_skip_test(cmd_opts, comment)
                case_num += 1

        # Now test --skip=data, --skip-blobs
        # Create an import file with blobs
        try:
            self.server1.exec_query("ALTER TABLE util_test.t3 "
                                    "ADD COLUMN me_blob BLOB")
            self.server1.exec_query("UPDATE util_test.t3 SET "
                                    "me_blob = 'This, is a BLOB!'")
        except UtilDBError as err:
            raise MUTLibError("Failed to add blob column: "
                              "{0}".format(err.errmsg))

        export_cmd = ("mysqldbexport.py {0} util_test --export=BOTH "
                      "--skip-gtid --format={1} --display=BRIEF > "
                      "{2} ").format(from_conn, "CSV", self.export_import_file)
        comment = "Generating import file"
        res = self.run_test_case(0, export_cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # No skips for reference (must skip events for deterministic reasons
        cmd_str = ("mysqldbimport.py {0} {1} --import=both --dryrun "
                   "--format=CSV --bulk-insert "
                   "--skip=events").format(to_conn, self.export_import_file)
        comment = "Test case {0} - no {1}".format(case_num, "events")
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        case_num += 1
        cmd_str = ("mysqldbimport.py {0} {1} --import=both --dryrun "
                   "--format=CSV --bulk-insert "
                   "--skip=events,grants,"
                   "data".format(to_conn, self.export_import_file))
        comment = "Test case {0} - no {1}".format(case_num, "data")
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        case_num += 1
        cmd_str = ("mysqldbimport.py {0} {1} --import=both --dryrun "
                   "--format=CSV --skip-blobs --bulk-insert "
                   "--skip=events").format(to_conn, self.export_import_file)
        comment = "Test case {0} - no {1}".format(case_num, "blobs")
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Do a quiet import
        case_num += 1
        cmd_str = ("mysqldbimport.py {0} {1} --import=both --quiet "
                   "--format=CSV "
                   "--bulk-insert").format(to_conn, self.export_import_file)
        comment = "Test case {0} - no {1}".format(case_num, "messages (quiet)")
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Import using multiprocessing.
        case_num += 1
        comment = "Test case {0} - multiprocessing.".format(case_num)
        import_opts = "--multiprocess=2"
        self.drop_db(self.server2, 'util_test')  # drop db before import.
        self.run_import_test(0, from_conn, to_conn, ['util_test'], "SQL",
                             "BOTH", comment, "", import_opts)

        # Import using autocommit.
        case_num += 1
        comment = "Test case {0} - autocommit.".format(case_num)
        import_opts = "--autocommit"
        self.drop_db(self.server2, 'util_test')  # drop db before import.
        self.run_import_test(0, from_conn, to_conn, ['util_test'], "SQL",
                             "BOTH", comment, "", import_opts)

        # Import multiple files at once
        # Test multiple formats and displays
        _FORMATS = ("SQL", "CSV", "TAB", "GRID", "VERTICAL")
        _DISPLAYS = ("BRIEF", "FULL")
        case_num += 1
        res = True
        database_list = ['util_test_fk', 'util_test_fk2', 'util_test_fk3']

        # Drop existing databases on both servers and load databases from
        # fkeys.sql into both server1 and server2, since they do not have
        # unsupported features (for formats other than sql) such as
        # auto-increment.
        self.server1.disable_foreign_key_checks(True)
        self.server2.disable_foreign_key_checks(True)
        self.drop_all()
        for db in database_list:
            self.drop_db(self.server1, db)
            self.drop_db(self.server2, db)

        # Load databases from fkeys.sql into both server1 and server2, since
        # they do not have unsupported csv features such as auto-increment.
        data_file = os.path.normpath("./std_data/fkeys.sql")
        try:
            self.server1.read_and_exec_SQL(data_file, self.debug)
            self.server2.read_and_exec_SQL(data_file, self.debug)
        except UtilError as err:
            raise MUTLibError("Failed to read commands from file "
                              "{0}: {1}".format(data_file, err.errmsg))
        self.server1.disable_foreign_key_checks(False)
        self.server2.disable_foreign_key_checks(False)
        for frmt in _FORMATS:
            for display in _DISPLAYS:
                comment = ("Test Case {0} : Testing multiple import with {1} "
                           "format and {2} display".format(case_num, frmt,
                                                           display))
                # We test DEFINITIONS and DATA separately in other tests
                self.run_import_test(
                    0, from_conn, to_conn, database_list,
                    frmt, "BOTH", comment, " --display={0}".format(display)
                )
                old_stdout = sys.stdout
                try:
                    # redirect stdout to prevent database_compare prints
                    # to reach the MUT output.
                    if not self.verbose:
                        sys.stdout = open(os.devnull, 'w')
                    # Test correctness of data
                    for database in database_list:
                        res = database_compare(s1_conn_str, s2_conn_str,
                                               database, database, cmp_options)
                        if not res:
                            break
                finally:
                    # restore stdout
                    if not self.verbose:
                        sys.stdout.close()
                    sys.stdout = old_stdout

                # Drop dbs from server2 to import them again from the
                # export file
                self.server2.disable_foreign_key_checks(True)
                for db in database_list:
                    self.drop_db(self.server2, db)
                self.server2.disable_foreign_key_checks(False)
                if not res:
                    raise MUTLibError("{0} failed".format(comment))

                case_num += 1

        # Mask multiprocessing warning.
        self.remove_result("# WARNING: Number of processes ")

        # Mask version
        self.replace_result(
            "MySQL Utilities mysqldbimport version",
            "MySQL Utilities mysqldbimport version X.Y.Z\n")

        return res

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        # Kill servers that won't be used anymore
        kill_list = ['export_basic', 'import_basic']
        return (import_basic.test.cleanup(self) and
                self.kill_server_list(kill_list))
