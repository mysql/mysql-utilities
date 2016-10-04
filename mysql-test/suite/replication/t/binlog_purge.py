#
# Copyright (c) 2014, 2016, Oracle and/or its affiliates. All rights reserved.
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
binlog_purge test.
"""

import mutlib
from binlog_rotate import binlog_file_exists

from mysql.utilities.exception import MUTLibError


class test(mutlib.System_test):
    """Tests the purge binlog utility
    This test executes the purge binlog utility on a single server.
    """

    server1 = None
    server1_datadir = None
    need_server = False

    def check_prerequisites(self):
        # Need at least one server.
        if not self.check_num_servers(2):
            self.need_server = True
        return self.check_num_servers(1)

    def setup(self):
        mysqld = (
            "--log-bin=mysql-bin --report-port={0}"
        ).format(self.servers.view_next_port())
        self.server1 = self.servers.spawn_server(
            "server_binlog_purge", mysqld, True)

        # Get datadir
        rows = self.server1.exec_query("SHOW VARIABLES LIKE 'datadir'")
        if not rows:
            raise MUTLibError("Unable to determine datadir of cloned server "
                              "at {0}:{1}".format(self.server1.host,
                                                  self.server1.port))
        self.server1_datadir = rows[0][1]

        # Flush server binary log
        self.server1.exec_query("FLUSH LOGS")

        return True

    def run(self):
        self.res_fname = "result.txt"
        from_conn = "--server={0}".format(
            self.build_connection_string(self.server1))

        cmd_str = "mysqlbinlogpurge.py {0}".format(from_conn)

        test_num = 1
        comment = ("Test case {0} - simple purge"
                   "".format(test_num))
        cmd = "{0}".format(cmd_str)
        res = self.run_test_case(0, cmd, comment)
        if not res or binlog_file_exists(self.server1_datadir,
                                         "mysql-bin.000001", self.debug):
            raise MUTLibError("{0}: failed".format(comment))

        # Flush master binary log to have some logs to purge
        self.server1.exec_query("FLUSH LOGS")

        test_num += 1
        comment = ("Test case {0} - purge using verbose (-v)"
                   "".format(test_num))
        cmd = "{0} -v ".format(cmd_str)
        res = self.run_test_case(0, cmd, comment)
        if not res or binlog_file_exists(self.server1_datadir,
                                         "mysql-bin.000002", self.debug):
            raise MUTLibError("{0}: failed".format(comment))

        # Mask known source host name.
        self.replace_result("# Source on ",
                            "# Source on XXXX-XXXX: ... connected.\n")

        # Mask version
        self.replace_result(
            "MySQL Utilities mysqlbinlogpurge version",
            "MySQL Utilities mysqlbinlogpurge version X.Y.Z "
            "(part of MySQL Workbench ... XXXXXX)\n"
        )

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        # Kill the servers that are only for this test.
        kill_list = ['server_binlog_purge']
        return self.kill_server_list(kill_list)
