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
binlog_purge test.
"""

import mutlib
from binlog_rotate import binlog_file_exists

from mysql.utilities.exception import MUTLibError
from mysql.utilities.common.user import change_user_privileges


class test(mutlib.System_test):
    """Tests the purge binlog utility
    This test executes the purge binlog utility on a single server.
    """

    server2 = None
    server2_datadir = None
    server3 = None
    mask_ports = []

    def check_prerequisites(self):
        # Need at least one server.
        return self.check_num_servers(1)

    def setup(self):
        next_port = self.servers.view_next_port()
        self.mask_ports.append(next_port)
        mysqld = ("--log-bin=mysql-bin --report-port={0}").format(next_port)
        self.server2 = self.servers.spawn_server(
            "server2_binlog_purge", mysqld, True)

        next_port = self.servers.view_next_port()
        self.mask_ports.append(next_port)
        mysqld = ("--report-port={0}").format(next_port)
        self.server3 = self.servers.spawn_server(
            "server3_binlog_purge", mysqld, True)

        # Get datadir
        rows = self.server2.exec_query("SHOW VARIABLES LIKE 'datadir'")
        if not rows:
            raise MUTLibError("Unable to determine datadir of cloned server "
                              "at {0}:{1}".format(self.server2.host,
                                                  self.server2.port))
        self.server2_datadir = rows[0][1]

        # Create user without No privileges.
        if self.debug:
            print("\nCreating user without any privileges on server...")
        change_user_privileges(self.server2, 'an_user', 'a_pwd',
                               self.server2.host, grant_list=None,
                               revoke_list=None, disable_binlog=True,
                               create_user=True)

        return True

    def run(self):
        self.res_fname = "result.txt"
        server_conn = "--server={0}".format(
            self.build_connection_string(self.server2))

        master_conn = "--master={0}".format(
            self.build_connection_string(self.server2))

        self.res_fname = "result.txt"
        server_conn3 = "--server={0}".format(
            self.build_connection_string(self.server3))

        master_conn3 = "--master={0}".format(
            self.build_connection_string(self.server3))

        cmd_str = "mysqlbinlogpurge.py {0}"

        test_num = 1
        comment = ("Test case {0} - No options"
                   "".format(test_num))
        cmd = "mysqlbinlogpurge.py"
        res = self.run_test_case(2, cmd, comment)
        if not res or not binlog_file_exists(self.server2_datadir,
                                             "mysql-bin.000001", self.debug):
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - Master no Slave options"
                   "".format(test_num))
        cmd = cmd_str.format(master_conn)
        res = self.run_test_case(2, cmd, comment)
        if not res or not binlog_file_exists(self.server2_datadir,
                                             "mysql-bin.000001", self.debug):
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - Server with Slave option"
                   "".format(test_num))
        cmd = "{0} --slave={1}".format(
            cmd_str.format(server_conn),
            self.build_connection_string(self.server2)
        )
        res = self.run_test_case(2, cmd, comment)
        if not res or not binlog_file_exists(self.server2_datadir,
                                             "mysql-bin.000001", self.debug):
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - Server without binlog"
                   "".format(test_num))
        cmd = "{0} ".format(
            cmd_str.format(server_conn3),
            self.build_connection_string(self.server2)
        )
        res = self.run_test_case(1, cmd, comment)
        if not res or not binlog_file_exists(self.server2_datadir,
                                             "mysql-bin.000001", self.debug):
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - Master with wrong Slave"
                   "".format(test_num))
        cmd = "{0} --slave={1}".format(
            cmd_str.format(master_conn3),
            self.build_connection_string(self.server2)
        )
        res = self.run_test_case(1, cmd, comment)
        if not res or not binlog_file_exists(self.server2_datadir,
                                             "mysql-bin.000001", self.debug):
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - Server with Discover option"
                   "".format(test_num))
        cmd = "{0} --discover={1}".format(
            cmd_str.format(server_conn),
            "root:rootpass"
        )
        res = self.run_test_case(2, cmd, comment)
        if not res or not binlog_file_exists(self.server2_datadir,
                                             "mysql-bin.000001", self.debug):
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - Only discover option"
                   "".format(test_num))
        cmd = "mysqlbinlogpurge.py --discover={0}".format("root:rootpass")
        res = self.run_test_case(2, cmd, comment)
        if not res or not binlog_file_exists(self.server2_datadir,
                                             "mysql-bin.000001", self.debug):
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - Only slaves option"
                   "".format(test_num))
        cmd = "mysqlbinlogpurge.py --slaves={0}".format(server_conn)
        res = self.run_test_case(2, cmd, comment)
        if not res or not binlog_file_exists(self.server2_datadir,
                                             "mysql-bin.000001", self.debug):
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - Only dry-run and verbose options"
                   "".format(test_num))
        cmd = "{0} -vv -d".format("mysqlbinlogpurge.py")
        res = self.run_test_case(2, cmd, comment)
        if not res or not binlog_file_exists(self.server2_datadir,
                                             "mysql-bin.000001", self.debug):
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - wrong binlog base name"
                   "".format(test_num))
        cmd = "{0} --binlog={1}".format(cmd_str.format(server_conn),
                                        "wrong_binlog_name.00002")
        res = self.run_test_case(1, cmd, comment)
        if not res or not binlog_file_exists(self.server2_datadir,
                                             "mysql-bin.000001", self.debug):
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - server and master options mixed"
                   "".format(test_num))
        cmd = "{0} {1}".format(cmd_str.format(server_conn), master_conn)
        res = self.run_test_case(2, cmd, comment)
        if not res or not binlog_file_exists(self.server2_datadir,
                                             "mysql-bin.000001", self.debug):
            raise MUTLibError("{0}: failed".format(comment))

        # Mask results
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
        kill_list = ['server2_binlog_purge',
                     'server3_binlog_purge']
        return self.kill_server_list(kill_list)
