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

"""
rpl_admin_failover_error test.
"""

import os

import rpl_admin

from mysql.utilities.exception import MUTLibError
from mysql.utilities.exception import UtilError


_DEFAULT_MYSQL_OPTS = ' '.join(['"--log-bin=mysql-bin',
                                '--skip-slave-start',
                                '--log-slave-updates',
                                '--gtid-mode=on',
                                '--enforce-gtid-consistency',
                                '--report-host=localhost',
                                '--report-port={0}',
                                '--sync-master-info=1',
                                '--master-info-repository=table"'])

_MYSQL_OPTS_GTID_OFF = ' '.join(['"--log-bin=mysql-bin',
                                 '--skip-slave-start',
                                 '--log-slave-updates',
                                 '--gtid-mode=off',
                                 '--enforce-gtid-consistency',
                                 '--report-host=localhost',
                                 '--report-port={0}',
                                 '--sync-master-info=1',
                                 '--master-info-repository=table"'])

_GTID_WAIT = "SELECT WAIT_UNTIL_SQL_THREAD_AFTER_GTIDS('{0}', {1})"

_SET_SQL_LOG_BIN = "SET SQL_LOG_BIN = {0}"

_LOGNAME = "temp_log.txt"


class test(rpl_admin.test):
    """Test replication administration command - failover
    This test runs the mysqlrpladmin utility on a known topology, and check
    the slaves status for the existence of SQL errors (prior to the failover
    operation). It also test other errors for the failover command.

    Note: this test requires GTID enabled servers.
    """

    master_conn = None
    slave1_conn = None
    slave2_conn = None
    slave3_conn = None
    slave4_conn = None
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
        mysqld = _DEFAULT_MYSQL_OPTS.format(self.servers.view_next_port())
        self.server1 = self.spawn_server("rep_master_gtid", mysqld, True)
        mysqld = _DEFAULT_MYSQL_OPTS.format(self.servers.view_next_port())
        self.server2 = self.spawn_server("rep_slave1_gtid", mysqld, True)
        mysqld = _DEFAULT_MYSQL_OPTS.format(self.servers.view_next_port())
        self.server3 = self.spawn_server("rep_slave2_gtid", mysqld, True)
        mysqld = _DEFAULT_MYSQL_OPTS.format(self.servers.view_next_port())
        self.server4 = self.spawn_server("rep_slave3_gtid", mysqld, True)
        mysqld = _MYSQL_OPTS_GTID_OFF.format(self.servers.view_next_port())
        self.server5 = self.spawn_server("rep_slave4_gtid_off", mysqld, True)

        # Reset spawned servers (clear binary log and GTID_EXECUTED set)
        self.reset_master()

        self.m_port = self.server1.port
        self.s1_port = self.server2.port
        self.s2_port = self.server3.port
        self.s3_port = self.server4.port
        self.s4_port = self.server5.port

        # Set the initial replication topology
        rpl_admin.test.reset_topology(self, [self.server2, self.server3,
                                             self.server4, self.server5])

        build_str = self.build_connection_string
        self.master_conn = build_str(self.server1).strip(' ')
        self.slave1_conn = build_str(self.server2).strip(' ')
        self.slave2_conn = build_str(self.server3).strip(' ')
        self.slave3_conn = build_str(self.server4).strip(' ')
        self.slave4_conn = build_str(self.server5).strip(' ')

        return True

    def run(self):
        # Create a conflicting transaction on server2 and server4, disabling
        # the binary log to avoid being detected as an errant transaction.
        self.server2.exec_query(_SET_SQL_LOG_BIN.format('0'))
        self.server2.exec_query("CREATE DATABASE `conflict_tnx`")
        self.server2.exec_query(_SET_SQL_LOG_BIN.format('1'))
        self.server4.exec_query(_SET_SQL_LOG_BIN.format('0'))
        self.server4.exec_query("CREATE DATABASE `conflict_tnx`")
        self.server4.exec_query(_SET_SQL_LOG_BIN.format('1'))
        # Create same conflicting database on the master to generate an SQL
        # error when replicated
        self.server1.exec_query("CREATE DATABASE `conflict_tnx`")

        # Wait for slaves with conflicting transactions to catch up with
        # the master, ensuring that SQL errors occur.
        self.wait_for_slave(self.server1, self.server2)
        self.wait_for_slave(self.server1, self.server4)

        test_num = 1

        comment = ("Test case {0} - failover to {1}:{2} with SQL errors on "
                   "slaves.".format(test_num, self.server2.host,
                                    self.server2.port))
        slaves = ",".join([self.slave1_conn, self.slave2_conn,
                           self.slave3_conn])
        cmd_str = ("mysqlrpladmin.py --candidates={0} --slaves={1} "
                   "failover -vvv".format(self.slave1_conn, slaves))
        res = self.run_test_case(1, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1

        comment = ("Test case {0} - failover to {1}:{2} with SQL errors on "
                   "slaves --force option.".format(test_num, self.server2.host,
                                                   self.server2.port))
        cmd_str = ("mysqlrpladmin.py --candidates={0} --slaves={1} "
                   "--force failover -vvv --log={2} --log-age=1 "
                   "".format(self.slave1_conn, slaves, _LOGNAME))
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Check log file for error.
        # Now check the log and dump its entries
        log_file = open(_LOGNAME, "r")
        rows = log_file.readlines()
        log_file.close()
        for row in rows:
            if "Problem detected with SQL thread" in row:
                self.results.append("Error found in log file. \n")
                break
        else:
            self.results.append("Error NOT found in the log.\n")
        # log file removed by the cleanup method

        test_num += 1

        slaves = ",".join([self.slave1_conn, self.slave2_conn,
                           self.slave4_conn, self.slave3_conn])
        comment = ("Test case {0} - failover with a slave with "
                   "GTID_MODE=OFF.".format(test_num))
        cmd_str = ("mysqlrpladmin.py --slaves={0} failover".format(slaves))
        res = self.run_test_case(1, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Mask out non-deterministic data
        rpl_admin.test.do_masks(self)
        self.replace_substring(str(self.s4_port), "PORT5")

        # Strip health report - not needed.
        self.remove_result("+-")
        self.remove_result("| ")

        # Strip GTID detailed information
        self.replace_result("# QUERY = SELECT WAIT_UNTIL_SQL_THREAD_AFTER",
                            "# QUERY = SELECT WAIT_UNTIL_SQL_THREAD_AFTER"
                            "_GTIDS(XXXXXXXXX)\n")
        self.replace_result("# Return Code =", "# Return Code = XXX\n")

        self.remove_result("NOTE: Log file")

        return True

    @staticmethod
    def wait_for_slave(master, slave):
        """Waits for slave.

        master[in]     Master instance.
        slave[in]      Slave instance.
        """
        master_gtid = master.exec_query("SELECT @@GLOBAL.GTID_EXECUTED")
        master_gtids = master_gtid[0][0].split('\n')
        for gtid in master_gtids:
            try:
                slave.exec_query(_GTID_WAIT.format(gtid.strip(','), 20))
            except UtilError as err:
                query = _GTID_WAIT.format(gtid.strip(','), 20)
                raise MUTLibError("Error executing {0}: "
                                  "{1}".format(query, err.errmsg))

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        # Remove log file (here to delete the file even if some test fails)
        try:
            os.unlink(_LOGNAME)
        except OSError:
            pass
        # kill servers that are only used in this test
        kill_list = ['rep_slave4_gtid_off']
        return (rpl_admin.test.cleanup(self)
                and self.kill_server_list(kill_list))
