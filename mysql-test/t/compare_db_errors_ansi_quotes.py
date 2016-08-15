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


_DEFAULT_MYSQL_OPTS = ('"--log-bin=mysql-bin --skip-slave-start '
                       '--log-slave-updates --gtid-mode=on '
                       '--enforce-gtid-consistency --report-host=localhost'
                       '--report-port={0} --bind-address=:: '
                       '--master-info-repository=table '
                       '--sql-mode=ANSI_QUOTES"')


class test(compare_db_errors.test):
    """check errors for dbcompare
    This test executes a series of error conditions for the check database
    utility. It uses the compare_db test as a parent for setup and teardown
    methods.
    """

    server1 = None
    server2 = None

    def setup(self):
        self.server0 = self.servers.get_server(0)
        mysqld = _DEFAULT_MYSQL_OPTS.format(self.servers.view_next_port())
        self.server1 = self.servers.spawn_server("compare_db_srv1_ansi_quotes",
                                                 mysqld, True)
        mysqld = _DEFAULT_MYSQL_OPTS.format(self.servers.view_next_port())
        self.server2 = self.servers.spawn_server("compare_db_srv2_ansi_quotes",
                                                 mysqld, True)

        if self.server1.select_variable("SQL_MODE") != "ANSI_QUOTES":
            raise MUTLibError("Failed to set SQL_MODE=ANSI_QUOTES to server"
                              " {0}:{1}".format(self.server1.host,
                                                self.server1.port))

        if self.server2.select_variable("SQL_MODE") != "ANSI_QUOTES":
            raise MUTLibError("Failed to set SQL_MODE=ANSI_QUOTES to server"
                              " {0}:{1}".format(self.server2.host,
                                                self.server2.port))
        self.drop_all()
        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        # Kill the servers that are only for this test.
        kill_list = ["compare_db_srv1_ansi_quotes",
                     "compare_db_srv2_ansi_quotes"]
        return (compare_db_errors.test.cleanup(self) and
                self.kill_server_list(kill_list))
