#
# Copyright (c) 2016, Oracle and/or its affiliates. All rights reserved.
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
compare_db_errors test.
"""

import compare_db_errors

from mysql.utilities.exception import MUTLibError


_DEFAULT_MYSQL_OPTS = ('"--log-bin=mysql-bin --report-host=localhost'
                       '--report-port={0} {1}"')


class test(compare_db_errors.test):
    """check errors for dbcompare
    This test executes a series of error conditions for the check database
    utility. It uses the compare_db test as a parent for setup and teardown
    methods. This test uses a server with sql_mode set to ANSI_QUOTES and other
    with a different mode.
    """

    server1 = None
    server2 = None

    def setup(self, spawn_servers=True):
        mysqld = _DEFAULT_MYSQL_OPTS.format(self.servers.view_next_port(), "")
        self.server1 = self.servers.spawn_server("compare_db_srv1_aq_mix",
                                                 mysqld, True)

        if self.server1.select_variable("SQL_MODE") == "ANSI_QUOTES":
            raise MUTLibError("This Test needs a server with SQL_MODE != "
                              "ANSI_QUOTES {0}:{1}".format(self.server2.host,
                                                           self.server2.port))
        mysqld = _DEFAULT_MYSQL_OPTS.format(self.servers.view_next_port(),
                                            "--sql-mode=ANSI_QUOTES")
        self.server2 = self.servers.spawn_server("compare_db_srv2_aq_mix",
                                                 mysqld, True)

        if self.server2.select_variable("SQL_MODE") != "ANSI_QUOTES":
            raise MUTLibError("Failed to set SQL_MODE!=ANSI_QUOTES to server"
                              " {0}:{1}".format(self.server2.host,
                                                self.server2.port))
        self.drop_all()
        return True

    def run(self):
        # Run compare_db_errors with first server with sql_mode == ANSI_QUOTES
        # but second with default sql_mode.
        part1 = compare_db_errors.test.run(self)
        compare_db_errors.test.cleanup(self)
        # Change the Order of the servers and run compare_db_errors again.
        self.server1, self.server2 = self.server2, self.server1
        part2 = compare_db_errors.test.run(self)
        return part1 and part2

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        # Kill the servers that are only for this test.
        kill_list = ["compare_db_srv1_aq_mix",
                     "compare_db_srv2_aq_mix"]
        return self.kill_server_list(kill_list)
