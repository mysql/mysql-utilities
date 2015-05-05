#
# Copyright (c) 2010, 2014, Oracle and/or its affiliates. All rights reserved.
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
rpl_admin_warnings test.
"""

import rpl_admin

from mysql.utilities.exception import MUTLibError


_DEFAULT_MYSQL_OPTS = ' '.join(['"--log-bin=mysql-bin',
                                '--log-slave-updates',
                                '--gtid-mode=on',
                                '--enforce-gtid-consistency',
                                '--report-host=localhost',
                                '--report-port={report_port}',
                                '--sync-master-info=1',
                                '--master-info-repository=table"'])

_MYSQL_OPTS_NO_REPORT = ' '.join(['"--log-bin=mysql-bin',
                                  '--log-slave-updates',
                                  '--gtid-mode=on',
                                  '--enforce-gtid-consistency',
                                  '--sync-master-info=1',
                                  '--master-info-repository=table"'])

_MYSQL_OPTS_GTID_OFF = ' '.join(['"--log-bin=mysql-bin',
                                 '--skip-slave-start',
                                 '--log-slave-updates',
                                 '--gtid-mode=off',
                                 '--enforce-gtid-consistency',
                                 '--report-host=localhost',
                                 '--report-port={report_port}',
                                 '--sync-master-info=1',
                                 '--master-info-repository=table"'])

_GRANT_QUERY = ("GRANT REPLICATION SLAVE ON *.* TO 'rpl'@'localhost' "
                "IDENTIFIED BY 'rpl'")
_SET_SQL_LOG_BIN = "SET SQL_LOG_BIN = {0}"


class test(rpl_admin.test):
    """test replication administration commands
    This test exercises the mysqlrpladmin utility warnings concerning options.
    It uses the rpl_admin test for setup and teardown methods.
    """

    server5 = None
    server6 = None
    server7 = None

    def check_prerequisites(self):
        if not self.servers.get_server(0).check_version_compat(5, 6, 9):
            raise MUTLibError("Test requires server version 5.6.9 or higher")
        return self.check_num_servers(1)

    def setup(self):
        self.res_fname = "result.txt"

        # Spawn servers
        self.server0 = self.servers.get_server(0)
        srv_port = self.servers.view_next_port()
        mysqld = _DEFAULT_MYSQL_OPTS.format(report_port=srv_port)
        self.server1 = self.servers.spawn_server("rep_master_gtid", mysqld,
                                                 True)
        srv_port = self.servers.view_next_port()
        mysqld = _DEFAULT_MYSQL_OPTS.format(report_port=srv_port)
        self.server2 = self.servers.spawn_server("rep_slave1_gtid", mysqld,
                                                 True)
        srv_port = self.servers.view_next_port()
        mysqld = _DEFAULT_MYSQL_OPTS.format(report_port=srv_port)
        self.server3 = self.servers.spawn_server("rep_slave2_gtid", mysqld,
                                                 True)
        srv_port = self.servers.view_next_port()
        mysqld = _DEFAULT_MYSQL_OPTS.format(report_port=srv_port)
        self.server4 = self.servers.spawn_server("rep_slave3_gtid", mysqld,
                                                 True)
        # Server without --report-host and --report-port
        mysqld = _MYSQL_OPTS_NO_REPORT
        self.server5 = self.servers.spawn_server("rep_slave4_gtid", mysqld,
                                                 True)
        # Master --gtid-mode=off
        srv_port = self.servers.view_next_port()
        mysqld = _MYSQL_OPTS_GTID_OFF.format(report_port=srv_port)
        self.server6 = self.servers.spawn_server("rep_master_gtid_off", mysqld,
                                                 True)
        # Slave --gtid-mode=off
        srv_port = self.servers.view_next_port()
        mysqld = _MYSQL_OPTS_GTID_OFF.format(report_port=srv_port)
        self.server7 = self.servers.spawn_server("rep_slave_gtid_off", mysqld,
                                                 True)

        # Reset spawned servers (clear binary log and GTID_EXECUTED set)
        self.reset_master([self.server1, self.server2, self.server3,
                           self.server4, self.server5, self.server6,
                           self.server7])

        self.m_port = self.server1.port
        self.s1_port = self.server2.port
        self.s2_port = self.server3.port
        self.s3_port = self.server4.port

        # Set the initial replication topology
        self.reset_topology([self.server2, self.server3, self.server4,
                             self.server5])

        return True

    def run(self):
        self.res_fname = "result.txt"

        master_conn = self.build_connection_string(self.server1).strip(' ')
        slave1_conn = self.build_connection_string(self.server2).strip(' ')
        slave2_conn = self.build_connection_string(self.server3).strip(' ')
        slave3_conn = self.build_connection_string(self.server4).strip(' ')

        master_str = "--master={0}".format(master_conn)
        slaves_str = "--slaves={0}".format(
            ",".join([slave1_conn, slave2_conn, slave3_conn]))
        candidates_str = "--candidates={0}".format(
            ",".join([slave1_conn, slave2_conn, slave3_conn]))

        test_num = 1
        comment = ("Test case {0} - warning for --exec* and not switchover or "
                   "failover".format(test_num))
        cmd_str = ("mysqlrpladmin.py {0} {1} health --quiet --format=csv "
                   " --exec-before=dummy "
                   "--exec-after=dummy".format(master_str, slaves_str))
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - warning for --candidate and not "
                   "switchover".format(test_num))
        cmd_str = ("mysqlrpladmin.py {0} {1} health --quiet --format=csv "
                   "{2}".format(master_str, slaves_str, candidates_str))
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - warning for --new-master and not "
                   "switchover".format(test_num))
        cmd_str = ("mysqlrpladmin.py {0} {1} health --quiet --format=tab "
                   " --new-master={2} ".format(master_str, slaves_str,
                                               slave2_conn))
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - warning for missing "
                   "--report-host".format(test_num))
        cmd_str = ("mysqlrpladmin.py {0} --disco=root:root health "
                   "--format=csv ".format(master_str))
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - warning for missing "
                   "--report-host (using --verbose)".format(test_num))
        cmd_str = ("mysqlrpladmin.py {0} --disco=root:root health "
                   "--format=csv --verbose".format(master_str))
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - warning for --format and not health or "
                   "gtid".format(test_num))
        cmd_str = ("mysqlrpladmin.py {0} {1} stop --quiet "
                   "--format=tab ".format(master_str, slaves_str))
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Reset the topology to its original state
        self.reset_topology([self.server2, self.server3, self.server4,
                             self.server5])

        test_num += 1
        comment = ("Test case {0} - warning for --master and "
                   "failover".format(test_num))
        cmd_str = ("mysqlrpladmin.py {0} {1} "
                   "failover".format(master_str, slaves_str))
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Reset the topology to its original state
        self.reset_topology([self.server2, self.server3, self.server4,
                             self.server5])

        test_num += 1
        comment = ("Test case {0} - warnings for switchover with offline "
                   "slave".format(test_num))
        off_slaves_str = ",".join([slave2_conn, slave3_conn,
                                   "root@offline:1234"])
        cmd_str = ("mysqlrpladmin.py --master={0} --new-master={1} --slaves="
                   "{2} switchover ".format(master_conn, slave1_conn,
                                            off_slaves_str))
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Reset the topology, using a slave with GTID_MODE=OFF
        self.reset_topology([self.server2, self.server3, self.server4,
                             self.server5, self.server7])

        test_num += 1
        comment = ("Test case {0} - elect using a slave with "
                   "gtid disabled.".format(test_num))
        slave4_conn = self.build_connection_string(self.server7).strip(' ')
        slaves_str = ",".join([slave1_conn, slave2_conn, slave3_conn,
                               slave4_conn])
        cmd_str = ("mysqlrpladmin.py --master={0} --slaves={1} "
                   "elect".format(master_conn, slaves_str))
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Reset the topology, using a master with GTID_MODE=OFF
        self.reset_topology([self.server2, self.server3, self.server4,
                             self.server5], master=self.server6)

        test_num += 1
        comment = ("Test case {0} - elect using a master with "
                   "gtid disabled.".format(test_num))
        master2_conn = self.build_connection_string(self.server6).strip(' ')
        slaves_str = ",".join([slave1_conn, slave2_conn, slave3_conn])
        cmd_str = ("mysqlrpladmin.py --master={0} --slaves={1} "
                   "elect".format(master2_conn, slaves_str))
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Reset the topology to its original state for other tests
        self.reset_topology([self.server2, self.server3, self.server4,
                             self.server5])

        # Mask out non-deterministic data
        rpl_admin.test.do_masks(self)

        # Mask server port.
        self.replace_substring(str(self.server5.port), "PORT5")

        # Mask slaves behind master.
        # It happens sometimes on windows in a non-deterministic way.
        self.replace_substring("+--------------------------------------------"
                               "--+", "+---------------------------+")
        self.replace_substring("| health                                     "
                               "  |", "| health                    |")
        self.replace_substring("| OK                                         "
                               "  |", "| OK                        |")
        self.replace_substring("| Slave delay is 1 seconds behind master., "
                               "No  |", "| OK                        |")
        self.replace_substring("| Cannot connect to slave.                   "
                               "  |", "| Cannot connect to slave.  |")

        # Mask verbose health report.
        self.replace_result("localhost,PORT1,MASTER,UP,ON,OK,",
                            "localhost,PORT1,MASTER,UP,ON,OK, ...\n")
        self.replace_result("localhost,PORT2,SLAVE,UP,ON,OK,",
                            "localhost,PORT2,SLAVE,UP,ON,OK, ...\n")
        self.replace_result("localhost,PORT3,SLAVE,UP,ON,OK,",
                            "localhost,PORT3,SLAVE,UP,ON,OK, ...\n")
        self.replace_result("localhost,PORT4,SLAVE,UP,ON,OK,",
                            "localhost,PORT4,SLAVE,UP,ON,OK, ...\n")

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        kill_list = ['rep_master_gtid', 'rep_slave1_gtid', 'rep_slave2_gtid',
                     'rep_slave3_gtid', 'rep_slave4_gtid',
                     'rep_master_gtid_off', 'rep_slave_gtid_off']
        return (rpl_admin.test.cleanup(self)
                and self.kill_server_list(kill_list))
