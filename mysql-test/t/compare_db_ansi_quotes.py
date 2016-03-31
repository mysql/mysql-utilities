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
compare_db test.
"""

import os

import mutlib
import compare_db

from mysql.utilities.exception import MUTLibError


_DEFAULT_MYSQL_OPTS = ('"--log-bin=mysql-bin --skip-slave-start '
                       '--log-slave-updates --gtid-mode=on '
                       '--enforce-gtid-consistency --report-host=localhost'
                       '--report-port={0} --bind-address=:: '
                       '--master-info-repository=table '
                       '--sql-mode=ANSI_QUOTES"')


class test(compare_db.test):
    """simple db diff
    This test executes a consistency check of two databases on
    separate servers.
    """

    server1 = None
    server2 = None
    need_server = False

    def setup(self):
        self.server0 = self.servers.get_server(0)
        mysqld = _DEFAULT_MYSQL_OPTS.format(self.servers.view_next_port())
        self.server1 = self.servers.spawn_server("compare_db_srv1_ansi_quotes",
                                                 mysqld, True)
        mysqld = _DEFAULT_MYSQL_OPTS.format(self.servers.view_next_port())
        self.server2 = self.servers.spawn_server("compare_db_srv2_ansi_quotes",
                                                 mysqld, True)

        self.data_files = [
            os.path.normpath("./std_data/db_compare_test.sql"),
            os.path.normpath("./std_data/db_compare_backtick_ansi_quotes.sql"),
            os.path.normpath("./std_data/db_compare_use_indexes.sql"),
            os.path.normpath("./std_data/db_compare_pkeys.sql"),
            os.path.normpath("./std_data/db_compare_quotes.sql"),
        ]
        compare_db.test.setup(self, spawn_servers=False)

        if self.server1.select_variable("SQL_MODE") != "ANSI_QUOTES":
            raise MUTLibError("Failed to set SQL_MODE=ANSI_QUOTES to server"
                              " {0}:{1}".format(self.server1.host,
                                                self.server1.port))

        if self.server2.select_variable("SQL_MODE") != "ANSI_QUOTES":
            raise MUTLibError("Failed to set SQL_MODE=ANSI_QUOTES to server"
                              " {0}:{1}".format(self.server2.host,
                                                self.server2.port))
        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        # Kill the servers that are only for this test.
        kill_list = ["compare_db_srv1_ansi_quotes",
                     "compare_db_srv2_ansi_quotes"]
        compare_db.test.cleanup(self)
        return self.kill_server_list(kill_list)
