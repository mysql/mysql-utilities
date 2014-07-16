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
replicate_ms test with SSL.
"""

import os

import ConfigParser

import replicate_ms

from mysql.utilities.common.server import Server
from mysql.utilities.common.user import grant_proxy_ssl_privileges
from mysql.utilities.exception import MUTLibError, UtilError
from mutlib.ssl_certs import (ssl_pass, ssl_user, ssl_util_opts, ssl_c_ca,
                              ssl_c_cert, ssl_c_key, SSL_OPTS)

_RPLMS_LOG = "{0}rplms_log.txt"
_TIMEOUT = 30
_SWITCHOVER_TIMEOUT = 60
_DEFAULT_MYSQL_OPTS = ('"--log-bin=mysql-bin --skip-slave-start '
                       '--log-slave-updates --gtid-mode=on '
                       '--enforce-gtid-consistency --report-host=127.0.0.1 '
                       '--report-port={0} '
                       '--sync-master-info=1 --master-info-repository=table '
                       '{1}"').format('{port}', SSL_OPTS)


class test(replicate_ms.test):
    """Test multi-source replication with SSL.

    This test exercises the mysqlrplms utility using SSL.
    """

    log_range = range(1, 2)
    total_masters = 2
    server0 = None
    server1 = None
    server2 = None
    server3 = None
    test_server_names = None
    config_file_path = 'replicate_ms_ssl.cnf'

    def setup(self):
        self.res_fname = "result.txt"

        # Spawn servers
        self.server0 = self.servers.get_server(0)
        mysqld = _DEFAULT_MYSQL_OPTS.format(port=self.servers.view_next_port())
        self.server1 = self.servers.spawn_server("rep_slave", mysqld, True)
        mysqld = _DEFAULT_MYSQL_OPTS.format(port=self.servers.view_next_port())
        self.server2 = self.servers.spawn_server("rep_master1", mysqld, True)
        mysqld = _DEFAULT_MYSQL_OPTS.format(port=self.servers.view_next_port())
        self.server3 = self.servers.spawn_server("rep_master2", mysqld, True)
        self.total_masters = 2

        for server in [self.server1, self.server2, self.server3]:
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

        # Drop all
        self.drop_all()

        # Reset topology
        self.reset_ms_topology()

        # Create data
        self.create_all()

        # Remove log files (leftover from previous test).
        self.cleanup_logs()

        # setup config_path
        config_p = ConfigParser.ConfigParser()
        self.test_server_names = []
        servers_ = [self.server1, self.server2, self.server3]
        with open(self.config_file_path, 'w') as config_f:
            for server in servers_:
                group_name = 'server_{0}'.format(server.port)
                self.test_server_names.append(group_name)
                config_p.add_section(group_name)
                config_p.set(group_name, 'user', server.user)
                config_p.set(group_name, 'password', server.passwd)
                config_p.set(group_name, 'host', server.host)
                config_p.set(group_name, 'port', server.port)
                config_p.set(group_name, 'ssl-ca', server.ssl_ca)
                config_p.set(group_name, 'ssl-cert', server.ssl_cert)
                config_p.set(group_name, 'ssl-key', server.ssl_key)
            config_p.write(config_f)

        server_n = 0
        for server in servers_:
            server_n += 1
            res = server.exec_query("SHOW STATUS LIKE 'Ssl_cipher'")
            if not res[0][1]:
                raise MUTLibError("Cannot spawn the SSL server{0}."
                                  "".format(server_n))

        return True

    def compare_databases(self, comment):
        """Compare databases.

        This method compares the databases replicated.

        comment[in]       Test comment.
        """
        # Compare command
        compare_cmd = "mysqldbcompare.py {0} {1} {2}:{2} {3}"
        from_conn = "--server1={0}".format(
            self.build_connection_string(self.server1))

        # Compare `inventory` database from master1
        to_conn = "--server2={0}".format(
            self.build_connection_string(self.server2)
        )
        res = self.run_test_case(
            0,
            compare_cmd.format(from_conn, to_conn, "inventory",
                               ssl_util_opts()),
            "Comparing `inventory` database."
        )
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Compare `import_test` database from master2
        to_conn = "--server2={0}".format(
            self.build_connection_string(self.server3)
        )
        res = self.run_test_case(
            0,
            compare_cmd.format(from_conn, to_conn, "import_test",
                               ssl_util_opts()),
            "Comparing `import_test` database."
        )
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

    def run(self):
        slave_str = "--slave={0}[{1}]".format(self.config_file_path,
                                              self.test_server_names[0])
        masters_str = "--masters={0}[{1}],{0}[{2}]".format(
            self.config_file_path,
            self.test_server_names[1],
            self.test_server_names[2]
        )

        test_num = 1
        rplms_cmd = ("python ../scripts/mysqlrplms.py --log={0} --interval=5 "
                     "--switchover-interval=30 --rpl-user=rpl:rpl {1} {2} {3}"
                     "".format(_RPLMS_LOG.format(test_num), slave_str,
                               masters_str, ssl_util_opts()))
        comment = ("Test case {0} - Simple multi-source replication."
                   "".format(test_num))
        self.test_rplms(rplms_cmd, _RPLMS_LOG.format(test_num), comment, True)
        return True

    def cleanup(self):
        try:
            os.unlink(self.config_file_path)
        except OSError:
            pass
        return replicate_ms.test.cleanup(self)
