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
rpl_admin_basic_ssl_opt_gtid_config_path test with ssl option using
config-path.
"""

import ConfigParser

import rpl_admin_basic_ssl_gtid_config_path
from rpl_admin_basic_ssl_gtid_config_path import (_DEFAULT_MYSQL_OPTS,
                                                  _DEFAULT_MYSQL_OPTS_DIFF_SSL)

from mysql.utilities.exception import MUTLibError, UtilError
from mysql.utilities.common.server import Server
from mysql.utilities.common.user import grant_proxy_ssl_privileges
from mutlib.ssl_certs import (ssl_pass, ssl_user, ssl_c_ca, ssl_c_cert,
                              ssl_c_key, ssl_c_ca_b, ssl_c_cert_b, ssl_c_key_b)


class test(rpl_admin_basic_ssl_gtid_config_path.test):
    """test replication administration commands
    This test runs the mysqlrpladmin utility on a known topology with
    configured servers with different ssl certificates using config-path login.

    Note: this test requires GTID enabled servers.
    """

    config_file_path = None
    servers_list = None
    test_server_names = None

    def check_prerequisites(self):
        if not self.servers.get_server(0).check_version_compat(5, 6, 9):
            raise MUTLibError("Test requires server version 5.6.9")
        return self.check_num_servers(1)

    def setup(self):
        self.res_fname = "result.txt"
        self.config_file_path = 'rpl_admin_b_ssl.cnf'

        # Spawn servers
        self.server0 = self.servers.get_server(0)
        mysqld = _DEFAULT_MYSQL_OPTS.format(self.servers.view_next_port())
        self.server1 = self.servers.spawn_server(
            "rep_master_gtid_ssl", mysqld, True
        )
        mysqld = _DEFAULT_MYSQL_OPTS.format(self.servers.view_next_port())
        self.server2 = self.servers.spawn_server(
            "rep_slave1_gtid_ssl", mysqld, True
        )
        mysqld = _DEFAULT_MYSQL_OPTS_DIFF_SSL.format(
            self.servers.view_next_port()
        )
        self.server3 = self.servers.spawn_server(
            "rep_slave2_gtid_ssl", mysqld, True
        )
        mysqld = _DEFAULT_MYSQL_OPTS.format(self.servers.view_next_port())
        self.server4 = self.servers.spawn_server(
            "rep_slave3_gtid_ssl", mysqld, True
        )

        self.servers_list = [self.server1, self.server2,
                             self.server3, self.server4]

        for server in self.servers_list:
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
        self.server1 = Server.fromServer(self.server1, conn_info)
        self.server1.connect()

        conn_info['port'] = self.server2.port
        self.server2 = Server.fromServer(self.server2, conn_info)
        self.server2.connect()

        conn_info['port'] = self.server3.port
        conn_info['ssl_ca'] = ssl_c_ca_b
        conn_info['ssl_cert'] = ssl_c_cert_b
        conn_info['ssl_key'] = ssl_c_key_b
        self.server3 = Server.fromServer(self.server3, conn_info)
        self.server3.connect()

        conn_info['port'] = self.server4.port
        conn_info['ssl_ca'] = ssl_c_ca
        conn_info['ssl_cert'] = ssl_c_cert
        conn_info['ssl_key'] = ssl_c_key
        self.server4 = Server.fromServer(self.server4, conn_info)
        self.server4.connect()

        for server_n, server in enumerate([self.server1, self.server2,
                                           self.server3, self.server4]):
            res = server.exec_query("SHOW STATUS LIKE 'Ssl_cipher'")
            if not res[0][1]:
                raise MUTLibError("Cannot spawn the SSL server{0}."
                                  "".format(server_n))

        # Reset spawned servers (clear binary log and GTID_EXECUTED set)
        self.reset_master()

        # Update server list
        self.servers_list = [self.server1, self.server2,
                             self.server3, self.server4]

        # setup config_path
        config_p = ConfigParser.ConfigParser()
        self.test_server_names = []

        with open(self.config_file_path, 'w') as config_f:
            for server in self.servers_list:
                group_name = 'server_{0}'.format(server.port)
                self.test_server_names.append(group_name)
                config_p.add_section(group_name)
                config_p.set(group_name, 'user', server.user)
                config_p.set(group_name, 'password', server.passwd)
                config_p.set(group_name, 'host', server.host)
                config_p.set(group_name, 'port', server.port)
                config_p.set(group_name, 'ssl', 1)
            config_p.write(config_f)

        master = self.servers_list[0]
        slaves_list = self.servers_list[1:]

        # Used for port masking.
        self.m_port = self.server1.port
        self.s1_port = self.server2.port
        self.s2_port = self.server3.port
        self.s3_port = self.server4.port

        return self.reset_topology(slaves_list, master=master)
