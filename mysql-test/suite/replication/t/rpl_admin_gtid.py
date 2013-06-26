#
# Copyright (c) 2010, 2013, Oracle and/or its affiliates. All rights reserved.
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

class test(rpl_admin.test):
    """test replication administration commands
    This test runs the mysqlrpladmin utility on a known topology.

    Note: this test requires GTID enabled servers.
    """

    def check_prerequisites(self):
        if not self.servers.get_server(0).check_version_compat(5, 6, 9):
            raise MUTLibError("Test requires server version 5.6.9")
        return self.check_num_servers(1)

    def setup(self):
        self.res_fname = "result.txt"

        # Spawn servers
        self.server0 = self.servers.get_server(0)
        mysqld = _DEFAULT_MYSQL_OPTS.format(port=self.servers.view_next_port())
        self.server1 = self.spawn_server("rep_master_gtid", mysqld, True)
        mysqld = _DEFAULT_MYSQL_OPTS.format(port=self.servers.view_next_port())
        self.server2 = self.spawn_server("rep_slave1_gtid", mysqld, True)
        mysqld = _DEFAULT_MYSQL_OPTS.format(port=self.servers.view_next_port())
        self.server3 = self.spawn_server("rep_slave2_gtid", mysqld, True)
        # Spawn server with --master-info-repository=TABLE and
        # --relay-log-info-repository=TABLE.
        mysqld = _MYSQL_OPTS_INFO_REPO_TABLE.format(
            port=self.servers.view_next_port()
        )
        self.server4 = self.spawn_server("rep_slave3_gtid", mysqld, True)
        # Spawn a server with MIR=FILE
        mysqld = _DEFAULT_MYSQL_OPTS_FILE.format(
            port=self.servers.view_next_port()
        )
        self.server5 = self.spawn_server("rep_slave4_gtid", mysqld, True)

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

        comment = "Test case %s - elect" % test_num
        slaves = ",".join([slave1_conn, slave2_conn, slave3_conn])
        cmd_str = "mysqlrpladmin.py --master=%s " % master_conn
        cmd_opts = " --candidates=%s  " % slaves
        cmd_opts += " --slaves=%s elect" % slaves
        res = mutlib.System_test.run_test_case(self, 0, cmd_str+cmd_opts,
                                               comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        test_num += 1

        comment = "Test case %s - gtid" % test_num
        slaves = ",".join([slave1_conn, slave2_conn, slave3_conn])
        cmd_str = "mysqlrpladmin.py --master=%s " % master_conn
        cmd_opts = " --slaves=%s gtid --format=csv " % slaves
        res = mutlib.System_test.run_test_case(self, 0, cmd_str+cmd_opts,
                                               comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        test_num += 1

        # Remove GTIDs here because they are not deterministic when run with
        # other tests that reuse these servers.
        self.remove_result("localhost,%s,MASTER," % self.m_port)
        self.remove_result("localhost,%s,SLAVE," % self.s1_port)
        self.remove_result("localhost,%s,SLAVE," % self.s2_port)
        self.remove_result("localhost,%s,SLAVE," % self.s3_port)

        comment = "Test case %s - heatlh with discover" % test_num
        slaves = ",".join([slave1_conn, slave2_conn, slave3_conn])
        cmd_str = "mysqlrpladmin.py --master=%s " % master_conn
        cmd_opts = " --discover-slaves-login=root:root health --format=csv "
        res = mutlib.System_test.run_test_case(self, 0, cmd_str+cmd_opts,
                                               comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        test_num += 1

        comment = "Test case %s - failover to %s:%s" % \
                  (test_num, self.server4.host, self.server4.port)
        slaves = ",".join(["root:root@127.0.0.1:%s" % self.server2.port,
                           slave2_conn, slave3_conn])
        cmd_str = "mysqlrpladmin.py "
        cmd_opts = " --candidates=%s  " % slave3_conn
        cmd_opts += " --slaves=%s failover" % slaves
        res = mutlib.System_test.run_test_case(self, 0, cmd_str+cmd_opts,
                                               comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        test_num += 1

        slaves = ",".join([slave1_conn, slave2_conn])
        cmd_str = "mysqlrpladmin.py --master=%s " % slave3_conn
        comment = "Test case %s - show health after failover" % test_num
        cmd_opts = " --slaves=%s --format=vertical health" % slaves
        res = mutlib.System_test.run_test_case(self, 0, cmd_str+cmd_opts,
                                               comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        test_num += 1

        # Test for BUG#14080657
        self.server2.exec_query("GRANT REPLICATION SLAVE ON *.* TO 'rpl'@'rpl'")

        cmd_str = "mysqlrpladmin.py --master=%s " % slave3_conn
        comment = "Test case %s - elect with missing rpl user" % test_num
        cmd_opts = " --slaves=%s elect -vvv --candidates=%s " % \
                   (slaves, slave1_conn)
        res = mutlib.System_test.run_test_case(self, 0, cmd_str+cmd_opts,
                                               comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        test_num += 1

        # Now we return the topology to its original state for other tests
        rpl_admin.test.reset_topology(self)

        # Add server5 to the topology
        conn_str = " --slave=%s" % self.build_connection_string(self.server5)
        conn_str += self.master_str
        cmd = "mysqlreplicate.py --rpl-user=rpl:rpl %s" % conn_str
        res = self.exec_util(cmd, self.res_fname)
        if res != 0:
            return False

        comment = "Test case %s - mix FILE/TABLE and missing --rpl-user" % test_num
        slaves = ",".join([slave1_conn, slave2_conn, slave3_conn, slave4_conn])
        cmd_str = "mysqlrpladmin.py --master=%s " % master_conn
        cmd_opts = " --discover-slaves-login=root:root switchover "
        cmd_opts += "--new-master=root:root@localhost:%s " % self.s4_port
        res = mutlib.System_test.run_test_case(self, 1, cmd_str+cmd_opts,
                                               comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        test_num += 1

        comment = "Test case %s - mix FILE/TABLE and --rpl-user" % test_num
        slaves = ",".join([slave1_conn, slave2_conn, slave3_conn, slave4_conn])
        cmd_str = "mysqlrpladmin.py --master=%s " % master_conn
        cmd_opts = " --discover-slaves-login=root:root switchover "
        cmd_opts += "--new-master=root:root@localhost:%s " % self.s4_port
        cmd_opts += " --rpl-user=rpl:rpl "
        res = mutlib.System_test.run_test_case(self, 0, cmd_str+cmd_opts,
                                               comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        test_num += 1

        # Now we return the topology to its original state for other tests
        rpl_admin.test.reset_topology(self)

        self.server5.exec_query("STOP SLAVE")
        self.server5.exec_query("RESET SLAVE")

        # Test for BUG#16571812
        comment = "Test case %s - slave not part of topology" % test_num
        slaves = ",".join([slave1_conn, slave2_conn, slave3_conn, slave4_conn])
        candidates = ",".join([slave1_conn, slave2_conn, slave3_conn])
        cmd_str = " ".join(["mysqlrpladmin.py", "failover", "--force",
                            "--candidates=%s" % candidates, "--quiet",
                            "--slaves=%s" % slaves, "--rpl-user=rpl:rpl"])
        res = mutlib.System_test.run_test_case(self, 0, cmd_str, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        test_num += 1

        # Reset the topology to its original state
        self.reset_topology()

        # Test if the correct number of transactions behind is displayed.
        # STOP the slave (not to catch up with the master.
        self.server2.exec_query("STOP SLAVE SQL_THREAD")
        # Add 3 transactions to the master.
        self.server1.exec_query("CREATE DATABASE `trx_behind`")
        self.server1.exec_query("CREATE TABLE `trx_behind`.`t1` (x char(30))")
        self.server1.exec_query("DROP DATABASE `trx_behind`")

        comment = ("Test case {0} - HEALTH with some transactions "
                   "behind").format(test_num)
        cmd_str = ("mysqlrpladmin.py --master={0} --slaves={1} health "
                   "--format=VERTICAL -vvv").format(master_conn, slave1_conn)
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Now we return the topology to its original state for other tests
        self.reset_topology()

        # Mask out non-deterministic data
        rpl_admin.test.do_masks(self)
        self.replace_substring(str(self.s4_port), "PORT5")

        self.replace_result("#  - For slave 'localhost",
                            "#  - For slave 'localhost@PORT?': XXXXX\n")

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
        self.replace_substring("+--------------------------------------------"
                               "--+", "+---------+")
        self.replace_substring("| health                                     "
                               "  |", "| health  |")
        self.replace_substring("| OK                                         "
                               "  |", "| OK      |")
        self.replace_substring("| Slave delay is 1 seconds behind master., "
                               "No  |", "| OK      |")
        self.replace_substring("+----------------------------------------------"
                               "-----------------------------------------+",
                               "+---------+")
        self.replace_substring("| health                                       "
                               "                                         |",
                               "| health  |")
        self.replace_substring("| OK                                           "
                               "                                         |",
                               "| OK      |")
        self.replace_substring("| Slave delay is 1 seconds behind master., No, "
                               "Slave has 1 transactions behind master.  |",
                               "| OK      |")

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        return rpl_admin.test.cleanup(self)
