#
# Copyright (c) 2010, 2014, Oracle and/or its affiliates. All rights reserved.
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

import import_basic

from mysql.utilities.exception import MUTLibError, UtilDBError


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

        from_conn = "--server={0}".format(
            self.build_connection_string(self.server1)
        )
        to_conn = "--server={0}".format(
            self.build_connection_string(self.server2)
        )

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
                   "--skip=events,data").format(to_conn,
                                                self.export_import_file)
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
        self.run_import_test(0, from_conn, to_conn, 'util_test', "SQL",
                             "BOTH", comment, "", import_opts)

        # Import using autocommit.
        case_num += 1
        comment = "Test case {0} - autocommit.".format(case_num)
        import_opts = "--autocommit"
        self.drop_db(self.server2, 'util_test')  # drop db before import.
        self.run_import_test(0, from_conn, to_conn, 'util_test', "SQL",
                             "BOTH", comment, "", import_opts)

        # Mask multiprocessing warning.
        self.remove_result("# WARNING: Number of processes ")

        # Mask version
        self.replace_result(
            "MySQL Utilities mysqldbimport version",
            "MySQL Utilities mysqldbimport version X.Y.Z "
            "(part of MySQL Workbench ... XXXXXX)\n"
        )

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        # Kill servers that won't be used anymore
        kill_list = ['export_basic', 'import_basic']
        return (import_basic.test.cleanup(self) and
                self.kill_server_list(kill_list))
