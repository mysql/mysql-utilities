#
# Copyright (c) 2010, 2016, Oracle and/or its affiliates. All rights reserved.
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
export_parameters_def test.
"""

import export_basic

from mysql.utilities.exception import MUTLibError


class test(export_basic.test):
    """check parameters for export utility
    This test executes a series of export database operations on a single
    server using a variety of parameters. It uses the export_basic test
    as a parent for setup and teardown methods.
    """

    server0 = None

    def check_prerequisites(self):
        self.server0 = self.servers.get_server(0)
        if not self.server0.check_version_compat(5, 7, 9):
            raise MUTLibError("Test requires server version 5.7.9 and later.")
        sql_mode = self.server0.show_server_variable("SQL_MODE")[0]
        if len(sql_mode[1]):
            raise MUTLibError("Test requires servers with sql_mode = ''.")
        # The innodb_default_row_format was introduce in 5.7.9
        if not self.servers.get_server(0).check_version_compat(5, 7, 9):
            raise MUTLibError("Test requires server version 5.7.9 and later.")
        innodb_row_format = \
            self.server0.show_server_variable("innodb_default_row_format")[0]
        if innodb_row_format[1].upper() != "COMPACT":
            raise MUTLibError("Test requires servers with"
                              " innodb_default_row_format = 'COMPACT'.")
        return export_basic.test.check_prerequisites(self)

    def setup(self, spawn_servers=True):
        return export_basic.test.setup(self)

    def run(self):
        self.res_fname = "result.txt"

        from_conn = ("--server="
                     "{0}".format(self.build_connection_string(self.server1)))

        cmd_str = "mysqldbexport.py --skip-gtid {0} ".format(from_conn)

        test_num = 1
        cmd_opts = "util_test --help"
        comment = "Test case {0} - help".format(test_num)
        res = self.run_test_case(0, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Remove version information
        self.remove_result_and_lines_after("MySQL Utilities mysqldbexport.py "
                                           "version", 6)

        # Now test the skips
        test_num += 1
        cmd_opts = "{0} util_test --skip=grants".format(cmd_str)
        comment = "Test case {0} - no grants".format(test_num)
        res = self.run_test_case(0, cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        cmd_opts = "{0},events".format(cmd_opts)
        comment = "Test case {0} - no events".format(test_num)
        res = self.run_test_case(0, cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        cmd_opts = "{0},triggers".format(cmd_opts)
        comment = "Test case {0} - no triggers".format(test_num)
        res = self.run_test_case(0, cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        cmd_opts = "{0},procedures".format(cmd_opts)
        comment = "Test case {0} - no procedures".format(test_num)
        res = self.run_test_case(0, cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        cmd_opts = "{0},functions".format(cmd_opts)
        comment = "Test case {0} - no functions".format(test_num)
        res = self.run_test_case(0, cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        cmd_opts = "{0},tables".format(cmd_opts)
        comment = "Test case {0} - no tables".format(test_num)
        res = self.run_test_case(0, cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        cmd_opts = "{0},create_db".format(cmd_opts)
        comment = "Test case {0} - no create_db".format(test_num)
        res = self.run_test_case(0, cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        cmd_opts += "{0},data".format(cmd_opts)
        comment = "Test case {0} - no data".format(test_num)
        res = self.run_test_case(0, cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        cmd_opts = ("{0} util_test --format=SQL "
                    "--export=definitions".format(cmd_str))
        comment = "Test case {0} - SQL single rows".format(test_num)
        res = self.run_test_case(0, cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = "Test case {0} - SQL bulk insert".format(test_num)
        res = self.run_test_case(0, "{0} --bulk-insert".format(cmd_opts),
                                 comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        self.test_format_and_display_values("{0} util_test "
                                            "--export=definitions "
                                            "--format=".format(cmd_str), 13)

        return True

    def test_format_and_display_values(self, cmd_opts, starting_case_num,
                                       full_format=True, no_headers=True,
                                       abbrev=True, displays=True):
        """Test format and display values.

        cmd_opts[in]            Commands options.
        starting_case_num[in]   Starting case number.
        full_format[in]         True for full format.
        no_headers[in]          True for no header.
        abbrev[in]              True for abbrev.
        displays[in]            True for displays.
        """
        _FORMATS = ("sql", "csv", "tab", "GRID", "VERTICAL")
        _FORMATS_ABBREV = ("SQ", "CS", "ta", "g", "v")

        # First, with headers
        if full_format:
            for format_ in _FORMATS:
                cmd_variant = cmd_opts + format_
                comment = "Test case {0} - {1} format".format(
                    starting_case_num, format_)
                res = self.run_test_case(0, cmd_variant, comment)
                starting_case_num += 1
                if not res:
                    raise MUTLibError("{0}: failed".format(comment))

        # Now without headers
        if no_headers:
            for format_ in _FORMATS:
                cmd_variant = cmd_opts + format_ + " --no-headers"
                comment = "Test case {0} - {1} format no headers".format(
                    starting_case_num, format_)
                res = self.run_test_case(0, cmd_variant, comment)
                starting_case_num += 1
                if not res:
                    raise MUTLibError("{0}: failed".format(comment))

        # Now the abbreviations
        if abbrev:
            for format_ in _FORMATS_ABBREV:
                cmd_variant = cmd_opts + format_
                comment = "Test case {0} - {1} format".format(
                    starting_case_num, format_)
                res = self.run_test_case(0, cmd_variant, comment)
                starting_case_num += 1
                if not res:
                    raise MUTLibError("{0}: failed".format(comment))

        # Conduct format and display combination tests

        _DISPLAYS = ("BRIEF", "FULL", "NAMES")
        # SQL format not valid
        _FORMAT_DISPLAY = ("GRID", "CSV", "TAB", "VERTICAL")

        if displays:
            for format_ in _FORMAT_DISPLAY:
                for display in _DISPLAYS:
                    cmd_variant = cmd_opts + "{0} --display={1}".format(
                        format_, display)
                    comment = ("Test case {0} - {1} format with {2} "
                               "display".format(starting_case_num, format_,
                                                display))
                    res = self.run_test_case(0, cmd_variant, comment)
                    starting_case_num += 1
                    if not res:
                        raise MUTLibError("{0}: failed".format(comment))

        # Perform masking for deterministic output

        # Mask version
        self.replace_result(
            "MySQL Utilities mysqldbexport version",
            "MySQL Utilities mysqldbexport version X.Y.Z\n")

        self.replace_result("CREATE EVENT `e1` ON SCHEDULE EVERY 1 YEAR",
                            "CREATE EVENT `e1` ON SCHEDULE EVERY 1 YEAR "
                            "STARTS XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX\n")
        self.replace_result("CREATE DEFINER=`root`@`localhost` EVENT `e1`",
                            "CREATE EVENT `e1` ON SCHEDULE EVERY 1 YEAR "
                            "STARTS XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX\n")

        # Mask known source.
        self.replace_result("# Source on localhost: ... connected.",
                            "# Source on XXXX-XXXX: ... connected.\n")
        self.replace_result("# Source on [::1]: ... connected.",
                            "# Source on XXXX-XXXX: ... connected.\n")

        self.remove_result("# WARNING: The server supports GTIDs")
        self._mask_grid()
        self._mask_csv()
        self._mask_tab()
        self._mask_vertical()

        return True

    def _mask_grid(self):
        """Masks grid.
        """
        self.mask_column_result("| def ", "|", 2, " None           ")
        self.mask_column_result("| None           | util_test       | trg",
                                "|", 2, " None             ")
        self.mask_column_result("| None             | util_test       | trg",
                                "|", 6, " None                  ")
        self.mask_column_result("| None           | util_test     | t", "|",
                                16, " XXXX-XX-XX XX:XX:XX ")
        self.mask_column_result("| None           | util_test     | t", "|",
                                11, " XXXXXXXXXX ")
        self.mask_column_result("| None           | util_test     | t", "|",
                                12, " XXXXXXXXXX ")
        self.mask_column_result("| None           | util_test     | t", "|",
                                14, " XXXXXXXXXX ")
        self.mask_column_result("| None           | util_test     | t", "|",
                                17, " XXXX-XX-XX XX:XX:XX ")
        self.mask_column_result("| None           | util_test "
                                "    | e1          |", "|", 14,
                                " XXXX-XX-XX XX:XX:XX ")
        self.mask_column_result("| util_test  | e1    |", "|", 18,
                                " X           ")
        self.mask_column_result("| util_test  | e1    |", "|", 9,
                                " XXXX-XX-XX XX:XX:XX  ")
        self.mask_column_result("| util_test  | e1    |", "|", 10,
                                " XXXX-XX-XX XX:XX:XX  ")
        self.mask_column_result("| util_test  | e1    |", "|", 12,
                                " XXXX-XX-XX XX:XX:XX  ")
        self.mask_column_result("| e1    | root@localhost  |", "|", 10,
                                " XXXX-XX-XX XX:XX:XX  ")
        self.mask_column_result("| e1    | root@localhost  |", "|", 14,
                                " X           ")
        self.mask_column_result("| util_test  | p1", "|", 14,
                                " XXXX-XX-XX XX:XX:XX  ")
        self.mask_column_result("| util_test  | p1", "|", 15,
                                " XXXX-XX-XX XX:XX:XX  ")
        self.mask_column_result("| util_test  | f1", "|", 14,
                                " XXXX-XX-XX XX:XX:XX  ")
        self.mask_column_result("| util_test  | f1", "|", 15,
                                " XXXX-XX-XX XX:XX:XX  ")
        self.mask_column_result("| util_test  | f2", "|", 14,
                                " XXXX-XX-XX XX:XX:XX  ")
        self.mask_column_result("| util_test  | f2", "|", 15,
                                " XXXX-XX-XX XX:XX:XX  ")
        self.mask_column_result("| util_test  | f2", "|", 15,
                                " XXXX-XX-XX XX:XX:XX  ")
        # Fix MySQL 5.7 output differences
        self.replace_result("+------------------+-----------------+"
                            "---------------+---------------------+",
                            "+------------------+-----------------+"
                            "---------------+---------------------+\n")
        self.replace_result("| None             | util_test       |"
                            "trg           | INSERT",
                            "| None             | util_test       |"
                            "trg           | INSERT\n")
        self.replace_result("| TRIGGER_CATALOG  | TRIGGER_SCHEMA  |"
                            " TRIGGER_NAME  |",
                            "| TRIGGER_CATALOG  | TRIGGER_SCHEMA  |"
                            " TRIGGER_NAME  |\n")

    def _mask_csv(self):
        """Masks CSV.
        """
        self.mask_column_result("`e1`,root@localhost,", ",", 5,
                                "XXXX-XX-XX XX:XX:XX")
        self.mask_column_result("`e1`,root@localhost,", ",", 9,
                                "XXXX-XX-XX XX:XX:XX")
        self.mask_column_result("`e1`,root@localhost,", ",", 10,
                                "XXXX-XX-XX XX:XX:XX")
        self.mask_column_result("`e1`,root@localhost,", ",", 13, "XX")
        self.mask_column_result("def,`util_test`,", ",", 1, "")
        self.mask_column_result(",`util_test`,`trg`", ",", 5, "")
        self.mask_column_result(",`util_test`,`t", ",", 10, "XXXXXXXXXX")
        self.mask_column_result(",`util_test`,`t", ",", 11, "XXXXXXXXXX")
        self.mask_column_result(",`util_test`,`t", ",", 13, "XXXXXXXXXX")
        self.mask_column_result(",`util_test`,`t", ",", 15,
                                "XXXX-XX-XX XX:XX:XX")
        self.mask_column_result(",`util_test`,`t", ",", 16,
                                "XXXX-XX-XX XX:XX:XX")
        self.mask_column_result("`util_test`,`p1`,PROCEDURE", ",", 13,
                                "XXXX-XX-XX XX:XX:XX")
        self.mask_column_result("`util_test`,`p1`,PROCEDURE", ",", 14,
                                "XXXX-XX-XX XX:XX:XX")
        self.mask_column_result("`util_test`,`f1`,FUNCTION", ",", 13,
                                "XXXX-XX-XX XX:XX:XX")
        self.mask_column_result("`util_test`,`f1`,FUNCTION", ",", 14,
                                "XXXX-XX-XX XX:XX:XX")
        self.mask_column_result("`util_test`,`f2`,FUNCTION", ",", 17,
                                "XXXX-XX-XX XX:XX:XX")
        self.mask_column_result("`util_test`,`f2`,FUNCTION", ",", 18,
                                "XXXX-XX-XX XX:XX:XX")
        self.mask_column_result("`util_test`,`e1`", ",", 8,
                                "XXXX-XX-XX XX:XX:XX")
        self.mask_column_result(",`util_test`,`e1`", ",", 17, "XX")
        self.mask_column_result("`util_test`,`e1`", ",", 9,
                                "XXXX-XX-XX XX:XX:XX")
        self.mask_column_result("`util_test`,`e1`", ",", 11,
                                "XXXX-XX-XX XX:XX:XX")
        self.mask_column_result("`util_test`,`e1`", ",", 17, "XX")
        # Mask MySQL 5.7 changes
        self.mask_column_result(",`util_test`,`trg", ",", 8, "X")
        self.mask_column_result(",`util_test`,`trg", ",", 17, "")

    def _mask_tab(self):
        """Masks tab.
        """
        self.mask_column_result("`e1`	root@localhost", "\t", 5,
                                "XXXX-XX-XX XX:XX:XX")
        self.mask_column_result("`e1`	root@localhost", "\t", 9,
                                "XXXX-XX-XX XX:XX:XX")
        self.mask_column_result("`e1`	root@localhost", "\t", 10,
                                "XXXX-XX-XX XX:XX:XX")
        self.mask_column_result("`e1`	root@localhost", "\t", 13, "XX")
        self.mask_column_result("def	`util_test`	`t", "\t", 1, "")
        self.mask_column_result("def	`util_test`	`v", "\t", 1, "")
        self.mask_column_result("	`util_test`	`trg`", "\t", 5, "")
        self.mask_column_result("	`util_test`	`t", "\t", 10, "XXXXXX")
        self.mask_column_result("	`util_test`	`t", "\t", 11, "XXXXXXXX")
        self.mask_column_result("	`util_test`	`t", "\t", 13, "XX")
        self.mask_column_result("	`util_test`	`t", "\t", 15,
                                "XXXX-XX-XX XX:XX:XX")
        self.mask_column_result("	`util_test`	`t", "\t", 16,
                                "XXXX-XX-XX XX:XX:XX")
        self.mask_column_result("`util_test`	`p1`	PROCEDURE", "\t", 13,
                                "XXXX-XX-XX XX:XX:XX")
        self.mask_column_result("`util_test`	`p1`	PROCEDURE", "\t", 14,
                                "XXXX-XX-XX XX:XX:XX")
        self.mask_column_result("`util_test`	`f1`	FUNCTION", "\t", 13,
                                "XXXX-XX-XX XX:XX:XX")
        self.mask_column_result("`util_test`	`f1`	FUNCTION", "\t", 14,
                                "XXXX-XX-XX XX:XX:XX")
        self.mask_column_result("`util_test`	`f2`	FUNCTION", "\t", 13,
                                "XXXX-XX-XX XX:XX:XX")
        self.mask_column_result("`util_test`	`f2`	FUNCTION", "\t", 14,
                                "XXXX-XX-XX XX:XX:XX")
        self.mask_column_result("`util_test`	`e1`", "\t", 8,
                                "XXXX-XX-XX XX:XX:XX")
        self.mask_column_result("`util_test`	`e1`", "\t", 17, "XX")
        self.mask_column_result("`util_test`	`e1`", "\t", 9,
                                "XXXX-XX-XX XX:XX:XX")
        self.mask_column_result("`util_test`	`e1`", "\t", 11,
                                "XXXX-XX-XX XX:XX:XX")
        # Mask MySQL 5.7 changes
        self.mask_column_result("	`util_test`	`trg", "\t", 17,
                                "XXXX-XX-XX XX:XX:XX")

    def _mask_vertical(self):
        """Masks vertical.
        """
        self.replace_result("                   UPDATE_TIME:",
                            "                   UPDATE_TIME: "
                            "XXXX-XX-XX XX:XX:XX\n")
        self.replace_result("                   CREATE_TIME:",
                            "                   CREATE_TIME: "
                            "XXXX-XX-XX XX:XX:XX\n")
        self.replace_result("              UPDATE_TIME:",
                            "              UPDATE_TIME: "
                            "XXXX-XX-XX XX:XX:XX\n")
        self.replace_result("              CREATE_TIME:",
                            "              CREATE_TIME: "
                            "XXXX-XX-XX XX:XX:XX\n")

        self.replace_result("              CREATED:",
                            "              CREATED: XXXX-XX-XX XX:XX:XX\n")
        self.replace_result("              created:",
                            "              CREATED: XXXX-XX-XX XX:XX:XX\n")
        self.replace_result("             MODIFIED:",
                            "             MODIFIED: XXXX-XX-XX XX:XX:XX\n")
        self.replace_result("             modified:",
                            "             MODIFIED: XXXX-XX-XX XX:XX:XX\n")
        self.replace_result("         LAST_ALTERED:",
                            "         LAST_ALTERED: XXXX-XX-XX XX:XX:XX\n")
        self.replace_result("               STARTS:",
                            "               STARTS: XXXX-XX-XX XX:XX:XX\n")
        self.replace_result("               starts:",
                            "               STARTS: XXXX-XX-XX XX:XX:XX\n")
        self.replace_result("                 ENDS:",
                            "                 ENDS: XXXX-XX-XX XX:XX:XX\n")
        self.replace_result("                 ends:",
                            "                 ENDS: XXXX-XX-XX XX:XX:XX\n")
        self.replace_result("           ORIGINATOR:",
                            "           ORIGINATOR: XX\n")
        self.replace_result("           originator:",
                            "           ORIGINATOR: XX\n")

        self.replace_result("                   DATA_LENGTH:",
                            "                   DATA_LENGTH: XXXXXXX\n")
        self.replace_result("                  INDEX_LENGTH:",
                            "                  INDEX_LENGTH: XXXXXXX\n")
        self.replace_result("               MAX_DATA_LENGTH:",
                            "               MAX_DATA_LENGTH: XXXXXXX\n")
        self.replace_result("                     DATA_FREE:",
                            "                     DATA_FREE: XXXXXXXXXXX\n")

        self.replace_result("           AVG_ROW_LENGTH:",
                            "           AVG_ROW_LENGTH: XXXXXXX\n")
        self.replace_result("              DATA_LENGTH:",
                            "              DATA_LENGTH: XXXXXXX\n")
        self.replace_result("             INDEX_LENGTH:",
                            "             INDEX_LENGTH: XXXXXXX\n")
        self.replace_result("          MAX_DATA_LENGTH:",
                            "          MAX_DATA_LENGTH: XXXXXXX\n")
        self.replace_result("                DATA_FREE:",
                            "                DATA_FREE: XXXXXXXXXXX\n")
        self.replace_result("            TABLE_CATALOG: def",
                            "            TABLE_CATALOG: None\n")
        self.replace_result("        TABLE_CATALOG: def",
                            "        TABLE_CATALOG: None\n")
        self.replace_result("            TRIGGER_CATALOG: def",
                            "            TRIGGER_CATALOG: None\n")
        self.replace_result("       EVENT_OBJECT_CATALOG: def",
                            "       EVENT_OBJECT_CATALOG: None\n")
        # Mask MySQL 5.7 changes
        self.replace_result("               ACTION_ORDER:",
                            "               ACTION_ORDER: X\n")
        self.replace_result("                    CREATED:",
                            "                    CREATED: "
                            "XXXX-XX-XX XX:XX:XX\n")

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        return export_basic.test.cleanup(self)
