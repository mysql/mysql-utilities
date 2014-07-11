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
export_basic test.
"""

import os

import copy_db_parameters

from mysql.utilities.exception import MUTLibError, UtilError


_OUTPUT_FILE = "export_result.sql"


class test(copy_db_parameters.test):
    """Export Data
    This test executes the export utility on a single server. It uses the
    copy_db_parameters test to setup.
    """

    def check_prerequisites(self):
        return copy_db_parameters.test.check_prerequisites(self)

    def setup(self):
        copy_db_parameters.test.setup(self)

        # Create database to export data with unicode characters
        data_file_import = os.path.normpath("./std_data/import_data.sql")
        try:
            self.server1.read_and_exec_SQL(data_file_import, self.debug)
        except UtilError as err:
            raise MUTLibError("Failed to read commands from file "
                              "{0}: {1}".format(data_file_import, err.errmsg))

        return True

    def run(self):
        self.mask_global = False  # Turn off global masks
        self.res_fname = "result.txt"

        from_conn = "--server={0}".format(
            self.build_connection_string(self.server1))

        cmd = "mysqldbexport.py {0} util_test --skip-gtid ".format(from_conn)

        test_num = 1
        comment = "Test case {0} - export metadata only".format(test_num)
        cmd_str = ("{0} --export=definitions --format=SQL "
                   "--skip=events ".format(cmd))
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - export data only - single "
                   "rows".format(test_num))
        cmd_str = "{0} --export=data --format=SQL ".format(cmd)
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - export data only - bulk "
                   "insert".format(test_num))
        cmd_str = "{0} --export=DATA --format=SQL --bulk-insert".format(cmd)
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = "Test case {0} - export data and metadata".format(test_num)
        cmd_str = "{0} --export=both --format=SQL --skip=events".format(cmd)
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - export data and metadata with "
                   "quiet".format(test_num))
        cmd_str = ("{0} --export=both --format=SQL --skip=events "
                   "--quiet".format(cmd))
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - export data and metadata with "
                   "debug".format(test_num))
        cmd_str = ("{0} --export=both --format=SQL --skip=events "
                   "-vvv".format(cmd))
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - export data and metadata with "
                   "multiprocessing (2 processes).").format(test_num)
        cmd_str = ("{0} --export=both --format=SQL --skip=events "
                   "--multiprocess=2").format(cmd)
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - export data and metadata to "
                   "output file.").format(test_num)
        cmd_str = ("{0} --export=both --format=SQL --skip=events "
                   "--output-file={1}").format(cmd, _OUTPUT_FILE)
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        # Send output file contents to results.
        self.results.append("Output file results:\n")
        self.record_results(_OUTPUT_FILE)

        test_num += 1
        # Set input parameter with appropriate quotes for the OS
        if os.name == 'posix':
            cmd_arg = "'`db``:db`' --export=both"
        else:
            cmd_arg = '"`db``:db`" --export=both'
        cmd_str = "mysqldbexport.py {0} {1} --skip-gtid".format(from_conn,
                                                                cmd_arg)
        comment = ("Test case {0} - export database with weird names "
                   "(backticks)".format(test_num))
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        # Insert data with special characters in `db``:db`
        special_chars = r'\0\'\"\b\n\r\t\Z\\\%\_'
        insert_query = ("INSERT INTO `db``:db`.```t``export_1` (other) "
                        "VALUES ('{0}')".format(special_chars))
        self.server1.exec_query(insert_query)
        comment = ("Test case {0} - export data with special "
                   "characters".format(test_num))
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - export data with unicode "
                   "characters".format(test_num))
        cmd_str = "{0} --export=data --format=SQL import_test".format(cmd)
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        self.replace_result("Time:", "Time:       XXXXXX\n")

        _REPLACEMENTS = ("PROCEDURE", "FUNCTION", "TRIGGER", "SQL")

        for replace in _REPLACEMENTS:
            self.mask_result_portion("CREATE", "DEFINER=", replace,
                                     "DEFINER=`XXXX`@`XXXXXXXXX` ")

        self.replace_substring("on [::1]", "on localhost")

        self.remove_result("# WARNING: The server supports GTIDs")

        # Mask event
        self.replace_result("CREATE DEFINER=`root`@`localhost` "
                            "EVENT ```e``export_1` "
                            "ON SCHEDULE EVERY 1 YEAR STARTS",
                            "CREATE EVENT ```e``export_1` "
                            "ON SCHEDULE EVERY 1 YEAR STARTS [...]\n")
        # Mask event for 5.1 servers
        self.replace_result("CREATE EVENT ```e``export_1` "
                            "ON SCHEDULE EVERY 1 YEAR STARTS",
                            "CREATE EVENT ```e``export_1` "
                            "ON SCHEDULE EVERY 1 YEAR STARTS [...]\n")
        # Mask multiprocessing warning.
        self.remove_result("# WARNING: Number of processes ")
        # Mask already existing outfile (in case cleanup-up fails).
        self.remove_result("# WARNING: Specified output file already exists.")

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        self.drop_db(self.server1, 'import_test')
        try:
            os.remove(_OUTPUT_FILE)
        except OSError:
            pass  # Ignore if file cannot be removed (may not exist).
        return copy_db_parameters.test.cleanup(self)
