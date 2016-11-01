#
# Copyright (c) 2010, 2016, Oracle and/or its affiliates. All rights reserved.
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
rpl_admin test.
"""

import os
import time

import mutlib

from mysql.utilities.exception import MUTLibError, UtilError


_DEFAULT_MYSQL_OPTS = ('"--log-bin=mysql-bin --report-host=localhost '
                       '--report-port={0} "')


class test(mutlib.System_test):
    """test replication administration commands
    This test runs the mysqlrpladmin utility on a known topology.

    Note: this test will run against servers without GTID enabled.
    See rpl_admin_gtid test for test cases for GTID enabled servers.
    """

    server0 = None
    server1 = None
    server2 = None
    server3 = None
    server4 = None
    s1_port = None
    s2_port = None
    s3_port = None
    m_port = None
    master_str = None

    def check_prerequisites(self):
        if not self.servers.get_server(0).check_version_compat(5, 5, 30):
            raise MUTLibError("Test requires server version 5.5.30 or later.")
        if self.servers.get_server(0).supports_gtid() == "ON":
            raise MUTLibError("Test requires servers without GTID enabled.")
        return self.check_num_servers(1)

    def setup(self):
        self.res_fname = "result.txt"

        # Check if the required tools are accessible
        self.check_mylogin_requisites()

        # Spawn servers
        self.server0 = self.servers.get_server(0)
        mysqld = _DEFAULT_MYSQL_OPTS.format(self.servers.view_next_port())
        self.server1 = self.servers.spawn_server("rep_master", kill=True,
                                                 mysqld=mysqld)
        mysqld = _DEFAULT_MYSQL_OPTS.format(self.servers.view_next_port())
        self.server2 = self.servers.spawn_server("rep_slave1", kill=True,
                                                 mysqld=mysqld)
        mysqld = _DEFAULT_MYSQL_OPTS.format(self.servers.view_next_port())
        self.server3 = self.servers.spawn_server("rep_slave2", kill=True,
                                                 mysqld=mysqld)
        mysqld = _DEFAULT_MYSQL_OPTS.format(self.servers.view_next_port())
        self.server4 = self.servers.spawn_server("rep_slave3", kill=True,
                                                 mysqld=mysqld)

        # Reset spawned servers (clear binary log and GTID_EXECUTED set)
        self.reset_master()

        self.m_port = self.server1.port
        self.s1_port = self.server2.port
        self.s2_port = self.server3.port
        self.s3_port = self.server4.port

        for slave in [self.server2, self.server3, self.server4]:
            slave.exec_query("SET SQL_LOG_BIN= 0")
            slave.exec_query("GRANT REPLICATION SLAVE ON *.* TO 'rpl'@'{0}' "
                             "IDENTIFIED BY 'rpl'".format(self.server1.host))
            slave.exec_query("SET SQL_LOG_BIN= 1")

        # Form replication topology - 1 master, 3 slaves
        return self.reset_topology()

    def run(self):
        self.mask_global = False  # Turn off global masks
        cmd_str = "mysqlrpladmin.py {0} ".format(self.master_str)

        master_conn = self.build_connection_string(self.server1).strip(' ')
        slave1_conn = self.build_connection_string(self.server2).strip(' ')
        slave2_conn = self.build_connection_string(self.server3).strip(' ')
        slave3_conn = self.build_connection_string(self.server4).strip(' ')

        slaves_str = ",".join([slave1_conn, slave2_conn, slave3_conn])

        test_num = 1
        comment = "Test case {0} - show health before switchover".format(
            test_num)
        cmd_opts = " --slaves={0} --format=vertical health".format(slaves_str)
        res = mutlib.System_test.run_test_case(self, 0, cmd_str + cmd_opts,
                                               comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Build connection string with loopback address instead of localhost
        slaves_loopback = ("root:root@127.0.0.1:{0},root:root@127.0.0.1:{1},"
                           "root:root@127.0.0.1:{2}".format(self.server2.port,
                                                            self.server3.port,
                                                            self.server4.port))
        slave3_conn_ip = slave3_conn.replace("localhost", "127.0.0.1")

        # Perform switchover from original master to all other slaves and back.
        test_cases = [
            # (master, [slaves_before], candidate, new_master, [slaves_after])
            (master_conn, [slave1_conn, slave2_conn, slave3_conn],
             slave1_conn, "slave1", [slave2_conn, slave3_conn, master_conn]),
            (slave1_conn, [slave2_conn, slave3_conn, master_conn],
             slave2_conn, "slave2", [slave1_conn, slave3_conn, master_conn]),
            (slave2_conn, [slave1_conn, slave3_conn, master_conn],
             slave3_conn, "slave3", [slave2_conn, slave1_conn, master_conn]),
            (slave3_conn_ip, ["root:root@127.0.0.1:"
                              "{0}".format(self.server3.port),
                              slave1_conn, master_conn],
             master_conn, "master", [slave1_conn, slave2_conn, slave3_conn]),
        ]
        test_num += 1
        for case in test_cases:
            slaves_str = ",".join(case[1])
            comment = "Test case {0} - switchover to {1}".format(test_num,
                                                                 case[3])
            cmd_str = ("mysqlrpladmin.py --master={0} "
                       "--rpl-user=rpl:rpl ".format(case[0]))
            cmd_opts = (" --new-master={0} --demote-master --slaves={1} "
                        "switchover".format(case[2], slaves_str))
            res = mutlib.System_test.run_test_case(self, 0, cmd_str + cmd_opts,
                                                   comment)
            if not res:
                raise MUTLibError("{0}: failed".format(comment))
            test_num += 1
            slaves_str = ",".join(case[4])
            cmd_str = "mysqlrpladmin.py --master={0} ".format(case[2])
            comment = "Test case {0} - show health after switchover".format(
                test_num)
            cmd_opts = " --slaves={0} --format=vertical health".format(
                slaves_str)
            res = mutlib.System_test.run_test_case(self, 0, cmd_str + cmd_opts,
                                                   comment)
            if not res:
                raise MUTLibError("{0}: failed".format(comment))
            test_num += 1

        cmd_str = ("mysqlrpladmin.py --master={0} health "
                   "--slaves={1}".format(master_conn, slaves_loopback))
        comment = "Test case {0} - health with loopback".format(test_num)
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        test_num += 1

        cmd_str = ("mysqlrpladmin.py --master={0} health "
                   "--disc=root:root".format(master_conn))
        comment = "Test case {0} - health with discovery".format(test_num)
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        test_num += 1

        # Perform stop, start, and reset (with --master option)
        commands = ['stop', 'start', 'stop', 'reset']
        for cmd in commands:
            comment = ("Test case {0} - run command {1} with "
                       "--master".format(test_num, cmd))
            cmd_str = ("mysqlrpladmin.py --master={0} --slaves={1} "
                       "{2}".format(master_conn, slaves_str, cmd))
            res = self.run_test_case(0, cmd_str, comment)
            if not res:
                raise MUTLibError("{0}: failed".format(comment))
            # START SLAVE is asynchronous and it can take some time to complete
            # on slow servers
            if cmd == 'start':
                time.sleep(3)  # wait 3 second for START to finish
                # Show HEALTH to make sure all slaves started.
                cmd_str = ("mysqlrpladmin.py --master={0} health "
                           "--slaves={1}".format(master_conn, slaves_str))
                comment = ("Test case {0}(b) - health after "
                           "{1}".format(test_num, cmd))
                res = self.run_test_case(0, cmd_str, comment)
                if not res:
                    raise MUTLibError("{0}: failed".format(comment))
            test_num += 1

        # Needed to reset the topology here to run with 5.1 servers.
        # Note: With 5.1 servers after reset commands slaves seem to forgot
        # about their master.
        self.reset_topology()

        # Perform stop, start, and reset (without --master option)
        commands = ['start', 'stop', 'reset']
        for cmd in commands:
            comment = ("Test case {0} - run command {1} without "
                       "--master".format(test_num, cmd))
            cmd_str = ("mysqlrpladmin.py --slaves={0} "
                       "{1}".format(slaves_str, cmd))
            res = self.run_test_case(0, cmd_str, comment)
            if not res:
                raise MUTLibError("{0}: failed".format(comment))
            if cmd == 'start':
                time.sleep(3)  # wait 3 second for START to finish
                # Show HEALTH to make sure all slaves started.
                cmd_str = ("mysqlrpladmin.py --master={0} health "
                           "--slaves={1}".format(master_conn, slaves_str))
                comment = ("Test case {0}(b) - health after "
                           "{1}".format(test_num, cmd))
                res = self.run_test_case(0, cmd_str, comment)
                if not res:
                    raise MUTLibError("{0}: failed".format(comment))
            test_num += 1

        # Now we return the topology to its original state for other tests
        self.reset_topology()

        # Mask out non-deterministic data
        self.do_masks()

        # Remove warning when using test servers without GTID enabled.
        self.remove_result("# WARNING: Errant transactions check skipped")

        # Cleanup for login paths
        self.remove_login_path_data('test_master_socket')
        self.remove_login_path_data('test_slave_socket')

        return True

    def do_masks(self):
        """Apply masks in the result.
        """
        self.replace_substring(str(self.m_port), "PORT1")
        self.replace_substring(str(self.s1_port), "PORT2")
        self.replace_substring(str(self.s2_port), "PORT3")
        self.replace_substring(str(self.s3_port), "PORT4")

        self.replace_substring(": NO", ": XXX")  # for columns.
        self.replace_substring("| NO ", "| XXX")
        self.replace_substring("OFF", "XXX")

        # Must mask 'version' (for tests that use this one as base) before
        # applying the next mask for 'health'.
        self.replace_result("+------------+-------+---------+--------"
                            "+------------+---------+-------------",
                            "+------------+-------+---------+--------"
                            "+------------+---------+-------------"
                            "+-------------------+-----------------"
                            "+------------+-------------+--------------"
                            "+------------------+---------------+-----------"
                            "+----------------+------------+---------------+"
                            "\n")
        self.replace_result("| host       | port  | role    | state  "
                            "| gtid_mode  | health  | version  ",
                            "| host       | port  | role    | state  "
                            "| gtid_mode  | health  | version     "
                            "| master_log_file   | master_log_pos  "
                            "| IO_Thread  | SQL_Thread  | Secs_Behind  "
                            "| Remaining_Delay  | IO_Error_Num  | IO_Error  "
                            "| SQL_Error_Num  | SQL_Error  | Trans_Behind  |"
                            "\n")
        self.replace_result("+------------+-------+---------+--------"
                            "+------------+----------------------------------"
                            "------------------------------------------------"
                            "-----+---------------",
                            "+------------+-------+---------+--------"
                            "+------------+---------+-------------"
                            "+-------------------+-----------------"
                            "+------------+-------------+--------------"
                            "+------------------+---------------+-----------"
                            "+----------------+------------+---------------+"
                            "\n")
        self.replace_result("| host       | port  | role    | state  "
                            "| gtid_mode  | health                           "
                            "                                                "
                            "     | version     ",
                            "| host       | port  | role    | state  "
                            "| gtid_mode  | health  | version     "
                            "| master_log_file   | master_log_pos  "
                            "| IO_Thread  | SQL_Thread  | Secs_Behind  "
                            "| Remaining_Delay  | IO_Error_Num  | IO_Error  "
                            "| SQL_Error_Num  | SQL_Error  | Trans_Behind  |"
                            "\n")

        # Mask slaves behind master.
        # It happens sometimes on windows in a non-deterministic way.
        self.replace_substring("+--------------------------------------------"
                               "--+", "+---------+")
        self.replace_substring("+--------------------------------------------"
                               "---+", "+---------+")
        self.replace_substring("| health                                     "
                               "  |", "| health  |")
        self.replace_substring("| health                                     "
                               "   |", "| health  |")
        self.replace_substring("| OK                                         "
                               "  |", "| OK      |")
        self.replace_substring("| OK                                         "
                               "   |", "| OK      |")
        self.replace_substring_portion("| Slave delay is ",
                                       "seconds behind master., No  |",
                                       "| OK      |")

    def reset_master(self, servers_list=None):
        """Resets a list of masters.

        server_list[in]     List with the server instances.
        """
        servers_list = [] if servers_list is None else servers_list
        # Clear binary log and GTID_EXECUTED of given servers
        if servers_list:
            servers = servers_list
        else:
            servers = [self.server1, self.server2, self.server3, self.server4]
        for srv in servers:
            try:
                srv.exec_query("RESET MASTER")
            except UtilError as err:
                raise MUTLibError("Unexpected error performing RESET MASTER "
                                  "for server {0}:{1}: "
                                  "{2}".format(srv.host, srv.port, err))

    def reset_topology(self, slaves_list=None, rpl_user='rpl',
                       rpl_passwd='rpl', master=None, ssl=True):
        """Reset topology.

        server_list[in]     List with the server instances.
        rpl_user[in]        Replication user. Default=rpl.
        rpl_passwd[in]      Replication password. Default=rpl
        master[in]          Master server instance.
        ssl[in]             Use the ssl certificates from the master
                            (default=True).
        """
        if slaves_list:
            slaves = slaves_list
        else:
            # Default replication topology - 1 master, 3 slaves
            slaves = [self.server2, self.server3, self.server4]
        if master is None:
            master = self.server1  # Use server1 as default master.
        self.master_str = " --master={0}".format(
            # Use the ssl certificates from the master, so the rpl user is set
            # with these certificates in all slaves, and they can connect to
            # master.
            self.build_connection_string(master, ssl)
        )

        servers = [master]
        servers.extend(slaves)

        # Check if all servers are alive, and if they are not,
        # spawn a new instance
        for index, server in enumerate(servers[:]):
            mysqld = _DEFAULT_MYSQL_OPTS.format(self.servers.view_next_port())
            servers[index] = self.servers.spawn_server(server.role, mysqld)

        for slave in servers:
            try:
                slave.exec_query("STOP SLAVE")
                slave.exec_query("RESET SLAVE")
            except UtilError:
                pass

        for slave in slaves:
            slave_str = " --slave={0}".format(
                self.build_connection_string(slave))
            conn_str = self.master_str + slave_str
            cmd = ("mysqlreplicate.py --rpl-user={0}:{1} {2} "
                   "-vvv".format(rpl_user, rpl_passwd, conn_str))
            res = self.exec_util(cmd, self.res_fname)
            if res != 0:
                return False

        return True

    def stop_slaves(self, slaves_list=None):
        """Stops a list of slaves.

        server_list[in]     List with the server instances.
        """
        if slaves_list:
            slaves = slaves_list
        else:
            # Default replication topology - 1 master, 3 slaves
            slaves = [self.server2, self.server3, self.server4]
        for slave in slaves:
            try:
                slave.exec_query("STOP SLAVE")
            except UtilError as err:
                raise MUTLibError("Unexpected error performing STOP SLAVE "
                                  "for server {0}:{1}: "
                                  "{2}".format(slave.host, slave.port, err))

    def reset_slaves(self, slaves_list=None):
        """Resets a list of slaves.

        server_list[in]     List with the server instances.
        """
        if slaves_list:
            slaves = slaves_list
        else:
            # Default replication topology - 1 master, 3 slaves
            slaves = [self.server2, self.server3, self.server4]
        for slave in slaves:
            try:
                slave.exec_query("RESET SLAVE")
            except UtilError as err:
                raise MUTLibError("Unexpected error performing RESET SLAVE "
                                  "for server {0}:{1}: "
                                  "{2}".format(slave.host, slave.port, err))

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        if self.res_fname:
            try:
                os.unlink(self.res_fname)
            except OSError:
                pass
        # Kill all spawned servers.
        self.kill_server_list(
            ['rep_master', 'rep_slave1', 'rep_slave2', 'rep_slave3']
        )
        return True
