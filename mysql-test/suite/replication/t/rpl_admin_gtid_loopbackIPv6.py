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
from mutlib import *
import rpl_admin
from mysql.utilities.exception import MUTLibError

_IPv6_LOOPBACK = "::1"

_DEFAULT_MYSQL_OPTS = ('"--log-bin=mysql-bin --skip-slave-start '
                      '--log-slave-updates --gtid-mode=on '
                      '--enforce-gtid-consistency --report-host=%s '
                      '--report-port=%s --bind-address=:: '
                      '--master-info-repository=table"')


class test(rpl_admin.test):
    """test replication administration commands
    This test runs the mysqlrpladmin utility on a known topology with
    loopback address (127.0.0.1).

    Note: this test requires GTID enabled servers.
    """

    def check_prerequisites(self):
        if not self.servers.get_server(0).check_version_compat(5, 6, 9):
            raise MUTLibError("Test requires server version 5.6.9")
        return self.check_num_servers(1)

    def setup(self):
        self.res_fname = "result.txt"

        # Spawn servers
        # Retrieved mutlib.HOST value: {0}'.format(mutlib.HOST) #localhost
        self.old_mutlib_HOST = mutlib.HOST
        mutlib.HOST = _IPv6_LOOPBACK
        # Setting mutlib.HOST to: {0}'.format(mutlib.HOST) #127.0.0.1
        self.server0 = self.servers.get_server(0)
        mysqld = _DEFAULT_MYSQL_OPTS % (_IPv6_LOOPBACK,
                                        self.servers.view_next_port())
        self.server1 = self.spawn_server("rep_master_gtid_loopback_ipv6",
                                         mysqld, True)
        mysqld = _DEFAULT_MYSQL_OPTS % (_IPv6_LOOPBACK,
                                        self.servers.view_next_port())
        self.server2 = self.spawn_server("rep_slave1_gtid_loopback_ipv6",
                                         mysqld, True)
        mysqld = _DEFAULT_MYSQL_OPTS % (_IPv6_LOOPBACK,
                                        self.servers.view_next_port())
        self.server3 = self.spawn_server("rep_slave2_gtid_loopback_ipv6",
                                         mysqld, True)
        mysqld = _DEFAULT_MYSQL_OPTS % (_IPv6_LOOPBACK,
                                        self.servers.view_next_port())
        self.server4 = self.spawn_server("rep_slave3_gtid_loopback_ipv6",
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
        res = self.run_test_case(0, "%s %s" % (cmd_str, "".join(cmd_opts)),
                                 comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        test_num += 1
        comment = ("Test case {0} - loopback ([::1]) "
                   "switchover demote-master ".format(test_num))
        slaves = ",".join([slave1_conn, slave2_conn, slave3_conn])
        cmd_str = "mysqlrpladmin.py --master=%s " % master_conn
        cmd_opts = [" --new-master=%s  " % slave1_conn,]
        cmd_opts.append("--discover-slaves=%s " % master_conn.split('@')[0])
        cmd_opts.append("--rpl-user=rpluser:hispassword ")
        cmd_opts.append("--demote-master switchover")
        res = self.run_test_case(0, "%s %s" % (cmd_str, "".join(cmd_opts)),
                                 comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        self.results.append("\n")

        test_num += 1
        comment = ("Test case {0} - mysqlrplshow "
                   "NEW Master after demote".format(test_num))
        cmd_str = "mysqlrplshow.py --master=%s " % slave1_conn
        cmd_opts = ["--discover-slaves=%s " % master_conn.split('@')[0]]
        res = self.run_test_case(0, "%s %s" % (cmd_str, "".join(cmd_opts)),
                                 comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        test_num += 1
        comment = ("Test case {0} - mysqlrplcheck "
                   "NEW Master after demote".format(test_num))
        cmd_str = "mysqlrplcheck.py --master=%s " % slave1_conn
        cmd_opts = ["--slave=%s " % master_conn]
        res = self.run_test_case(0, "%s %s" % (cmd_str, "".join(cmd_opts)),
                                 comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        self.results.append("\n")

        test_num += 1
        comment = ("Test case {0} - loopback "
                   "([::1]) failover ".format(test_num))
        cmd_str = "mysqlrpladmin.py "#--master=%s " % slave1_conn
        slaves = ",".join([slave2_conn, slave3_conn,
                           master_conn])
        cmd_opts = [" --slaves={0} ".format(slaves)]
        cmd_opts.append("--rpl-user=rpluser:hispassword ")
        cmd_opts.append("failover ")
        res = self.run_test_case(0, "%s %s" % (cmd_str, "".join(cmd_opts)),
                                 comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        self.results.append("\n")

        test_num += 1
        comment = ("Test case {0} - mysqlrplshow "
                   "NEW Master after failover".format(test_num))
        cmd_str = "mysqlrplshow.py --master=%s " % slave2_conn
        cmd_opts = ["--discover-slaves=%s " % master_conn.split('@')[0]]
        res = self.run_test_case(0, "%s %s" % (cmd_str, "".join(cmd_opts)),
                                 comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        # Mask out non-deterministic data
        rpl_admin.test.do_masks(self)

        self.replace_result("# QUERY = SELECT "
                            "WAIT_UNTIL_SQL_THREAD_AFTER_GTIDS(",
                            "# QUERY = SELECT "
                            "WAIT_UNTIL_SQL_THREAD_AFTER_GTIDS(XXXXX)\n")
        #self.replace_substring("localhost", "XXXXXXXXX")

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

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        # Restoring mutlib.HOST value to: {0}'.format(self.old_mutlib_HOST)
        mutlib.HOST = self.old_mutlib_HOST
        # Kill the servers that are only for this test.
        self.servers.stop_server(self.server1)
        self.servers.stop_server(self.server2)
        self.servers.stop_server(self.server3)
        self.servers.stop_server(self.server4)
        return rpl_admin.test.cleanup(self)

