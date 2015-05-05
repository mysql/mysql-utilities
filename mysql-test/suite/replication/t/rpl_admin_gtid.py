#
# Copyright (c) 2010, 2015, Oracle and/or its affiliates. All rights reserved.
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
rpl_admin_gtid test.
"""

import mutlib
import rpl_admin

from mysql.utilities.exception import MUTLibError, UtilDBError


_DEFAULT_MYSQL_OPTS = ('"--log-bin=mysql-bin --skip-slave-start '
                       '--log-slave-updates --gtid-mode=on '
                       '--enforce-gtid-consistency --report-host=localhost '
                       '--report-port={port} '
                       '--sync-master-info=1 --master-info-repository=table"')

_DEFAULT_MYSQL_OPTS_FILE = ('"--log-bin=mysql-bin --skip-slave-start '
                            '--log-slave-updates --gtid-mode=on '
                            '--enforce-gtid-consistency '
                            '--report-host=localhost --report-port={port} '
                            '--sync-master-info=1 '
                            '--master-info-repository=file"')

_MYSQL_OPTS_INFO_REPO_TABLE = ('"--log-bin=mysql-bin --skip-slave-start '
                               '--log-slave-updates --gtid-mode=ON '
                               '--enforce-gtid-consistency '
                               '--report-host=localhost --report-port={port} '
                               '--sync-master-info=1 '
                               '--master-info-repository=TABLE '
                               '--relay-log-info-repository=TABLE"')

TIMEOUT = 30


class test(rpl_admin.test):
    """test replication administration commands
    This test runs the mysqlrpladmin utility on a known topology.

    Note: this test requires GTID enabled servers.
    """

    server5 = None
    s4_port = None

    def check_prerequisites(self):
        if not self.servers.get_server(0).check_version_compat(5, 6, 9):
            raise MUTLibError("Test requires server version 5.6.9")
        return self.check_num_servers(1)

    def setup(self):
        self.res_fname = "result.txt"

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

        # Reset spawned servers (clear binary log and GTID_EXECUTED set)
        self.reset_master([self.server1, self.server2, self.server3,
                           self.server4, self.server5])

        self.m_port = self.server1.port
        self.s1_port = self.server2.port
        self.s2_port = self.server3.port
        self.s3_port = self.server4.port
        self.s4_port = self.server5.port

        rpl_admin.test.reset_topology(self)

        return True

    def run(self):

        # As first phase, repeat rpl_admin tests
        phase1 = rpl_admin.test.run(self)
        if not phase1:
            return False

        test_num = 19

        rpl_admin.test.reset_topology(self)

        master_conn = self.build_connection_string(self.server1).strip(' ')
        slave1_conn = self.build_connection_string(self.server2).strip(' ')
        slave2_conn = self.build_connection_string(self.server3).strip(' ')
        slave3_conn = self.build_connection_string(self.server4).strip(' ')
        slave4_conn = self.build_connection_string(self.server5).strip(' ')

        comment = "Test case {0} - elect".format(test_num)
        slaves = ",".join([slave1_conn, slave2_conn, slave3_conn])
        cmd_str = "mysqlrpladmin.py --master={0} ".format(master_conn)
        cmd_opts = " --candidates={0} --slaves={0} elect".format(slaves)
        res = mutlib.System_test.run_test_case(self, 0, cmd_str + cmd_opts,
                                               comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        test_num += 1

        comment = "Test case {0} - gtid".format(test_num)
        slaves = ",".join([slave1_conn, slave2_conn, slave3_conn])
        cmd_str = "mysqlrpladmin.py --master={0} ".format(master_conn)
        cmd_opts = " --slaves={0} gtid --format=csv ".format(slaves)
        res = mutlib.System_test.run_test_case(self, 0, cmd_str + cmd_opts,
                                               comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        test_num += 1

        # Remove GTIDs here because they are not deterministic when run with
        # other tests that reuse these servers.
        self.remove_result("localhost,{0},MASTER,".format(self.m_port))
        self.remove_result("localhost,{0},SLAVE,".format(self.s1_port))
        self.remove_result("localhost,{0},SLAVE,".format(self.s2_port))
        self.remove_result("localhost,{0},SLAVE,".format(self.s3_port))

        comment = "Test case {0} - heatlh with discover".format(test_num)
        slaves = ",".join([slave1_conn, slave2_conn, slave3_conn])
        cmd_str = "mysqlrpladmin.py --master={0} ".format(master_conn)
        cmd_opts = " --discover-slaves-login=root:root health --format=csv "
        res = mutlib.System_test.run_test_case(self, 0, cmd_str + cmd_opts,
                                               comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        test_num += 1

        comment = "Test case {0} - failover to {1}:{2}".format(
            test_num, self.server4.host, self.server4.port)
        slaves = ",".join(["root:root@127.0.0.1:{0}".format(self.server2.port),
                           slave2_conn, slave3_conn])
        cmd_str = "mysqlrpladmin.py "
        cmd_opts = " --candidates={0}  --slaves={1} failover".format(
            slave3_conn, slaves)
        res = mutlib.System_test.run_test_case(self, 0, cmd_str + cmd_opts,
                                               comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        test_num += 1

        slaves = ",".join([slave1_conn, slave2_conn])
        cmd_str = "mysqlrpladmin.py --master={0} ".format(slave3_conn)
        comment = "Test case {0} - show health after failover".format(test_num)
        cmd_opts = " --slaves={0} --format=vertical health".format(slaves)
        res = mutlib.System_test.run_test_case(self, 0, cmd_str + cmd_opts,
                                               comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        test_num += 1

        # Test for BUG#14080657
        # Note: disable binary logging to avoid creating errant transactions.
        self.server2.exec_query("SET SQL_LOG_BIN= 0")
        self.server2.exec_query("CREATE USER 'rpl'@'rpl'")
        self.server2.exec_query("GRANT REPLICATION SLAVE ON *.* TO "
                                "'rpl'@'rpl'")
        self.server2.exec_query("SET SQL_LOG_BIN= 1")

        cmd_str = "mysqlrpladmin.py --master={0} ".format(slave3_conn)
        comment = "Test case {0} - elect with missing rpl user".format(
            test_num)
        cmd_opts = " --slaves={0} elect -vvv --candidates={1} ".format(
            slaves, slave1_conn)
        res = mutlib.System_test.run_test_case(self, 0, cmd_str + cmd_opts,
                                               comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        test_num += 1

        # Now we return the topology to its original state for other tests
        rpl_admin.test.reset_topology(self)

        # Add server5 to the topology
        conn_str = " --slave={0}{1}".format(
            self.build_connection_string(self.server5), self.master_str)
        cmd = "mysqlreplicate.py --rpl-user=rpl:rpl {0}".format(conn_str)
        res = self.exec_util(cmd, self.res_fname)
        if res != 0:
            return False

        comment = ("Test case {0} - mix FILE/TABLE and missing "
                   "--rpl-user".format(test_num))
        cmd_str = "mysqlrpladmin.py --master={0} ".format(master_conn)
        cmd_opts = (" --discover-slaves-login=root:root switchover "
                    "--new-master=root:root@localhost:{0}"
                    "".format(self.s4_port))
        res = mutlib.System_test.run_test_case(self, 1, cmd_str + cmd_opts,
                                               comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        test_num += 1

        comment = "Test case {0} - mix FILE/TABLE and --rpl-user".format(
            test_num)
        cmd_str = "mysqlrpladmin.py --master={0} ".format(master_conn)
        cmd_opts = (" --discover-slaves-login=root:root switchover "
                    "--new-master=root:root@localhost:{0} "
                    "--rpl-user=rpl:rpl ".format(self.s4_port))
        res = mutlib.System_test.run_test_case(self, 0, cmd_str + cmd_opts,
                                               comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        test_num += 1

        # Now we return the topology to its original state for other tests
        rpl_admin.test.reset_topology(self)

        self.server5.exec_query("STOP SLAVE")
        self.server5.exec_query("RESET SLAVE")

        # Test for BUG#16571812
        comment = "Test case {0} - slave not part of topology".format(test_num)
        slaves = ",".join([slave1_conn, slave2_conn, slave3_conn, slave4_conn])
        candidates = ",".join([slave1_conn, slave2_conn, slave3_conn])
        cmd_str = " ".join(["mysqlrpladmin.py", "failover", "--force",
                            "--candidates={0}".format(candidates), "--quiet",
                            "--slaves={0}".format(slaves),
                            "--rpl-user=rpl:rpl"])
        res = mutlib.System_test.run_test_case(self, 0, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        test_num += 1

        # Test for BUG#16554609 and BUG#18083550
        comment = ("Test case {0} - HEALTH with some transactions "
                   "behind".format(test_num))
        cmd_str = ("mysqlrpladmin.py --master={0} --slaves={1} health "
                   "--format=VERTICAL -vvv".format(master_conn, slave1_conn))

        # Reset the topology to its original state
        self.reset_topology()

        # Get master uuid
        master_uuid = self.server1.get_uuid()

        # STOP the slaves, purge binlogs and reset gtid_executed on both
        # master and slave2 and reset all the slaves
        self.stop_slaves()
        self.reset_master([self.server1, self.server2])
        self.reset_slaves()

        # set of transactions to skip on slave
        slave_skip_trx = set([3, 5, 7, 12])
        LAST_GTID = 21
        for i in range(1, LAST_GTID + 1):
            automatic = True if i == LAST_GTID else False
            # inject transaction on master
            gtid = "{0}:{1}".format(master_uuid, i)
            self.server1.inject_empty_trx(gtid, automatic)
            # check it transaction should be skipped
            if i not in slave_skip_trx:
                self.server2.inject_empty_trx(gtid, automatic)

        # Run the test
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Now we return the topology to its original state for other tests
        self.reset_topology()

        # Mask out non-deterministic data
        rpl_admin.test.do_masks(self)
        self.replace_substring(str(self.s4_port), "PORT5")

        # Mask data from verbose health report (except Trans_Behind)
        self.replace_result("         version: ",
                            "         version: XX.XX.XX\n")
        self.replace_result(" master_log_file: ",
                            " master_log_file: XXXXX.XXXX\n")
        self.replace_result("  master_log_pos: ",
                            "  master_log_pos: XXXX\n")
        self.replace_result("     Secs_Behind: ",
                            "     Secs_Behind: X\n")
        self.replace_result(" Remaining_Delay: ",
                            " Remaining_Delay: XXX\n")

        # Mask slaves behind master.
        # It happens sometimes on windows in a non-deterministic way.
        self.replace_result("    health: Slave delay is ",
                            "    health: OK")
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

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        # Kill all spawned servers.
        self.kill_server_list(
            ['rep_master_gtid', 'rep_slave1_gtid', 'rep_slave2_gtid',
             'rep_slave3_gtid', 'rep_slave4_gtid']
        )
        return rpl_admin.test.cleanup(self)
