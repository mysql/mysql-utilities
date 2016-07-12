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
rpl_admin_basic_ssl_gtid test.
"""

import rpl_admin

from mysql.utilities.exception import MUTLibError, UtilError
from mysql.utilities.common.server import Server
from mysql.utilities.common.user import grant_proxy_ssl_privileges
from mutlib.ssl_certs import (ssl_pass, ssl_user, ssl_util_opts, ssl_c_ca,
                              ssl_c_cert, ssl_c_key, SSL_OPTS)

_DEFAULT_MYSQL_OPTS = ('"--log-bin=mysql-bin --skip-slave-start '
                       '--log-slave-updates --gtid-mode=on '
                       '--enforce-gtid-consistency --report-host=localhost '
                       '--report-port={0} --bind-address=:: '
                       '--master-info-repository=table {1}'
                       '"').format('{0}', SSL_OPTS)


class test(rpl_admin.test):
    """test replication administration commands
    This test runs the mysqlrpladmin utility on a known topology with ssl.

    Note: this test requires GTID enabled servers.
    """

    def check_prerequisites(self):
        if not self.servers.get_server(0).check_version_compat(5, 6, 9):
            raise MUTLibError("Test requires server version >= 5.6.9")
        return self.check_num_servers(1)

    def setup(self):
        self.res_fname = "result.txt"

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
        mysqld = _DEFAULT_MYSQL_OPTS.format(self.servers.view_next_port())
        self.server3 = self.servers.spawn_server(
            "rep_slave2_gtid_ssl", mysqld, True
        )
        mysqld = _DEFAULT_MYSQL_OPTS.format(self.servers.view_next_port())
        self.server4 = self.servers.spawn_server(
            "rep_slave3_gtid_ssl", mysqld, True
        )

        for server in [self.server1, self.server2, self.server3,
                       self.server4]:
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

        self.m_port = self.server1.port
        self.s1_port = self.server2.port
        self.s2_port = self.server3.port
        self.s3_port = self.server4.port

        rpl_admin.test.reset_topology(self)

        return True

    def run(self):
        test_num = 1

        master_conn = self.build_connection_string(self.server1).strip(' ')
        slave1_conn = self.build_connection_string(self.server2).strip(' ')
        slave2_conn = self.build_connection_string(self.server3).strip(' ')
        slave3_conn = self.build_connection_string(self.server4).strip(' ')

        comment = ("Test case {0} - SSL mysqlrplshow OLD Master "
                   "before demote".format(test_num))
        cmd_str = "mysqlrplshow.py --master={0} {1} ".format(master_conn,
                                                             ssl_util_opts())
        cmd_opts = "--discover-slaves={0} ".format(master_conn.split('@')[0])
        cmds = "{0} {1}".format(cmd_str, cmd_opts)
        res = self.run_test_case(0, cmds, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - SSL "
                   "switchover demote-master ".format(test_num))
        cmd_str = ("mysqlrpladmin.py --master={0} {1} "
                   ).format(master_conn, ssl_util_opts())
        cmd_opts = (" --new-master={0} --discover-slaves={1} "
                    "--rpl-user=rpluser:hispassword --demote-master "
                    "switchover".format(slave1_conn,
                                        master_conn.split('@')[0]))
        cmds = "{0} {1}".format(cmd_str, cmd_opts)
        res = self.run_test_case(0, cmds, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        self.results.append("\n")

        test_num += 1
        comment = ("Test case {0} - SSL mysqlrplshow "
                   "NEW Master after demote".format(test_num))
        cmd_str = "mysqlrplshow.py --master={0} {1}".format(slave1_conn,
                                                            ssl_util_opts())
        cmd_opts = " --discover-slaves={0} ".format(master_conn.split('@')[0])
        cmds = "{0} {1}".format(cmd_str, cmd_opts)
        res = self.run_test_case(0, cmds, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - SSL mysqlrplcheck "
                   "NEW Master after demote".format(test_num))
        cmd_opts = "--slave={0} --show-slave-status".format(master_conn)
        cmd_str = "mysqlrplcheck.py --master={0} {1} ".format(slave1_conn,
                                                              ssl_util_opts())
        cmds = "{0} {1}".format(cmd_str, cmd_opts)
        res = self.run_test_case(0, cmds, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        self.results.append("\n")

        test_num += 1
        comment = ("Test case {0} - SSL mysqlrplcheck "
                   "NEW Master after demote".format(test_num))
        cmd_opts = "--slave={0} --show-slave-status".format(slave2_conn)
        cmds = "{0} {1}".format(cmd_str, cmd_opts)
        res = self.run_test_case(0, cmds, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        self.results.append("\n")

        test_num += 1
        comment = ("Test case {0} - SSL mysqlrplcheck "
                   "NEW Master after demote".format(test_num))
        cmd_opts = "--slave={0} --show-slave-status".format(slave3_conn)
        cmds = "{0} {1}".format(cmd_str, cmd_opts)
        res = self.run_test_case(0, cmds, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        self.results.append("\n")

        test_num += 1
        comment = ("Test case {0} - SSL "
                   "failover ".format(test_num))
        cmd_str = "mysqlrpladmin.py {0} ".format(ssl_util_opts())
        slaves = ",".join([slave2_conn, slave3_conn,
                           master_conn])
        cmd_opts = (" --slaves={0} --rpl-user=rpluser:hispassword "
                    "failover".format(slaves))
        cmds = "{0} {1}".format(cmd_str, cmd_opts)
        res = self.run_test_case(0, cmds, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        self.results.append("\n")

        test_num += 1
        comment = ("Test case {0} - SSL mysqlrplshow "
                   "NEW Master after failover".format(test_num))
        cmd_str = "mysqlrplshow.py --master={0} {1}".format(slave2_conn,
                                                            ssl_util_opts())
        cmd_opts = " --discover-slaves={0} ".format(master_conn.split('@')[0])
        cmds = "{0} {1}".format(cmd_str, cmd_opts)
        res = self.run_test_case(0, cmds, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - SSL mysqlrplcheck "
                   "NEW Master after demote".format(test_num))
        cmd_str = "mysqlrplcheck.py --master={0} {1} ".format(slave2_conn,
                                                              ssl_util_opts())
        cmd_opts = "--slave={0} --show-slave-status".format(master_conn)
        cmds = "{0} {1}".format(cmd_str, cmd_opts)
        res = self.run_test_case(0, cmds, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        self.results.append("\n")

        test_num += 1
        comment = ("Test case {0} - SSL mysqlrplcheck "
                   "NEW Master after demote".format(test_num))
        cmd_opts = "--slave={0} --show-slave-status".format(slave3_conn)
        cmds = "{0} {1}".format(cmd_str, cmd_opts)
        res = self.run_test_case(0, cmds, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        self.results.append("\n")

        self.mask_results()
        return True

    def mask_results(self):
        """Mask out non-deterministic data
        """
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
        self.remove_result("            Master_TLS_Version :")

        self.remove_result_and_lines_after("         Seconds_Behind_Master :",
                                           16)
        self.remove_result_and_lines_after("            Retrieved_Gtid_Set :",
                                           3)

        self.remove_result("          Replicate_Rewrite_DB :")

        # Remove slave_master_info data available for servers starting 5.7.6.
        self.remove_result("                  Channel_Name :")
        self.remove_result("            Master_TLS_Version :")

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        # Kill the servers that are only for this test.
        kill_list = ['rep_master_gtid_ssl',
                     'rep_slave1_gtid_ssl',
                     'rep_slave2_gtid_ssl',
                     'rep_slave3_gtid_ssl']
        self.kill_server_list(kill_list)
        return True
