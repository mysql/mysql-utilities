#
# Copyright (c) 2014, Oracle and/or its affiliates. All rights reserved.
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
binlog_rotate errors test.
"""

import mutlib
from binlog_rotate import binlog_file_exists

from mysql.utilities.common.user import change_user_privileges
from mysql.utilities.exception import MUTLibError


class test(mutlib.System_test):
    """Tests the rotate binlog utility
    This test executes the rotate binlog utility error messages.
    """

    server1 = None
    server1_datadir = None
    server2 = None
    mask_ports = []

    def check_prerequisites(self):
        # Need at least one server.
        return self.check_num_servers(1)

    def setup(self):
        mysqld = ("--log-bin=mysql-bin --report-port={0}"
                  ).format(self.servers.view_next_port())
        self.server1 = self.servers.spawn_server(
            "server1_binlog_rotate", mysqld, True)

        # Get datadir
        rows = self.server1.exec_query("SHOW VARIABLES LIKE 'datadir'")
        if not rows:
            raise MUTLibError("Unable to determine datadir of cloned server "
                              "at {0}:{1}".format(self.server1.host,
                                                  self.server1.port))
        self.server1_datadir = rows[0][1]

        # Server not using binlog
        mysqld = ("--report-port={0}"
                  ).format(self.servers.view_next_port())
        self.server2 = self.servers.spawn_server(
            "server2_binlog_rotate", mysqld, True)

        self.mask_ports.append(self.server1.port)
        self.mask_ports.append(self.server2.port)

        return True

    def run(self):
        self.res_fname = "result.txt"
        from_conn = "--server={0}".format(
            self.build_connection_string(self.server1)
        )

        server2_conn = "--server={0}".format(
            self.build_connection_string(self.server2)
        )

        cmd_str = "mysqlbinlogrotate.py "

        test_num = 1
        comment = ("Test case {0} - no options"
                   "".format(test_num))
        cmd = "{0}".format(cmd_str)
        res = self.run_test_case(2, cmd, comment)
        if not res or not binlog_file_exists(self.server1_datadir,
                                             "mysql-bin.000001", self.debug):
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - server has no binlog"
                   "".format(test_num))
        cmd = "{0} {1}".format(cmd_str, server2_conn)
        res = self.run_test_case(1, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - rotate bad value min_size option"
                   "".format(test_num))
        cmd = "{0} {1} --min-size={2}".format(cmd_str, from_conn, "A100")
        res = self.run_test_case(2, cmd, comment)
        if not res or not binlog_file_exists(self.server1_datadir,
                                             "mysql-bin.000001", self.debug):
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - rotate high value min_size option"
                   "".format(test_num))
        cmd = "{0} {1} --min-size={2}".format(cmd_str, from_conn, "10000")
        res = self.run_test_case(0, cmd, comment)
        if not res or not binlog_file_exists(self.server1_datadir,
                                             "mysql-bin.000001", self.debug):
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - rotate on server without binlog and "
                   "option (-vv)".format(test_num))
        cmd = "{0} -vv {1}".format(cmd_str, server2_conn)
        res = self.run_test_case(1, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Mask results
        self.replace_substring_portion(
            "because it's size", "is lower than the minimum",
            "because it's size XXX is lower than the minimum"
        )
        self.replace_substring_portion(
            "ERROR:", " You are not using binary log",
            "ERROR: You are not using binary log"
        )

        self.replace_substring("localhost", "XXXX-XXXX")
        p_n = 0
        for port in self.mask_ports:
            p_n += 1
            self.replace_substring(repr(port), "PORT{0}".format(p_n))

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        # Kill the servers that are only for this test.
        kill_list = ['server1_binlog_rotate',
                     'server2_binlog_rotate']
        return self.kill_server_list(kill_list)
