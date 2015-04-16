#
# Copyright (c) 2014, 2015, Oracle and/or its affiliates. All rights reserved.
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
config_parser test.
"""

import ConfigParser
import os

from mysql.utilities.exception import MUTLibError, UtilError
from mysql.utilities.common.server import Server
from mysql.utilities.common.user import grant_proxy_ssl_privileges
from mutlib.ssl_certs import (ssl_pass, ssl_user, ssl_server_opts,
                              ssl_c_ca, ssl_c_cert, ssl_c_key)

import server_info


class test(server_info.test):
    """Test the config-path authentication mechanism.
    This module tests the ability to login to MySQL server using a
    configuration file.
    """

    config_file_path = os.path.abspath('./temp.cnf')
    test_group_names = []

    def check_prerequisites(self):
        # This test requires server version < 5.5.7, due to the lack of
        # 'GRANT PROXY ON ...' on previous versions.
        if not self.servers.get_server(0).check_version_compat(5, 5, 8):
            raise MUTLibError("Test requires server version >= 5.5.8")
        # Check the required number of servers
        return self.check_num_servers(1)

    def setup(self):
        # Remove previews configuration files (leftover from previous test).
        try:
            os.unlink(self.config_file_path)
        except OSError:
            pass
        # use --log-error option in order to normalize serverinfo
        # output between 5.6 and 5.7 servers by setting log_err to stderr
        startup_opts = "{0} --log-error=error_log".format(ssl_server_opts())
        try:
            self.servers.spawn_server('ssl_server',
                                      startup_opts, kill=False)
        except MUTLibError as err:
            raise MUTLibError("Cannot spawn needed servers: {0}"
                              "".format(err.errmsg))

        index = self.servers.find_server_by_name('ssl_server')
        self.server1 = self.servers.get_server(index)

        for server in [self.server1]:
            try:
                grant_proxy_ssl_privileges(server, ssl_user, ssl_pass)
            except UtilError as err:
                raise MUTLibError("{0} on: {1}".format(err.errmsg,
                                                       server.role))

        conn_info = {
            'user': ssl_user,
            'passwd': ssl_pass,
            'host': self.server1.host,
            'port': self.server1.port,
            'ssl_ca': ssl_c_ca,
            'ssl_cert': ssl_c_cert,
            'ssl_key': ssl_c_key,
        }

        self.server2 = Server.fromServer(self.server1, conn_info)
        self.server2.connect()

        res = self.server2.exec_query("SHOW STATUS LIKE 'Ssl_cipher'")
        if not res[0][1]:
            raise MUTLibError('Cannot setup SSL server for test')

        config_p = ConfigParser.ConfigParser()
        with open(self.config_file_path, 'w') as config_f:

            config_p.add_section('client')
            config_p.set('client', 'user', self.server1.user)
            config_p.set('client', 'password', self.server1.passwd)
            config_p.set('client', 'host', self.server1.host)
            config_p.set('client', 'port', self.server1.port)

            self.test_group_names.append(('simple group name', 'simple_login'))
            config_p.add_section('simple_login')
            config_p.set('simple_login', 'user', self.server1.user)
            config_p.set('simple_login', 'password', self.server1.passwd)
            config_p.set('simple_login', 'host', self.server1.host)
            config_p.set('simple_login', 'port', self.server1.port)

            group_name = 'very_loooooooooooooooooooooooong_group_name'
            self.test_group_names.append(('long group name ', group_name))
            config_p.add_section(group_name)
            config_p.set(group_name, 'user', self.server1.user)
            config_p.set(group_name, 'password', self.server1.passwd)
            config_p.set(group_name, 'host', self.server1.host)

            config_p.set(group_name, 'port', self.server1.port)

            group_name = 'c0Mpl1-cat3d//name_group'
            self.test_group_names.append(('complicated group name ',
                                          group_name))
            config_p.add_section(group_name)
            config_p.set(group_name, 'user', self.server1.user)
            config_p.set(group_name, 'password', self.server1.passwd)
            config_p.set(group_name, 'host', self.server1.host)
            config_p.set(group_name, 'port', self.server1.port)

            config_p.add_section('ssl-login')
            self.test_group_names.append(('login with ssl', 'ssl-login'))
            config_p.set('ssl-login', 'user', self.server2.user)
            config_p.set('ssl-login', 'password', self.server2.passwd)
            config_p.set('ssl-login', 'host', self.server2.host)
            config_p.set('ssl-login', 'port', self.server2.port)
            config_p.set('ssl-login', 'ssl-ca', self.server2.ssl_ca)
            config_p.set('ssl-login', 'ssl-cert', self.server2.ssl_cert)
            config_p.set('ssl-login', 'ssl-key', self.server2.ssl_key)
            config_p.write(config_f)

        return True

    def run(self):
        self.res_fname = "result.txt"
        test_num = 0

        for test in self.test_group_names:
            test_name, group_name = test
            test_num += 1

            comment = ("Test case {0} - serverinfo with config_path, {1}"
                       "").format(test_num, test_name)
            test_cmd = ('mysqlserverinfo.py --server="{0}{1}" --format='
                        "vertical").format(self.config_file_path,
                                           "[{0}]".format(group_name))

            res = self.run_test_case(0, test_cmd, comment)
            if not res:
                raise MUTLibError("{0}: failed".format(comment))
            self.results.append('\n')

        self.do_replacements()

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        os.remove(self.config_file_path)
        self.servers.stop_server(self.server2)
        self.servers.remove_server(self.server2.role)
        return True
