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
export_parameters_data test.
"""

import export_parameters_def

from mysql.utilities.exception import MUTLibError, UtilError


class test(export_parameters_def.test):
    """check parameters for export utility
    This test executes a series of export database operations on a single
    server using a variety of parameters. It uses the export_parameters_def
    test as a parent for setup and teardown methods.
    """

    def check_prerequisites(self):
        return export_parameters_def.test.check_prerequisites(self)

    def setup(self):
        res = export_parameters_def.test.setup(self)
        if not res:
            return False

        try:
            self.server1.exec_query("ALTER TABLE util_test.t2 ADD COLUMN "
                                    " x_blob blob")
        except UtilError as err:
            raise MUTLibError("Cannot alter table:{0}".format(err.errmsg))

        try:
            self.server1.exec_query("UPDATE util_test.t2 SET x_blob = "
                                    "'This is a blob.' ")

        except UtilError as err:
            raise MUTLibError("Cannot update rows: {0}".format(err.errmsg))

        return True

    def run(self):
        self.res_fname = "result.txt"

        from_conn = "--server={0}".format(
            self.build_connection_string(self.server1))

        test_num = 1
        cmd_str = "mysqldbexport.py --skip-gtid {0} ".format(from_conn)

        cmd_opts = "{0} util_test --format=SQL --export=data".format(cmd_str)
        comment = "Test case {0} - SQL single rows".format(test_num)
        res = self.run_test_case(0, cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = "Test case {0} - SQL bulk insert".format(test_num)
        res = self.run_test_case(0, cmd_opts + " --bulk-insert", comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = "Test case {0} - skip blobs".format(test_num)
        res = self.run_test_case(0, cmd_opts + " --skip-blobs", comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Conduct format and display combination tests
        # Note: should say it is ignored for --export=data output.

        func = export_parameters_def.test.test_format_and_display_values
        func(self, "{0} util_test --export=data --format=".format(cmd_str), 4)

        self.server1.exec_query("ALTER TABLE util_test.t2 ADD COLUMN "
                                " y_blob blob")
        self.server1.exec_query("UPDATE util_test.t2 SET y_blob = "
                                "'This is yet another blob.' ")

        test_num = 31
        comment = "Test case {0} - multiple blobs".format(test_num)
        res = self.run_test_case(0, cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        ## Mask known source.
        self.replace_result("# Source on localhost: ... connected.",
                            "# Source on XXXX-XXXX: ... connected.\n")
        self.replace_result("# Source on [::1]: ... connected.",
                            "# Source on XXXX-XXXX: ... connected.\n")
        # Mask GTID warning when servers with GTID enabled are used
        self.remove_result("# WARNING: The server supports GTIDs but you")

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        return export_parameters_def.test.cleanup(self)
