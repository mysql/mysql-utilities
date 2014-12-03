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
binlog_purge_rpl_errors test.
"""

import rpl_admin
from binlog_rotate import binlog_file_exists

from mysql.utilities.common.user import change_user_privileges
from mysql.utilities.exception import MUTLibError


_DEFAULT_MYSQL_OPTS = ('"--log-bin=mysql-bin '
                       '--report-host=localhost '
                       '--report-port={0} --bind-address=:: '
                       '"')

_NO_BINLOG_MYSQL_OPTS = ('"'
                         '--report-host=localhost '
                         '--report-port={0} --bind-address=:: '
                         '"')


class test(rpl_admin.test):
    """Test errors for the binlog purge utility

    This test checks error conditions when executing the mysqlbinlogpurge
    utility on a known topology.
    """
    mask_ports = []
    server1_datadir = None
    server2_datadir = None
    server4_datadir = None
    server5 = None

    def check_prerequisites(self):
        return self.check_num_servers(1)

    def setup(self):
        self.res_fname = "result.txt"

        # Spawn servers
        self.server0 = self.servers.get_server(0)
        mysqld = _DEFAULT_MYSQL_OPTS.format(self.servers.view_next_port())
        self.server1 = self.servers.spawn_server(
            "binlog_purge_rpl_master", mysqld, True
        )
        mysqld = _DEFAULT_MYSQL_OPTS.format(self.servers.view_next_port())
        self.server2 = self.servers.spawn_server(
            "binlog_purge_rpl_slave1", mysqld, True
        )
        mysqld = _DEFAULT_MYSQL_OPTS.format(self.servers.view_next_port())
        self.server3 = self.servers.spawn_server(
            "binlog_purge_rpl_slave2", mysqld, True
        )
        mysqld = _DEFAULT_MYSQL_OPTS.format(self.servers.view_next_port())
        self.server4 = self.servers.spawn_server(
            "binlog_purge_standalone", mysqld, True
        )
        mysqld = _NO_BINLOG_MYSQL_OPTS.format(self.servers.view_next_port())
        self.server5 = self.servers.spawn_server(
            "binlog_purge_no_binlog", mysqld, True
        )

        # Get datadirs
        rows = self.server1.exec_query("SHOW VARIABLES LIKE 'datadir'")
        if not rows:
            raise MUTLibError("Unable to determine datadir of cloned server "
                              "at {0}:{1}".format(self.server1.host,
                                                  self.server1.port))
        self.server1_datadir = rows[0][1]

        rows = self.server2.exec_query("SHOW VARIABLES LIKE 'datadir'")
        if not rows:
            raise MUTLibError("Unable to determine datadir of cloned server "
                              "at {0}:{1}".format(self.server2.host,
                                                  self.server2.port))
        self.server2_datadir = rows[0][1]

        rows = self.server4.exec_query("SHOW VARIABLES LIKE 'datadir'")
        if not rows:
            raise MUTLibError("Unable to determine datadir of cloned server "
                              "at {0}:{1}".format(self.server4.host,
                                                  self.server4.port))
        self.server4_datadir = rows[0][1]

        # Reset spawned servers (clear binary log and GTID_EXECUTED set)
        self.reset_master()

        self.mask_ports.append(self.server1.port)
        self.mask_ports.append(self.server2.port)
        self.mask_ports.append(self.server3.port)
        self.mask_ports.append(self.server4.port)
        self.mask_ports.append(self.server5.port)

        rpl_admin.test.reset_topology(self, slaves_list=[self.server2],
                                      master=self.server1)

        rpl_user = 'rpl'
        rpl_passwd = 'rpl'
        self.master_str = " --master={0}".format(
            self.build_connection_string(self.server2, ssl=True)
        )

        slave_str = " --slave={0}".format(
            self.build_connection_string(self.server3))
        conn_str = self.master_str + slave_str
        cmd = ("mysqlreplicate.py --rpl-user={0}:{1} {2} "
               "-vvv".format(rpl_user, rpl_passwd, conn_str))
        res = self.exec_util(cmd, self.res_fname)
        if res != 0:
            return False

        # Flush master binary log
        for _ in range(2):
            self.server1.exec_query("FLUSH BINARY LOGS")

        self.server1.exec_query("SHOW BINARY LOGS")

        return True

    def run(self):
        test_num = 1

        master_conn = self.build_connection_string(self.server1).strip(' ')
        slave1_conn = self.build_connection_string(self.server2).strip(' ')
        slave2_conn = self.build_connection_string(self.server3).strip(' ')
        std_server_conn = self.build_connection_string(self.server4).strip(' ')
        nb_server_conn = self.build_connection_string(self.server5).strip(' ')

        comment = "mysqlrplshow.py"
        cmd_opts = ("-r --discover-slaves-login={0} "
                    ).format(master_conn.split('@')[0])
        cmds = "mysqlrplshow.py --master={0} {1}".format(master_conn, cmd_opts)
        self.run_test_case(0, cmds, comment)

        cmd_str = "mysqlbinlogpurge.py --master={0} ".format(master_conn)
        cmd_opts = "--discover-slaves={0} ".format("in:valid")

        comment = ("Test case {0} - mysqlbinlogpurge: with discover invalid "
                   "login".format(test_num))
        cmds = "{0} {1}".format(cmd_str, cmd_opts)
        res = self.run_test_case(1, cmds, comment)
        if not res or not binlog_file_exists(self.server1_datadir,
                                             "mysql-bin.000001", self.debug):
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - mysqlbinlogpurge: with discover invalid "
                   "login and verbose".format(test_num))
        cmds = "{0} {1} -vvv".format(cmd_str, cmd_opts)
        res = self.run_test_case(1, cmds, comment)
        if not res or not binlog_file_exists(self.server1_datadir,
                                             "mysql-bin.000001", self.debug):
            raise MUTLibError("{0}: failed".format(comment))

        cmd_str = "mysqlbinlogpurge.py --master={0} "
        cmd_opts = "--discover-slaves={0} ".format(master_conn.split('@')[0])
        test_num += 1
        comment = ("Test case {0} - mysqlbinlogpurge: single server given as "
                   "master and --discover option".format(test_num))
        cmds = "{0} {1}".format(cmd_str.format(std_server_conn), cmd_opts)
        res = self.run_test_case(1, cmds, comment)
        if not res or not binlog_file_exists(self.server4_datadir,
                                             "mysql-bin.000001", self.debug):
            raise MUTLibError("{0}: failed".format(comment))

        cmd_opts = "--slaves={0},{1}".format(slave1_conn, slave2_conn)
        test_num += 1
        comment = ("Test case {0} - mysqlbinlogpurge: standalone server given "
                   "as master and --slaves from other master".format(test_num))
        cmds = "{0} {1}".format(cmd_str.format(std_server_conn), cmd_opts)
        res = self.run_test_case(1, cmds, comment)
        if not res or not binlog_file_exists(self.server4_datadir,
                                             "mysql-bin.000001", self.debug):
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - mysqlbinlogpurge: server without binlog "
                   "as master and --slaves from other master".format(test_num))
        cmds = "{0} {1}".format(cmd_str.format(nb_server_conn), cmd_opts)
        res = self.run_test_case(1, cmds, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        cmd_opts = "--slaves={0},{1} ".format(slave1_conn, slave2_conn)
        cmd_str = "mysqlbinlogpurge.py --master={0} ".format(master_conn)
        test_num += 1
        comment = ("Test case {0} - mysqlbinlogpurge: one slave from other "
                   "master".format(test_num))
        cmds = "{0} {1}".format(cmd_str.format(slave2_conn), cmd_opts)
        res = self.run_test_case(1, cmds, comment)
        if not res or not binlog_file_exists(self.server1_datadir,
                                             "mysql-bin.000001", self.debug):
            raise MUTLibError("{0}: failed".format(comment))

        cmd_opts = "--slaves={0},{1} ".format(slave1_conn, std_server_conn)
        test_num += 1
        comment = ("Test case {0} - mysqlbinlogpurge: with slaves including an"
                   " standalone server".format(test_num))
        cmds = "{0} {1}".format(cmd_str, cmd_opts)
        res = self.run_test_case(1, cmds, comment)
        if not res or not binlog_file_exists(self.server1_datadir,
                                             "mysql-bin.000001", self.debug):
            raise MUTLibError("{0}: failed".format(comment))

        cmd_opts = "--slaves={0},{1} ".format(slave1_conn, nb_server_conn)
        test_num += 1
        comment = ("Test case {0} - mysqlbinlogpurge: with slave without "
                   "binlog".format(test_num))
        cmds = "{0} {1}".format(cmd_str, cmd_opts)
        res = self.run_test_case(1, cmds, comment)
        if not res or not binlog_file_exists(self.server1_datadir,
                                             "mysql-bin.000001", self.debug):
            raise MUTLibError("{0}: failed".format(comment))

        cmd_str = "mysqlbinlogpurge.py --master={0} ".format(nb_server_conn)
        cmd_opts = "--slaves={0},{1} ".format(slave1_conn, slave2_conn)
        test_num += 1
        comment = ("Test case {0} - mysqlbinlogpurge: Master without binlog"
                   " and --slaves from other master".format(test_num))
        cmds = "{0} {1}".format(cmd_str, cmd_opts)
        res = self.run_test_case(1, cmds, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        cmd_str = "mysqlbinlogpurge.py --server={0} ".format(master_conn)
        test_num += 1
        comment = ("Test case {0} - mysqlbinlogpurge: Master given as server"
                   " on --server option".format(test_num))
        cmds = "{0}".format(cmd_str)
        res = self.run_test_case(1, cmds, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - mysqlbinlogpurge: Master given as server"
                   " on --server option and -v".format(test_num))
        cmds = "{0} -v".format(cmd_str)
        res = self.run_test_case(1, cmds, comment)
        if not res or not binlog_file_exists(self.server1_datadir,
                                             "mysql-bin.000001", self.debug):
            raise MUTLibError("{0}: failed".format(comment))

        self.server2.exec_query("FLUSH BINARY LOGS")
        self.server3.exec_query("STOP SLAVE IO_THREAD")

        disc_opts = "--discover-slaves={0} -vv".format("root:root")
        cmd_str = "mysqlbinlogpurge.py --master={0} ".format(slave1_conn)
        test_num += 1
        comment = ("Test case {0} - mysqlbinlogpurge: Slave disconnected from "
                   "master using --discover-slave option".format(test_num))
        cmds = "{0} {1}".format(cmd_str, disc_opts)
        res = self.run_test_case(1, cmds, comment)
        if not res or not binlog_file_exists(self.server2_datadir,
                                             "mysql-bin.000001", self.debug):
            raise MUTLibError("{0}: failed".format(comment))

        cmd_str = "mysqlbinlogpurge.py --master={0} ".format(slave1_conn)
        test_num += 1
        comment = ("Test case {0} - mysqlbinlogpurge: Slave disconnected from "
                   "master --slaves option".format(test_num))
        cmds = "{0} --slave={1} -vv".format(cmd_str, slave2_conn)
        res = self.run_test_case(1, cmds, comment)
        if not res or not binlog_file_exists(self.server2_datadir,
                                             "mysql-bin.000001", self.debug):
            raise MUTLibError("{0}: failed".format(comment))

        # Mask out non-deterministic data
        rpl_admin.test.do_masks(self)

        p_n = 0
        for port in self.mask_ports:
            p_n += 1
            self.replace_substring(str(port), "PORT{0}".format(p_n))

        self.replace_substring_portion(
            "Slave with id:", "is connected",
            "Slave with id:XXX at localhost:PORT2 is connected"
        )

        # following line is not available in MySQL servers version < 5.6
        self.remove_result("# Binary log basename path:")

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        # Kill the servers that are only for this test.
        kill_list = ['binlog_purge_rpl_master',
                     'binlog_purge_rpl_slave1',
                     'binlog_purge_rpl_slave2',
                     'binlog_purge_standalone',
                     'binlog_purge_no_binlog']
        return self.kill_server_list(kill_list)
