#
# Copyright (c) 2015, Oracle and/or its affiliates. All rights reserved.
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
clone_server_parameters_old test.
"""

import clone_server_parameters
from mysql.utilities.exception import MUTLibError


class test(clone_server_parameters.test):
    """Audit log maintenance utility tests for older server versions.

    This test runs the serverclone utility to test its features for older
    MySQL server versions. Requires a server version between 5.6.0 and 5.7.5
    inclusive.
    """

    def check_prerequisites(self):
        # Check if server version is compatible
        has_server = self.check_num_servers(1)
        srv = self.servers.get_server(0)
        if (not srv.check_version_compat(5, 6, 0) or  # <=5.6.0
                srv.check_version_compat(5, 7, 6)):  # >= 5.7.6
            raise MUTLibError("Test requires server version between 5.6.0 and "
                              "5.7.5 inclusive.")
        return has_server

    def run(self):
        """Run test cases.
        """
        # Run all test cases from the parent class clone_server_parameters
        ran_ok = super(test, self).run()
        if ran_ok:
            # Replace lines that appear only on older MySQL versions
            self.replace_result(
                "#      mysql_system_tables.sql:",
                "#      mysql_system_tables.sql: XXXXXXXXXXXX\n"
            )
            self.replace_result(
                "# mysql_system_tables_data.sql:",
                "# mysql_system_tables_data.sql: XXXXXXXXXXXX\n"
            )
            self.replace_result(
                "# mysql_test_data_timezone.sql:",
                "# mysql_test_data_timezone.sql: XXXXXXXXXXXX\n"
            )
            self.replace_result(
                "#         fill_help_tables.sql:",
                "#         fill_help_tables.sql: XXXXXXXXXXXX\n"
            )
        return ran_ok

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)
