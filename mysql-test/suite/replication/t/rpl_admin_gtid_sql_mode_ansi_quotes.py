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
rpl_admin_gtid_sql_mode_ansi_quotes test.
"""

import rpl_admin_gtid_loopback

from mysql.utilities.exception import MUTLibError


_IPv4_LOOPBACK = "127.0.0.1"

_DEFAULT_MYSQL_OPTS = ('"--log-bin=mysql-bin --skip-slave-start '
                       '--log-slave-updates --gtid-mode=on '
                       '--enforce-gtid-consistency --report-host={0} '
                       '--report-port={1} --bind-address=:: '
                       '--master-info-repository=table '
                       '--sql-mode=ANSI_QUOTES"')


class test(rpl_admin_gtid_loopback.test):
    """test replication administration commands
    This test runs the mysqlrpladmin utility on a known topology with
    all servers using sql_mode=ANSI_QUOTES.

    Note: this test requires GTID enabled servers.
    """

    old_cloning_host = None

    def check_prerequisites(self):
        if not self.servers.get_server(0).check_version_compat(5, 6, 9):
            raise MUTLibError("Test requires server version 5.6.9")
        return self.check_num_servers(1)

    def setup(self):
        self.res_fname = "result.txt"

        # Spawn servers
        # Change cloning Server_List host value
        self.old_cloning_host = self.servers.cloning_host
        self.servers.cloning_host = _IPv4_LOOPBACK

        self.server0 = self.servers.get_server(0)
        mysqld = _DEFAULT_MYSQL_OPTS.format(_IPv4_LOOPBACK,
                                            self.servers.view_next_port())
        self.server1 = self.servers.spawn_server("rep_master_gtid_ansiquotes",
                                                 mysqld, True)
        mysqld = _DEFAULT_MYSQL_OPTS.format(_IPv4_LOOPBACK,
                                            self.servers.view_next_port())
        self.server2 = self.servers.spawn_server("rep_slave1_gtid_ansiquotes",
                                                 mysqld, True)
        mysqld = _DEFAULT_MYSQL_OPTS.format(_IPv4_LOOPBACK,
                                            self.servers.view_next_port())
        self.server3 = self.servers.spawn_server("rep_slave2_gtid_ansiquotes",
                                                 mysqld, True)
        mysqld = _DEFAULT_MYSQL_OPTS.format(_IPv4_LOOPBACK,
                                            self.servers.view_next_port())
        self.server4 = self.servers.spawn_server("rep_slave3_gtid_ansiquotes",
                                                 mysqld, True)

        # Reset spawned servers (clear binary log and GTID_EXECUTED set)
        self.reset_master()

        self.m_port = self.server1.port
        self.s1_port = self.server2.port
        self.s2_port = self.server3.port
        self.s3_port = self.server4.port

        rpl_admin_gtid_loopback.test.reset_topology(self)

        if self.server1.select_variable("SQL_MODE") != "ANSI_QUOTES":
            raise MUTLibError("Failed to set SQL_MODE=ANSI_QUOTES to server"
                              " {0}:{1}".format(self.server1.host,
                                                self.server1.port))
        if self.server2.select_variable("SQL_MODE") != "ANSI_QUOTES":
            raise MUTLibError("Failed to set SQL_MODE=ANSI_QUOTES to server"
                              " {0}:{1}".format(self.server2.host,
                                                self.server2.port))
        if self.server3.select_variable("SQL_MODE") != "ANSI_QUOTES":
            raise MUTLibError("Failed to set SQL_MODE=ANSI_QUOTES to server"
                              " {0}:{1}".format(self.server3.host,
                                                self.server3.port))
        if self.server4.select_variable("SQL_MODE") != "ANSI_QUOTES":
            raise MUTLibError("Failed to set SQL_MODE=ANSI_QUOTES to server"
                              " {0}:{1}".format(self.server4.host,
                                                self.server4.port))

        return True

    def run(self):
        rpl_admin_gtid_loopback.test.run(self)

        self.results.append("\n")
        self.results.append(
            "For server {0}:{1} SQL_MODE is {2}\n"
            "".format(self.server1.host, self.server1.port,
                      self.server1.select_variable("SQL_MODE")))
        self.results.append(
            "For server {0}:{1} SQL_MODE is {2}\n"
            "".format(self.server2.host, self.server2.port,
                      self.server2.select_variable("SQL_MODE")))
        self.results.append(
            "For server {0}:{1} SQL_MODE is {2}\n"
            "".format(self.server3.host, self.server3.port,
                      self.server3.select_variable("SQL_MODE")))
        self.results.append(
            "For server {0}:{1} SQL_MODE is {2}\n"
            "".format(self.server4.host, self.server4.port,
                      self.server4.select_variable("SQL_MODE")))

        # Mask out non-deterministic data
        rpl_admin_gtid_loopback.test.do_masks(self)

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        # Restoring cloning Server_List host value
        self.servers.cloning_host = self.old_cloning_host
        # Kill the servers that are only for this test.
        kill_list = ['rep_master_gtid_ansiquotes',
                     'rep_slave1_gtid_ansiquotes',
                     'rep_slave2_gtid_ansiquotes',
                     'rep_slave3_gtid_ansiquotes']
        rpl_admin_gtid_loopback.test.cleanup(self)
        return (self.kill_server_list(kill_list))
