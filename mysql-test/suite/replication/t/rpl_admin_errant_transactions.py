#
# Copyright (c) 2013, 2014, Oracle and/or its affiliates. All rights reserved.
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

import rpl_admin
from mysql.utilities.exception import MUTLibError

_DEFAULT_MYSQL_OPTS = ' '.join(['"--log-bin=mysql-bin',
                                '--skip-slave-start',
                                '--log-slave-updates',
                                '--gtid-mode=on',
                                '--enforce-gtid-consistency',
                                '--report-host=localhost',
                                '--report-port={report_port}',
                                '--sync-master-info=1',
                                '--master-info-repository=table"'])


class test(rpl_admin.test):
    """Test replication administration command - failover
    This test runs the mysqlrpladmin utility on a known topology, and verifies
    the correct detection of errant transactions.

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
        srv_port = self.servers.view_next_port()
        mysqld = _DEFAULT_MYSQL_OPTS.format(report_port=srv_port)
        self.server1 = self.spawn_server("rep_master_gtid", mysqld, True)
        srv_port = self.servers.view_next_port()
        mysqld = _DEFAULT_MYSQL_OPTS.format(report_port=srv_port)
        self.server2 = self.spawn_server("rep_slave1_gtid", mysqld, True)
        srv_port = self.servers.view_next_port()
        mysqld = _DEFAULT_MYSQL_OPTS.format(report_port=srv_port)
        self.server3 = self.spawn_server("rep_slave2_gtid", mysqld, True)
        srv_port = self.servers.view_next_port()
        mysqld = _DEFAULT_MYSQL_OPTS.format(report_port=srv_port)
        self.server4 = self.spawn_server("rep_slave3_gtid", mysqld, True)

        # Reset spawned servers (clear binary log and GTID_EXECUTED set)
        self.reset_master()

        self.m_port = self.server1.port
        self.s1_port = self.server2.port
        self.s2_port = self.server3.port
        self.s3_port = self.server4.port

        # Set the initial replication topology
        self.reset_topology()

        build_str = self.build_connection_string
        self.master_conn = build_str(self.server1).strip(' ')
        self.slave1_conn = build_str(self.server2).strip(' ')
        self.slave2_conn = build_str(self.server3).strip(' ')
        self.slave3_conn = build_str(self.server4).strip(' ')

        return True

    def run(self):

        test_num = 1

        # Create an errant transaction on server2 and server4
        self.server2.exec_query("CREATE DATABASE `errant_tnx2`")
        self.server4.exec_query("CREATE DATABASE `errant_tnx4`")

        comment = ("Test case {0} - failover to {1}:{2} with errant "
                   "transactions.".format(test_num, self.server2.host,
                                          self.server2.port))
        slaves = ",".join([self.slave1_conn, self.slave2_conn,
                           self.slave3_conn])
        cmd_str = ("mysqlrpladmin.py --candidates={0} --slaves={1} "
                   "failover -vvv".format(self.slave1_conn, slaves))
        res = self.run_test_case(1, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1

        comment = ("Test case {0} - failover to {1}:{2} with errant "
                   "transactions using --force "
                   "option.".format(test_num, self.server2.host,
                                    self.server2.port))
        cmd_str = ("mysqlrpladmin.py --candidates={0} --slaves={1} "
                   "--force failover -vvv".format(self.slave1_conn, slaves))
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Mask out non-deterministic data
        self.do_masks()

        # Strip health report - not needed.
        self.remove_result("+-")
        self.remove_result("| ")

        # Strip GTID detailed information
        self.replace_result("# QUERY = SELECT WAIT_UNTIL_SQL_THREAD_AFTER",
                            "# QUERY = SELECT WAIT_UNTIL_SQL_THREAD_AFTER"
                            "_GTIDS(XXXXXXXXX)\n")
        self.replace_result("# Return Code =", "# Return Code = XXX\n")
        self.replace_result("#  - For slave 'localhost@PORT2':",
                            "#  - For slave 'localhost@PORT2': XXXXXXXXX:1\n")
        self.replace_result("#  - For slave 'localhost@PORT4':",
                            "#  - For slave 'localhost@PORT4': XXXXXXXXX:1\n")

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        # Kill all spawned servers.
        self.kill_server_list(
            ['rep_master_gtid', 'rep_slave1_gtid', 'rep_slave2_gtid',
             'rep_slave3_gtid']
        )

        return rpl_admin.test.cleanup(self)
