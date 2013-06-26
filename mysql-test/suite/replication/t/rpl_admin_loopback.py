#
# Copyright (c) 2013, Oracle and/or its affiliates. All rights reserved.
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

import mutlib
import rpl_admin
from mysql.utilities.exception import MUTLibError

_IPv4_LOOPBACK = "127.0.0.1"

_DEFAULT_MYSQL_OPTS = ('"--log-bin=mysql-bin --skip-slave-start '
                       '--log-slave-updates  '
                       '--report-host=%s '
                       '--report-port=%s --bind-address=0.0.0.0 "')


class test(rpl_admin.test):
    """test replication administration commands
    This test runs the mysqlrpladmin utility on a known topology with
    loopback address (127.0.0.1).
    """

    def check_prerequisites(self):
        # Check if GTID_MODE is disabled (required for this test)
        if self.servers.get_server(0).supports_gtid() == "ON":
            raise MUTLibError("Test requires servers without GTID enabled.")
        return self.check_num_servers(1)

    def setup(self):
        self.res_fname = "result.txt"

        # Spawn servers
        # Change cloning Server_List host value
        self.old_cloning_host = self.servers.cloning_host
        self.servers.cloning_host = _IPv4_LOOPBACK

        self.server0 = self.servers.get_server(0)
        mysqld = _DEFAULT_MYSQL_OPTS % (_IPv4_LOOPBACK,
                                        self.servers.view_next_port())
        self.server1 = self.spawn_server("rep_master_loopback",
                                         mysqld, True)
        mysqld = _DEFAULT_MYSQL_OPTS % (_IPv4_LOOPBACK,
                                        self.servers.view_next_port())
        self.server2 = self.spawn_server("rep_slave1_loopback",
                                         mysqld, True)
        mysqld = _DEFAULT_MYSQL_OPTS % (_IPv4_LOOPBACK,
                                        self.servers.view_next_port())
        self.server3 = self.spawn_server("rep_slave2_loopback",
                                         mysqld, True)
        mysqld = _DEFAULT_MYSQL_OPTS % (_IPv4_LOOPBACK,
                                        self.servers.view_next_port())
        self.server4 = self.spawn_server("rep_slave3_loopback",
                                         mysqld, True)

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

        comment = ("Test case {0} - mysqlrplshow OLD Master "
                   "before demote".format(test_num))
        cmd_str = "mysqlrplshow.py --master=%s " % master_conn
        cmd_opts = ["--discover-slaves=%s " % master_conn.split('@')[0]]
        res = self.run_test_case(0, "%s %s" % (cmd_str,"".join(cmd_opts)),
                                 comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        test_num += 1
        comment = ("Test case {0} - loopback (127.0.0.1) "
                   "switchover demote-master ".format(test_num))
        slaves = ",".join([slave1_conn, slave2_conn, slave3_conn])
        cmd_str = "mysqlrpladmin.py --master=%s " % master_conn
        cmd_opts = [" --new-master=%s  " % slave1_conn,]
        cmd_opts.append("--discover-slaves=%s " % master_conn.split('@')[0])
        cmd_opts.append("--rpl-user=rpl:rpl ")
        cmd_opts.append("--demote-master switchover --force")
        res = self.run_test_case(0, "%s %s" % (cmd_str,"".join(cmd_opts)),
                                 comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        self.results.append("\n")

        test_num += 1
        comment = ("Test case {0} - mysqlrplshow "
                   "NEW Master after demote".format(test_num))
        cmd_str = "mysqlrplshow.py --master=%s " % slave1_conn
        cmd_opts = ["--discover-slaves=%s " % master_conn.split('@')[0]]
        res = self.run_test_case(0, "%s %s" % (cmd_str,"".join(cmd_opts)),
                                 comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        test_num += 1
        comment = ("Test case {0} - mysqlrplcheck "
                   "NEW Master after demote".format(test_num))
        cmd_str = "mysqlrplcheck.py --master=%s " % slave1_conn
        cmd_opts = ["--slave=%s " % master_conn]
        res = self.run_test_case(0, "%s %s" % (cmd_str,"".join(cmd_opts)),
                                 comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        self.results.append("\n")

        # Now we return the topology to its original state for other tests
        rpl_admin.test.reset_topology(self)

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

        self.replace_result("| 127.0.0.1  | PORT2  | MASTER  | UP     "
                            "| OFF        | OK      |",
                            "| 127.0.0.1  | PORT2  | MASTER  | UP     "
                            "| NO         | OK      |\n")
        self.replace_result("| 127.0.0.1  | PORT1  | SLAVE   | UP     "
                            "| OFF        | OK      |",
                            "| 127.0.0.1  | PORT1  | SLAVE   | UP     "
                            "| NO         | OK      |\n")
        self.replace_result("| 127.0.0.1  | PORT3  | SLAVE   | UP     "
                            "| OFF        | OK      |",
                            "| 127.0.0.1  | PORT3  | SLAVE   | UP     "
                            "| NO         | OK      |\n")
        self.replace_result("| 127.0.0.1  | PORT4  | SLAVE   | UP     "
                            "| OFF        | OK      |",
                            "| 127.0.0.1  | PORT4  | SLAVE   | UP     "
                            "| NO         | OK      |\n")

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        # Restoring cloning Server_List host value
        self.servers.cloning_host = self.old_cloning_host
        # Kill the servers that are only for this test.
        kill_list = ['rep_master_loopback', 'rep_slave1_loopback',
                    'rep_slave2_loopback', 'rep_slave3_loopback']
        return (rpl_admin.test.cleanup(self)
                and self.kill_server_list(kill_list))

