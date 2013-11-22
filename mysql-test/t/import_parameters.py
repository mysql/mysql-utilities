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
            self.build_connection_string(self.server1))
        to_conn = "--server={0}".format(
            self.build_connection_string(self.server2))

        cmd_str = "mysqldbimport.py {0} {1} --import=definitions ".format(
            to_conn, self.export_import_file)

        test_num = 1
        cmd_opts = " --help"
        comment = "Test case {0} - help".format(test_num)
        res = self.run_test_case(0, cmd_str + cmd_opts, comment)
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

        test_num = 2
        for format_ in _FORMATS:
            # Create an import file
            export_cmd = ("mysqldbexport.py {0} util_test --export=BOTH {0} "
                          "--skip-gtid --format={1} --display=BRIEF > "
                          "{2} ".format(from_conn, format_,
                                        self.export_import_file))
            comment = "Generating import file"
            res = self.run_test_case(0, export_cmd, comment)
            if not res:
                raise MUTLibError("{0}: failed".format(comment))

            cmd_opts = "{0} --format={1} --skip=".format(cmd_str, format_)
            for skip in _SKIPS:
                if test_num != 2 and test_num != 2 + len(_SKIPS):
                    cmd_opts += ","
                cmd_opts += skip
                comment = "Test case {0} - no {1}".format(test_num, skip)
                self.do_skip_test(cmd_opts, comment)
                test_num += 1

        # Now test --skip=data, --skip-blobs
        # Create an import file with blobs
        try:
            self.server1.exec_query("ALTER TABLE util_test.t3 "
                                    "ADD COLUMN me_blob BLOB")
            self.server1.exec_query("UPDATE util_test.t3 SET "
                                    "me_blob = 'This, is a BLOB!'")
        except UtilDBError as err:
            raise MUTLibError("Failed to add blob column: {0}".format(
                err.errmsg))

        export_cmd = ("mysqldbexport.py {0} util_test --export=BOTH "
                      "--skip-gtid --format={1} --display=BRIEF > {2}"
                      "".format(from_conn, "CSV", self.export_import_file))
        comment = "Generating import file"
        res = self.run_test_case(0, export_cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # No skips for reference (must skip events for deterministic reasons
        cmd_str = ("mysqldbimport.py {0} {1} --import=both --dryrun  "
                   "--format=CSV "
                   "--bulk-insert ".format(to_conn,  self.export_import_file))
        comment = "Test case {0} - no events".format(test_num)
        res = self.run_test_case(0, cmd_str + "--skip=events", comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        test_num += 1

        cmd_str = ("mysqldbimport.py {0} {1} --import=both --dryrun "
                   "--format=CSV "
                   "--bulk-insert ".format(to_conn,  self.export_import_file))

        comment = "Test case {0} - no data".format(test_num)
        res = self.run_test_case(0, cmd_str + "--skip=events,data", comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        test_num += 1

        cmd_str = ("mysqldbimport.py {0} {1} --import=both --dryrun "
                   "--format=CSV --skip-blobs "
                   "--bulk-insert ".format(to_conn, self.export_import_file))

        comment = "Test case {0} - no blobs".format(test_num)
        res = self.run_test_case(0, cmd_str + "--skip=events", comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        test_num += 1

        # Lastly, do a quiet import

        cmd_str = ("mysqldbimport.py {0} {1} --import=both --quiet "
                   "--format=CSV "
                   "--bulk-insert ".format(to_conn, self.export_import_file))
        comment = "Test case {0} - no messages (quiet)".format(test_num)
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

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
