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
rpl_admin_basic_ssl_gtid test with different ssl certificates, using
config-path.
"""

import ConfigParser
import os

import rpl_admin

from mysql.utilities.exception import MUTLibError, UtilError
from mysql.utilities.common.server import Server
from mysql.utilities.common.user import grant_proxy_ssl_privileges
from mutlib.ssl_certs import (ssl_pass, ssl_user, ssl_c_ca, ssl_c_cert,
                              ssl_c_key, ssl_c_ca_b, ssl_c_cert_b,
                              ssl_c_key_b, SSL_OPTS, SSL_OPTS_B)

_DEFAULT_MYSQL_OPTS = ('"--log-bin=mysql-bin --skip-slave-start '
                       '--log-slave-updates --gtid-mode=on '
                       '--enforce-gtid-consistency --report-host=localhost '
                       '--report-port={0} --bind-address=:: '
                       '--master-info-repository=table {1}'
                       '"').format('{0}', SSL_OPTS)

_DEFAULT_MYSQL_OPTS_DIFF_SSL = ('"--log-bin=mysql-bin --skip-slave-start '
                                '--log-slave-updates --gtid-mode=on '
                                '--enforce-gtid-consistency --report-host='
                                'localhost --report-port={0} '
                                '--bind-address=:: '
                                '--master-info-repository=table {1}'
                                '"').format('{0}', SSL_OPTS_B)


class test(rpl_admin.test):
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

    def reset_topology(self, slaves_list=None, rpl_user='rpl',
                       rpl_passwd='rpl', master=None, ssl=False):
        """Reset topology.

        server_list[in]     List with the server instances.
        rpl_user[in]        Replication user. Default=rpl.
        rpl_passwd[in]      Replication password. Default=rpl
        master[in]          Master server instance.

        """

        if master is None:
            master = self.server1  # Use server1 as default master.
        group_name = 'server_{0}'.format(master.port)
        master_str = " --master={0}[{1}]".format(self.config_file_path,
                                                 group_name)

        servers = [master]
        servers.extend(slaves_list)

        for slave in servers:
            try:
                slave.exec_query("STOP SLAVE")
                slave.exec_query("RESET SLAVE")
            except UtilError:
                pass

        for slave in slaves_list:
            group_name = 'server_{0}'.format(slave.port)
            slave_str = " --slave={0}[{1}]".format(self.config_file_path,
                                                   group_name)
            conn_str = "{0} {1}".format(master_str, slave_str)
            cmd = ("mysqlreplicate.py --rpl-user={0}:{1} {2} "
                   "-vvv".format(rpl_user, rpl_passwd, conn_str))
            res = self.exec_util(cmd, self.res_fname)
            if res != 0:
                return False

        return True

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
        conn_info['port'] = self.server1.port
        self.server1 = Server.fromServer(self.server1, conn_info)
        self.server1.connect()

        conn_info['port'] = self.server2.port
        conn_info['port'] = self.server2.port
        self.server2 = Server.fromServer(self.server2, conn_info)
        self.server2.connect()

        conn_info['port'] = self.server3.port
        conn_info['port'] = self.server3.port
        conn_info['ssl_ca'] = ssl_c_ca_b
        conn_info['ssl_cert'] = ssl_c_cert_b
        conn_info['ssl_key'] = ssl_c_key_b
        self.server3 = Server.fromServer(self.server3, conn_info)
        self.server3.connect()

        conn_info['port'] = self.server4.port
        conn_info['port'] = self.server4.port
        conn_info['ssl_ca'] = ssl_c_ca
        conn_info['ssl_cert'] = ssl_c_cert
        conn_info['ssl_key'] = ssl_c_key
        self.server4 = Server.fromServer(self.server4, conn_info)
        self.server4.connect()

        server_n = 0
        for server in [self.server1, self.server2, self.server3,
                       self.server4]:
            server_n += 1
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
                config_p.set(group_name, 'ssl-ca', server.ssl_ca)
                config_p.set(group_name, 'ssl-cert', server.ssl_cert)
                config_p.set(group_name, 'ssl-key', server.ssl_key)
            config_p.write(config_f)

        master = self.servers_list[0]
        slaves_list = self.servers_list[1:]

        # Used for port masking.
        self.m_port = self.server1.port
        self.s1_port = self.server2.port
        self.s2_port = self.server3.port
        self.s3_port = self.server4.port

        return self.reset_topology(slaves_list, master=master)

    def run(self):
        config_file = self.config_file_path
        master = '{0}[server_{1}]'.format(config_file, self.server1.port)
        slave1 = '{0}[server_{1}]'.format(config_file, self.server2.port)
        slave2 = '{0}[server_{1}]'.format(config_file, self.server3.port)
        slave3 = '{0}[server_{1}]'.format(config_file, self.server4.port)

        test_num = 1
        comment = ("Test case {0} - SSL "
                   "switchover demote-master ".format(test_num))
        cmd_str = "mysqlrpladmin.py --master={0} ".format(master)
        slaves = [slave1, slave2, slave3]
        cmd_opts = (" --new-master={0} "
                    "--rpl-user=rpluser:hispassword --demote-master "
                    "switchover --slaves={1}"
                    "").format(slave1, ",".join(slaves))
        cmds = "{0} {1}".format(cmd_str, cmd_opts)
        res = self.run_test_case(0, cmds, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        self.results.append("\n")

        test_num += 1
        comment = ("Test case {0} - SSL mysqlrplcheck "
                   "NEW Master after demote".format(test_num))
        cmd_opts = "--slave={0} --show-slave-status".format(master)
        cmd_str = "mysqlrplcheck.py --master={0} ".format(slave1)
        cmds = "{0} {1}".format(cmd_str, cmd_opts)
        res = self.run_test_case(0, cmds, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        self.results.append("\n")

        test_num += 1
        comment = ("Test case {0} - SSL mysqlrplcheck "
                   "NEW Master after demote".format(test_num))
        cmd_opts = "--slave={0} --show-slave-status".format(slave2)
        cmds = "{0} {1}".format(cmd_str, cmd_opts)
        res = self.run_test_case(0, cmds, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        self.results.append("\n")

        test_num += 1
        comment = ("Test case {0} - SSL mysqlrplcheck "
                   "NEW Master after demote".format(test_num))
        cmd_opts = "--slave={0} --show-slave-status".format(slave3)
        cmds = "{0} {1}".format(cmd_str, cmd_opts)
        res = self.run_test_case(0, cmds, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        self.results.append("\n")

        test_num += 1
        comment = ("Test case {0} - SSL "
                   "failover ".format(test_num))
        cmd_str = "mysqlrpladmin.py --master={0}".format(slave1)
        slaves = ",".join([slave2, slave3,
                           master])
        cmd_opts = (" --slaves={0} --rpl-user=rpluser:hispassword "
                    "failover".format(slaves))
        cmd_opts = "{0} --candidates={1}".format(cmd_opts, slaves)
        cmds = "{0} {1}".format(cmd_str, cmd_opts)
        res = self.run_test_case(0, cmds, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        self.results.append("\n")

        test_num += 1
        comment = ("Test case {0} - SSL mysqlrplcheck "
                   "NEW Master after demote".format(test_num))
        cmd_str = "mysqlrplcheck.py --master={0} ".format(slave2)
        cmd_opts = "--slave={0} --show-slave-status".format(master)
        cmds = "{0} {1}".format(cmd_str, cmd_opts)
        res = self.run_test_case(0, cmds, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        self.results.append("\n")

        test_num += 1
        comment = ("Test case {0} - SSL mysqlrplcheck "
                   "NEW Master after demote".format(test_num))
        cmd_opts = "--slave={0} --show-slave-status".format(slave3)
        cmds = "{0} {1}".format(cmd_str, cmd_opts)
        res = self.run_test_case(0, cmds, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        self.results.append("\n")

        # Mask out non-deterministic data
        rpl_admin.test.do_masks(self)

        self.replace_result("# QUERY = SELECT "
                            "WAIT_UNTIL_SQL_THREAD_AFTER_GTIDS(",
                            "# QUERY = SELECT "
                            "WAIT_UNTIL_SQL_THREAD_AFTER_GTIDS(XXXXX)\n")

        self.remove_result_and_lines_before("WARNING: There are slaves that"
                                            " had connection errors.")

        self.replace_result("| 127.0.0.1  | PORT2  | MASTER  | UP     "
                            "| ON         | OK      | ",
                            "| 127.0.0.1  | PORT2  | MASTER  | UP     "
                            "| ON         | OK      | XXXXXXXX    "
                            "| XXXXXXXX          | XXXXXXXX        "
                            "|            |             |              "
                            "|                  |               |           "
                            "|                |            "
                            "|               |\n")

        self.replace_result("| 127.0.0.1  | PORT1  | SLAVE   | UP     "
                            "| ON         | OK      | ",
                            "| 127.0.0.1  | PORT1  | SLAVE   | UP     "
                            "| ON         | OK      | XXXXXXXX    "
                            "| XXXXXXXX          | XXXXXXXX        "
                            "| Yes        | Yes         | 0            "
                            "| No               | 0             |           "
                            "| 0              |            "
                            "| 0             |\n")

        self.replace_result("| 127.0.0.1  | PORT3  | SLAVE   | UP     "
                            "| ON         | OK      | ",
                            "| 127.0.0.1  | PORT3  | SLAVE   | UP     "
                            "| ON         | OK      | XXXXXXXX    "
                            "| XXXXXXXX          | XXXXXXXX        "
                            "| Yes        | Yes         | 0            "
                            "| No               | 0             |           "
                            "| 0              |            "
                            "| 0             |\n")

        self.replace_result("| 127.0.0.1  | PORT4  | SLAVE   | UP     "
                            "| ON         | OK      | ",
                            "| 127.0.0.1  | PORT4  | SLAVE   | UP     "
                            "| ON         | OK      | XXXXXXXX    "
                            "| XXXXXXXX          | XXXXXXXX        "
                            "| Yes        | Yes         | 0            "
                            "| No               | 0             |           "
                            "| 0              |            "
                            "| 0             |\n")

        self.replace_result("| 127.0.0.1  | PORT1  | MASTER  | UP     "
                            "| ON         | OK      | ",
                            "| 127.0.0.1  | PORT1  | MASTER  | UP     "
                            "| ON         | OK      | XXXXXXXX    "
                            "| XXXXXXXX          | XXXXXXXX        "
                            "|            |             |              "
                            "|                  |               |           "
                            "|                |            "
                            "|               |\n")

        self.mask_column_result("| version", "|", 2, " XXXXXXXX ")
        self.mask_column_result("| master_log_file", "|", 2, " XXXXXXXX ")
        self.mask_column_result("| master_log_pos", "|", 2, " XXXXXXXX ")

        # Mask slaves behind master.
        # It happens sometimes on windows in a non-deterministic way.
        self.replace_substring("+---------------------------------------------"
                               "------------------------------------------+",
                               "+---------+")
        self.replace_substring("+---------------------------------------------"
                               "-------------------------------------------+",
                               "+---------+")
        self.replace_substring("| health                                      "
                               "                                          |",
                               "| health  |")
        self.replace_substring("| health                                      "
                               "                                           |",
                               "| health  |")
        self.replace_substring("| OK                                          "
                               "                                          |",
                               "| OK      |")
        self.replace_substring("| OK                                          "
                               "                                           |",
                               "| OK      |")
        self.replace_substring_portion("| Slave delay is ",
                                       "seconds behind master., No, Slave has "
                                       "1 transactions behind master.  |",
                                       "| OK      |")
        self.replace_substring("| Slave has 1 transactions behind master.     "
                               "                                          |",
                               "| OK      |")
        self.replace_substring("| Slave has 1 transactions behind master.     "
                               "                                           |",
                               "| OK      |")

        self.replace_substring("+------------------------------------------+",
                               "+---------+")
        self.replace_substring("| health                                   |",
                               "| health  |")
        self.replace_substring("| OK                                       |",
                               "| OK      |")
        self.replace_substring("| Slave has 1 transactions behind master.  |",
                               "| OK      |")

        # Do replacements in the result for rplcheck.
        self.replace_result("            Master_SSL_CA_File :",
                            "            Master_SSL_CA_File : XXXXX\n")
        self.replace_result("               Master_SSL_Cert :",
                            "               Master_SSL_Cert : XXXX\n")
        self.replace_result("                Master_SSL_Key :",
                            "                Master_SSL_Key : XXXX\n")
        self.replace_result("                Master_SSL_Crl :",
                            "                Master_SSL_Crl : XXXX\n")

        self.remove_result("                 Connect_Retry :")
        self.remove_result("               Master_Log_File :")
        self.remove_result("           Read_Master_Log_Pos :")
        self.remove_result("                Relay_Log_File :")
        self.remove_result("                 Relay_Log_Pos :")
        self.remove_result("         Relay_Master_Log_File :")
        self.remove_result("              Slave_IO_Running :")
        self.remove_result("             Slave_SQL_Running :")
        self.remove_result("               Replicate_Do_DB :")
        self.remove_result("           Replicate_Ignore_DB :")
        self.remove_result("            Replicate_Do_Table :")
        self.remove_result("        Replicate_Ignore_Table :")
        self.remove_result("       Replicate_Wild_Do_Table :")
        self.remove_result("   Replicate_Wild_Ignore_Table :")

        self.remove_result("                  Skip_Counter :")
        self.remove_result("           Exec_Master_Log_Pos :")
        self.remove_result("               Relay_Log_Space :")
        self.remove_result("               Until_Condition :")
        self.remove_result("                Until_Log_File :")
        self.remove_result("                 Until_Log_Pos :")

        self.remove_result_and_lines_after("         Seconds_Behind_Master :",
                                           16)
        self.remove_result_and_lines_after("            Retrieved_Gtid_Set :",
                                           3)

        self.remove_result("          Replicate_Rewrite_DB :")

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        if self.res_fname:
            try:
                os.unlink(self.res_fname)
                os.unlink(self.config_file_path)
            except OSError:
                pass
        # Kill the servers that are only for this test.
        kill_list = ['rep_master_gtid_ssl',
                     'rep_slave1_gtid_ssl',
                     'rep_slave2_gtid_ssl',
                     'rep_slave3_gtid_ssl']
        self.kill_server_list(kill_list)
        return True
