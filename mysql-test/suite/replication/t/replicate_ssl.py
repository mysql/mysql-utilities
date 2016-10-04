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
replicate ssl test.
"""

import ConfigParser
import os

import mutlib
from mutlib.ssl_certs import (ssl_pass, ssl_user, ssl_util_opts,
                              ssl_c_ca, ssl_c_cert, ssl_c_key, SSL_OPTS)

from mysql.utilities.common.server import Server
from mysql.utilities.common.user import grant_proxy_ssl_privileges
from mysql.utilities.exception import MUTLibError, UtilDBError, UtilError

_RPL_USER_GROUP_NAME = 'rpl_user_01'


class test(mutlib.System_test):
    """setup replication
    This test executes a simple replication setup among two servers with SSL.
    """

    server0 = None
    server1 = None
    server2 = None
    s1_serverid = None
    s2_serverid = None
    test_server_names = None
    config_file_path = None

    def check_prerequisites(self):
        # This test requires server version < 5.5.7, due to the lack of
        # 'GRANT PROXY ON ...' on previews versions.
        if not self.servers.get_server(0).check_version_compat(5, 5, 8):
            raise MUTLibError("Test requires server version 5.5.8")
        return self.check_num_servers(1)

    def setup(self):
        self.config_file_path = 'replicate_ssl.cnf'
        self.server0 = self.servers.get_server(0)

        mysqld = (
            "--log-bin=mysql-bin --report-port={0} {1}"
        ).format(self.servers.view_next_port(), SSL_OPTS)
        self.server1 = self.servers.spawn_server(
            "rep_server1_ssl", mysqld, True)
        mysqld = (
            "--log-bin=mysql-bin --report-port={0} {1}"
        ).format(self.servers.view_next_port(), SSL_OPTS)
        self.server2 = self.servers.spawn_server(
            "rep_server2_ssl", mysqld, True)

        for server in [self.server1, self.server2]:
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
        res = self.server1.exec_query("SHOW STATUS LIKE 'Ssl_cipher'")
        if not res[0][1]:
            raise MUTLibError("Cannot spawn a SSL server1.")

        conn_info['port'] = self.server2.port
        conn_info['port'] = self.server2.port
        self.server2 = Server.fromServer(self.server2, conn_info)
        self.server2.connect()
        res = self.server2.exec_query("SHOW STATUS LIKE 'Ssl_cipher'")
        if not res[0][1]:
            raise MUTLibError("Cannot spawn a SSL server2.")

        # setup config_path
        config_p = ConfigParser.ConfigParser()
        self.test_server_names = []
        servers_ = [self.server1, self.server2]
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
            # rpl_user group
            group_name = _RPL_USER_GROUP_NAME
            self.test_server_names.append(group_name)
            config_p.add_section(group_name)
            config_p.set(group_name, 'user', group_name)
            config_p.set(group_name, 'password', "rpl_user_pass")
            config_p.write(config_f)

        self.s1_serverid = 'server_{0}'.format(self.server1.port)
        self.s2_serverid = 'server_{0}'.format(self.server2.port)
        return True

    def run_rpl_test(self, slave, master, comment, options=None,
                     save_for_compare=False, expected_result=0,
                     save_results=True, ssl=False, config_path=False,
                     rpl_user='rpl', rpl_pass='rpl',
                     ssl_opts=ssl_util_opts(), use_rpl_user_group=False):
        """Run replication test.

        slave[in]               Slave instance.
        master[in]              Master instance.
        comment[in]             Test case comment.
        options[in]             Options.
        save_for_compare[in]    True for save compare
        expected_result[in]     Expected result.
        save_results[in]        True for save results.
        ssl[in]                 use ssl by default False.
        config_path[in]         use config-path by default False.
        rpl_user[in]            the rpl user name to use by default 'rpl'.
        rpl_pass[in]            the rpl user password to use by default 'rpl'.
        ssl_opts[in]            the ssl certificate options.
        use_rpl_user_group[in]  use rpl user from config-path by default false.
        """
        if not config_path:
            master_str = "--master={0}".format(
                self.build_connection_string(master))
        else:
            master_ = 'server_{0}'.format(master.port)
            master_str = "--master={0}[{1}]".format(self.config_file_path,
                                                    master_)
        if not config_path:
            slave_str = " --slave={0}".format(
                self.build_connection_string(slave))
        else:
            slave_ = 'server_{0}'.format(slave.port)
            slave_str = " --slave={0}[{1}]".format(self.config_file_path,
                                                   slave_)
        conn_str = '{0}{1}'.format(master_str, slave_str)

        # Test case 1 - setup replication among two servers
        if not save_for_compare:
            self.results.append(comment)
        if use_rpl_user_group:
            cmd = (
                "mysqlreplicate.py --rpl-user={0}[{1}] {2}"
            ).format(self.config_file_path, _RPL_USER_GROUP_NAME, conn_str)
        else:
            cmd = (
                "mysqlreplicate.py --rpl-user={0}:{1} {2}"
            ).format(rpl_user, rpl_pass, conn_str)
        if ssl:
            cmd = "{0} {1}".format(cmd, ssl_opts)
        if options:
            cmd = "{0} {1}".format(cmd, options)
        if not save_for_compare and save_results:
            self.results.append(cmd)
        res = self.exec_util(cmd, self.res_fname)
        if not save_for_compare and save_results:
            self.results.append(res)

        if res != expected_result:
            return False

        # Now test the result and record the action.
        try:
            res = slave.exec_query("SHOW SLAVE STATUS")
            if not save_for_compare and save_results:
                self.results.append(res)
        except UtilDBError as err:
            raise MUTLibError("Cannot show slave status: "
                              "{0}".format(err.errmsg))

        if save_for_compare:
            self.results.append(comment + "\n")
            with open(self.res_fname) as f:
                for line in f:
                    # Don't save lines that have [Warning]
                    index = line.find("[Warning]")
                    if index <= 0:
                        self.results.append(line)

        return True

    def run(self):
        self.res_fname = "result.txt"

        test_num = 1
        comment = ("Test case {0} - replicate server1 as slave of "
                   "server2 ".format(test_num))
        res = self.run_rpl_test(self.server1, self.server2, self.s1_serverid,
                                comment, None, ssl=True, config_path=False,
                                rpl_user=ssl_user, rpl_pass=ssl_pass)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        try:
            self.server1.exec_query("STOP SLAVE")
        except UtilError:
            raise MUTLibError("{0}: Failed to stop slave.".format(comment))

        test_num += 1
        comment = ("Test case {0} - replicate server2 as slave of "
                   "server1 ".format(test_num))
        res = self.run_rpl_test(self.server2, self.server1, self.s2_serverid,
                                comment, None, ssl=True, config_path=False,
                                rpl_user=ssl_user, rpl_pass=ssl_pass)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        try:
            self.server2.exec_query("STOP SLAVE")
        except UtilError:
            raise MUTLibError("{0}: Failed to stop slave.".format(comment))

        test_num += 1
        comment = ("Test case {0} - replicate server1 as slave of "
                   "server2 ".format(test_num))
        res = self.run_rpl_test(self.server1, self.server2, self.s1_serverid,
                                comment, None, config_path=True,
                                rpl_user=ssl_user, rpl_pass=ssl_pass,
                                ssl_opts='')
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        try:
            self.server1.exec_query("STOP SLAVE")
        except UtilError:
            raise MUTLibError("{0}: Failed to stop slave.".format(comment))

        test_num += 1
        comment = ("Test case {0} - replicate server2 as slave of "
                   "server1 ".format(test_num))
        res = self.run_rpl_test(self.server2, self.server1, self.s2_serverid,
                                comment, None, ssl=True, config_path=True,
                                rpl_user=ssl_user, rpl_pass=ssl_pass,
                                ssl_opts='')
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        try:
            self.server2.exec_query("STOP SLAVE")
        except UtilError:
            raise MUTLibError("{0}: Failed to stop slave.".format(comment))

        test_num += 1
        comment = ("Test case {0} - replicate server1 as slave of "
                   "server2 with rpl_user=config-path ".format(test_num))
        res = self.run_rpl_test(self.server1, self.server2, self.s1_serverid,
                                comment, None, config_path=True,
                                use_rpl_user_group=True)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        try:
            self.server1.exec_query("STOP SLAVE")
        except UtilError:
            raise MUTLibError("{0}: Failed to stop slave.".format(comment))

        test_num += 1
        comment = ("Test case {0} - replicate server2 as slave of "
                   "server1 with rpl_user=config-path ".format(test_num))
        res = self.run_rpl_test(self.server2, self.server1, self.s2_serverid,
                                comment, None, ssl=True, config_path=False,
                                use_rpl_user_group=True)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        try:
            self.server2.exec_query("STOP SLAVE")
        except UtilError:
            raise MUTLibError("{0}: Failed to stop slave.".format(comment))

        return True

    def check_test_case(self, index, comment):
        """Check test case.

        index[in]     Index.
        comment[in]   Comment.
        """
        msg = None
        test_passed = True

        # Check test case
        if self.results[index] == 0:
            if self.results[index + 1] == ():
                return False, "{0}: Slave status missing.".format(comment)
            test_result = self.results[index + 1][0]
            if test_result[0] != "Waiting for master to send event":
                test_passed = False
                msg = ("{0}: Slave failed to communicate with "
                       "master.".format(comment))
        else:
            test_passed = False
            msg = "{0}: Replication event failed.".format(comment)
        return test_passed, msg

    def get_result(self):
        """Gets the result.
        """
        # tc1 tc2 content
        # --- --- -----
        #  0   4  comment
        #  1   5  command
        #  2   6  result of exec_util
        #  3   7  result of SHOW SLAVE STATUS
        # tc3 tc4 content
        # --- --- -----
        #  8   12  comment
        #  9   13  command
        #  10  14  result of exec_util
        #  11  15  result of SHOW SLAVE STATUS

        res = self.check_test_case(2, "Test case 1")
        if not res[0]:
            return res

        res = self.check_test_case(6, "Test case 2")
        if not res[0]:
            return res

        res = self.check_test_case(10, "Test case 3")
        if not res[0]:
            return res

        res = self.check_test_case(14, "Test case 4")
        if not res[0]:
            return res

        return True, None

    def mask_results(self):
        """Mask the results.
        """
        self.mask_column_result("| builtin", "|", 2, " XXXXXXXX ")
        self.mask_column_result("| XXXXXXX", "|", 3, " XXXXXXXXXXXXXXX ")
        self.mask_column_result("| XXXXXXX", "|", 4, " XXXXXXXXXXXXXXXXXXXX ")

        self.replace_result("#  slave id =", "#  slave id = XXX\n")
        self.replace_result("# master id =", "# master id = XXX\n")
        self.replace_result("# master uuid = ",
                            "# master uuid = XXXXX\n")
        self.replace_result("#  slave uuid = ",
                            "#  slave uuid = XXXXX\n")

        self.remove_result("# Creating replication user...")
        self.remove_result("CREATE USER 'rpl'@'localhost'")
        self.remove_result("# Granting replication access")
        self.remove_result("# CHANGE MASTER TO MASTER_HOST = 'localhost'")

    def record(self):
        # Not a comparative test, returning True
        return True

    def cleanup(self):
        if self.res_fname:
            try:
                os.unlink(self.res_fname)
                os.unlink(self.config_file_path)
            except OSError:
                pass
        return True
