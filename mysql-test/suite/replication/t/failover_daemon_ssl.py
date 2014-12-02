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
failover_daemon test with ssl.
"""

import os

import failover_daemon
import rpl_admin
from mutlib.ssl_certs import (ssl_pass, ssl_user, ssl_util_opts, ssl_c_ca,
                              ssl_c_cert, ssl_c_key, SSL_OPTS)

from mysql.utilities.common.server import Server
from mysql.utilities.common.user import grant_proxy_ssl_privileges
from mysql.utilities.exception import MUTLibError, UtilError


_FAILOVER_LOG = "{0}fail_log.txt"
_FAILOVER_PID = "{0}fail_pid.txt"
_FAILOVER_COMPLETE = "Failover complete"
_TIMEOUT = 30

_DEFAULT_MYSQL_OPTS = ('"--log-bin=mysql-bin --skip-slave-start '
                       '--log-slave-updates --gtid-mode=on '
                       '--enforce-gtid-consistency --report-host=localhost '
                       '--report-port={port} '
                       '--sync-master-info=1 --master-info-repository=table '
                       '{ssl}"').format(port='{port}', ssl=SSL_OPTS)

_DEFAULT_MYSQL_OPTS_FILE = ('"--log-bin=mysql-bin --skip-slave-start '
                            '--log-slave-updates --gtid-mode=on '
                            '--enforce-gtid-consistency '
                            '--report-host=localhost --report-port={port} '
                            '--sync-master-info=1 '
                            '--master-info-repository=file '
                            '{ssl}"').format(port='{port}', ssl=SSL_OPTS)

_MYSQL_OPTS_INFO_REPO_TABLE = ('"--log-bin=mysql-bin --skip-slave-start '
                               '--log-slave-updates --gtid-mode=ON '
                               '--enforce-gtid-consistency '
                               '--report-host=localhost --report-port={port} '
                               '--sync-master-info=1 '
                               '--master-info-repository=TABLE '
                               '--relay-log-info-repository=TABLE '
                               '{ssl}"').format(port='{port}', ssl=SSL_OPTS)


class test(failover_daemon.test):
    """Test replication failover daemon with ssl

    This test exercises the mysqlfailover utility failover event and modes.
    It uses the rpl_admin_gtid test for setup and teardown methods.
    """

    log_range = range(1, 6)

    def setup(self):
        self.res_fname = "result.txt"
        self.temp_files = []
        # Post failover script executed to detect failover events (by creating
        # a specific directory).
        if os.name == 'posix':
            self.fail_event_script = os.path.normpath("./std_data/"
                                                      "fail_event.sh")
        else:
            self.fail_event_script = os.path.normpath("./std_data/"
                                                      "fail_event.bat")

        # Directory created by the post failover script.
        self.failover_dir = os.path.normpath("./fail_event")

        # Remove log files (leftover from previous test).
        for log in self.log_range:
            try:
                os.unlink(_FAILOVER_LOG.format(log))
            except OSError:
                pass

        # Spawn servers
        self.server0 = self.servers.get_server(0)
        mysqld = _DEFAULT_MYSQL_OPTS.format(port=self.servers.view_next_port())
        self.server1 = self.servers.spawn_server("rep_master_gtid", mysqld,
                                                 True)
        mysqld = _DEFAULT_MYSQL_OPTS.format(port=self.servers.view_next_port())
        self.server2 = self.servers.spawn_server("rep_slave1_gtid", mysqld,
                                                 True)
        mysqld = _DEFAULT_MYSQL_OPTS.format(port=self.servers.view_next_port())
        self.server3 = self.servers.spawn_server("rep_slave2_gtid", mysqld,
                                                 True)
        # Spawn server with --master-info-repository=TABLE and
        # --relay-log-info-repository=TABLE.
        mysqld = _MYSQL_OPTS_INFO_REPO_TABLE.format(
            port=self.servers.view_next_port()
        )
        self.server4 = self.servers.spawn_server("rep_slave3_gtid", mysqld,
                                                 True)
        # Spawn a server with MIR=FILE
        mysqld = _DEFAULT_MYSQL_OPTS_FILE.format(
            port=self.servers.view_next_port()
        )
        self.server5 = self.servers.spawn_server("rep_slave4_gtid", mysqld,
                                                 True)

        self.m_port = self.server1.port
        self.s1_port = self.server2.port
        self.s2_port = self.server3.port
        self.s3_port = self.server4.port
        self.s4_port = self.server5.port

        servers = [self.server1, self.server2, self.server3,
                   self.server4, self.server5]
        for server in servers:
            try:
                grant_proxy_ssl_privileges(server, ssl_user, ssl_pass)
            except UtilError as err:
                raise MUTLibError("{0} on:{1}".format(err.errmsg,
                                                      server.role))
        conn_info = {
            'user': ssl_user,
            'passwd': ssl_pass,
            'host': self.server0.host,
            'port': self.server0.port,
            'ssl_ca': ssl_c_ca,
            'ssl_cert': ssl_c_cert,
            'ssl_key': ssl_c_key,
        }

        conn_info['port'] = self.server1.port
        conn_info['port'] = self.server1.port
        self.server1 = Server.fromServer(self.server1, conn_info)
        self.server1.connect()

        conn_info['port'] = self.server2.port
        conn_info['port'] = self.server2.port
        self.server2 = Server.fromServer(self.server2, conn_info)
        self.server2.connect()

        conn_info['port'] = self.server3.port
        conn_info['port'] = self.server3.port
        self.server3 = Server.fromServer(self.server3, conn_info)
        self.server3.connect()

        conn_info['port'] = self.server4.port
        conn_info['port'] = self.server4.port
        self.server4 = Server.fromServer(self.server4, conn_info)
        self.server4.connect()

        conn_info['port'] = self.server5.port
        conn_info['port'] = self.server5.port
        self.server5 = Server.fromServer(self.server5, conn_info)
        self.server5.connect()

        # Update server list prior to check.
        servers = [self.server1, self.server2, self.server3,
                   self.server4, self.server5]

        server_n = 0
        for server in servers:
            server_n += 1
            res = server.exec_query("SHOW STATUS LIKE 'Ssl_cipher'")
            if not res[0][1]:
                raise MUTLibError("Cannot spawn the SSL server{0}."
                                  "".format(server_n))

        # Reset spawned servers (clear binary log and GTID_EXECUTED set)
        self.reset_master([self.server1, self.server2, self.server3,
                           self.server4, self.server5])

        return rpl_admin.test.reset_topology(self)

    def run(self):
        self.res_fname = "result.txt"

        master_conn = self.build_connection_string(self.server1).strip(" ")
        slave1_conn = self.build_connection_string(self.server2).strip(" ")
        slave2_conn = self.build_connection_string(self.server3).strip(" ")
        slave3_conn = self.build_connection_string(self.server4).strip(" ")
        slave4_conn = self.build_connection_string(self.server5).strip(" ")
        # Failover must work even with a slave that does not exist
        slave5_conn = "doesNotExist@localhost:999999999999"

        master_str = "--master={0}".format(master_conn)
        slaves_str = "--slaves={0}".format(
            ",".join([slave1_conn, slave2_conn, slave3_conn, slave5_conn])
        )
        self.test_results = []
        self.test_cases = []

        failover_cmd = (
            "{0} {1}"
            "".format("python ../scripts/mysqlfailover.py --interval=10 "
                      "--daemon={0} --discover-slaves-login=root:root {1} "
                      "--failover-mode={2} --log={3} "
                      "--exec-post-fail=\"{4}\" --timeout=5{5}",
                      ssl_util_opts())
        )

        i = 1
        cmd = failover_cmd.format("nodetach",
                                  " ".join([master_str, slaves_str]), "auto",
                                  _FAILOVER_LOG.format("1"),
                                  self.fail_event_script,
                                  " --candidates={0}".format(slave1_conn))
        self.test_cases.append(
            (self.server1, cmd, True, _FAILOVER_LOG.format("1"),
             "Test case {0} - Simple failover with --daemon=nodetach "
             "--failover=auto.".format(i),
             _FAILOVER_COMPLETE, False)
        )

        i += 1
        cmd = failover_cmd.format("nodetach",
                                  "--master={0}".format(slave1_conn), "elect",
                                  _FAILOVER_LOG.format("2"),
                                  self.fail_event_script,
                                  " --candidates={0} ".format(slave2_conn))
        self.test_cases.append(
            (self.server2, cmd, True, _FAILOVER_LOG.format("2"),
             "Test case {0} - Simple failover with --failover=elect."
             "".format(i), _FAILOVER_COMPLETE, True)
        )

        i += 1
        cmd = failover_cmd.format("nodetach",
                                  "--master={0}".format(slave2_conn), "fail",
                                  _FAILOVER_LOG.format("3"),
                                  self.fail_event_script, "")
        self.test_cases.append(
            (self.server3, cmd, False, _FAILOVER_LOG.format("3"),
             "Test case {0} - Simple failover with --failover=fail.".format(i),
             "Master has failed and automatic", True)
        )

        i += 1
        cmd = failover_cmd.format("nodetach",
                                  "--master={0}".format(slave3_conn), "fail",
                                  _FAILOVER_LOG.format("4"),
                                  self.fail_event_script, " --force")
        self.test_cases.append(
            (self.server4, cmd, False, _FAILOVER_LOG.format("4"),
             "Test case {0} - Test with --daemon=nodetach and --force on "
             "first run.".format(i), None, True)
        )

        # Run --daemon=nodetach tests
        for test_case in self.test_cases:
            res = self.test_failover_daemon_nodetach(test_case)
            if res:
                self.test_results.append(res)
            else:
                raise MUTLibError("{0}: failed".format(test_case[4]))

        i += 1
        comment = ("Test case {0} - Start failover with --daemon=start."
                   "".format(i))
        cmd_extra = " --pidfile={0}".format(_FAILOVER_PID.format("5"))
        cmd = failover_cmd.format("start",
                                  "--master={0}".format(slave4_conn), "auto",
                                  _FAILOVER_LOG.format("5"),
                                  self.fail_event_script, cmd_extra)

        res = self.test_failover_daemon(comment, cmd,
                                        _FAILOVER_LOG.format("5"),
                                        _FAILOVER_PID.format("5"), False)
        if res:
            self.test_results.append(res)
        else:
            raise MUTLibError("{0}: failed".format(comment))

        i += 1
        comment = ("Test case {0} - Restart failover by using --daemon="
                   "restart and then stop the daemon.".format(i))
        cmd = failover_cmd.format("restart",
                                  "--master={0}".format(slave4_conn), "auto",
                                  _FAILOVER_LOG.format("5"),
                                  self.fail_event_script, cmd_extra)

        res = self.test_failover_daemon(comment, cmd,
                                        _FAILOVER_LOG.format("5"),
                                        _FAILOVER_PID.format("5"), True)
        if res:
            self.test_results.append(res)
        else:
            raise MUTLibError("{0}: failed".format(comment))

        return True
