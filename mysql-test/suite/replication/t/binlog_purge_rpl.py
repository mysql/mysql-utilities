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
binlog_purge_rpl test.
"""

import rpl_admin
from binlog_rotate import binlog_range_files_exists

from mysql.utilities.exception import MUTLibError

_DEFAULT_MYSQL_OPTS = ('"--log-bin=mysql-bin '
                       ' --report-host=localhost '
                       '--report-port={0} --bind-address=:: '
                       '"').format('{0}', "")


def flush_server_logs_(server, times=5):
    """Flush logs on a server

    server[in]    the instance server where to flush logs on
    times[in]     number of times to flush the logs.
    """
    # Flush master binary log
    server.exec_query("SET sql_log_bin = 0")
    for _ in range(times):
        server.exec_query("FLUSH LOCAL BINARY LOGS")
    server.exec_query("SET sql_log_bin = 1")


class test(rpl_admin.test):
    """test binlog purge Utility
    This test runs the mysqlbinlogpurge utility on a known topology.
    """

    master_datadir = None
    slaves = None
    mask_ports = []

    def check_prerequisites(self):
        return self.check_num_servers(1)

    def setup(self):
        self.res_fname = "result.txt"

        # Spawn servers
        self.server0 = self.servers.get_server(0)
        mysqld = _DEFAULT_MYSQL_OPTS.format(self.servers.view_next_port())
        self.server1 = self.servers.spawn_server(
            "rep_master_binlog_purge", mysqld, True
        )
        mysqld = _DEFAULT_MYSQL_OPTS.format(self.servers.view_next_port())
        self.server2 = self.servers.spawn_server(
            "rep_slave1_binlog_purge", mysqld, True
        )
        mysqld = _DEFAULT_MYSQL_OPTS.format(self.servers.view_next_port())
        self.server3 = self.servers.spawn_server(
            "rep_slave2_binlog_purge", mysqld, True
        )
        mysqld = _DEFAULT_MYSQL_OPTS.format(self.servers.view_next_port())
        self.server4 = self.servers.spawn_server(
            "rep_slave3_binlog_purge", mysqld, True
        )

        # Get master datadir
        rows = self.server1.exec_query("SHOW VARIABLES LIKE 'datadir'")
        if not rows:
            raise MUTLibError("Unable to determine datadir of cloned server "
                              "at {0}:{1}".format(self.server1.host,
                                                  self.server1.port))
        self.master_datadir = rows[0][1]

        # Reset spawned servers (clear binary log and GTID_EXECUTED set)
        self.reset_master()

        self.mask_ports.append(self.server1.port)
        self.mask_ports.append(self.server2.port)
        self.mask_ports.append(self.server3.port)
        self.mask_ports.append(self.server4.port)

        slaves_list = [self.server2, self.server3, self.server4]
        rpl_admin.test.reset_topology(self, slaves_list=slaves_list,
                                      master=self.server1)

        self.slaves = [self.server2, self.server3, self.server4]

        # Flush master binary log
        flush_server_logs_(self.server1)

        return True

    def run(self):
        test_num = 1

        master_conn = self.build_connection_string(self.server1).strip(' ')
        slave1_conn = self.build_connection_string(self.server2).strip(' ')
        slave2_conn = self.build_connection_string(self.server3).strip(' ')
        slave3_conn = self.build_connection_string(self.server4).strip(' ')

        comment = "mysqlrplshow.py"
        cmd_opts = ("-r --discover-slaves-login={0} "
                    ).format(master_conn.split('@')[0])
        cmds = "mysqlrplshow.py --master={0} {1}".format(master_conn, cmd_opts)
        self.run_test_case(0, cmds, comment)

        cmd_str = "mysqlbinlogpurge.py --master={0} ".format(master_conn)
        cmd_opts = "--discover-slaves={0} ".format(master_conn.split('@')[0])

        comment = ("Test case {0} - mysqlbinlogpurge: with discover option"
                   "".format(test_num))
        cmds = "{0} {1}".format(cmd_str, cmd_opts)
        res = self.run_test_case(0, cmds, comment)
        # Binlog Files 1 and 5 must not exists
        if not res or True in binlog_range_files_exists((1, 5),
                                                        self.master_datadir,
                                                        debug=self.debug):
            raise MUTLibError("{0}: failed".format(comment))

        flush_server_logs_(self.server1)

        test_num += 1
        comment = ("Test case {0} - mysqlbinlogpurge: with discover "
                   "and verbose options".format(test_num))
        cmds = ("{0} {1} -vv"
                "").format(cmd_str, cmd_opts, "binlog_purge{0}.log".format(1))
        res = self.run_test_case(0, cmds, comment)
        # Binlog Files 6 and 10 must not exists
        if not res or True in binlog_range_files_exists((6, 10),
                                                        self.master_datadir,
                                                        debug=self.debug):
            raise MUTLibError("{0}: failed".format(comment))

        flush_server_logs_(self.server1)
        rpl_admin.test.reset_topology(self, slaves_list=self.slaves,
                                      master=self.server1)

        cmd_opts = "--slaves={0},{1},{2} ".format(slave1_conn, slave2_conn,
                                                  slave3_conn)
        test_num += 1
        comment = ("Test case {0} - mysqlbinlogpurge: slaves option"
                   "".format(test_num))
        cmds = "{0} {1} ".format(cmd_str, cmd_opts)
        res = self.run_test_case(0, cmds, comment)
        # Binlog Files 11 and 15 must not exists
        if not res or True in binlog_range_files_exists((11, 15),
                                                        self.master_datadir,
                                                        debug=self.debug):
            raise MUTLibError("{0}: failed".format(comment))

        flush_server_logs_(self.server1)
        rpl_admin.test.reset_topology(self, slaves_list=self.slaves,
                                      master=self.server1)

        cmd_opts = "--slaves={0},{1},{2} ".format(slave1_conn, slave2_conn,
                                                  slave3_conn)
        test_num += 1
        comment = ("Test case {0} - mysqlbinlogpurge: slaves and verbose "
                   "options".format(test_num))
        cmds = "{0} {1} -vv".format(cmd_str, cmd_opts)
        res = self.run_test_case(0, cmds, comment)
        # Binlog Files 16 and 20 must not exists
        if not res or True in binlog_range_files_exists((16, 20),
                                                        self.master_datadir,
                                                        debug=self.debug):
            raise MUTLibError("{0}: failed".format(comment))

        flush_server_logs_(self.server1)
        rpl_admin.test.reset_topology(self, slaves_list=self.slaves,
                                      master=self.server1)

        test_num += 1
        comment = ("Test case {0} - mysqlbinlogpurge: --binlog "
                   "option".format(test_num))
        opts = "{0} --binlog={1}".format(cmd_opts, "mysql-bin.0000023")
        cmds = "{0} {1}".format(cmd_str, opts)
        res = self.run_test_case(0, cmds, comment)
        # Binlog Files 21 and 22 must not exists
        if not res or True in binlog_range_files_exists((21, 22),
                                                        self.master_datadir,
                                                        debug=self.debug):
            raise MUTLibError("{0}: failed".format(comment))

        flush_server_logs_(self.server1)
        rpl_admin.test.reset_topology(self, slaves_list=self.slaves,
                                      master=self.server1)

        test_num += 1
        comment = ("Test case {0} - mysqlbinlogpurge: --binlog "
                   "option and verbose".format(test_num))
        opts = "{0} --binlog={1}".format(cmd_opts, "mysql-bin.27")
        cmds = "{0} {1} -v".format(cmd_str, opts)
        res = self.run_test_case(0, cmds, comment)
        # Binlog Files 23 and 26 must not exists
        if not res or True in binlog_range_files_exists((23, 26),
                                                        self.master_datadir,
                                                        debug=self.debug):
            raise MUTLibError("{0}: failed".format(comment))

        # Mask out non-deterministic data
        rpl_admin.test.do_masks(self)

        p_n = 0
        for port in self.mask_ports:
            p_n += 1
            self.replace_substring(str(port), "PORT{0}".format(p_n))

        io_reading = "I/O thread is currently reading: mysql-bin.{0}"
        sql_executed = "executed by the SQL thread: mysql-bin.{0}"

        # Mask binlog file numbers range, limited by calls to flush logs
        for num in range(5, 62):
            self.replace_substring(io_reading.format(repr(num).zfill(6)),
                                   io_reading.format("XXXXXX"))
            self.replace_substring(sql_executed.format(repr(num).zfill(6)),
                                   sql_executed.format("XXXXXX"))

        self.replace_result(
            "# File position of the I/O thread:",
            "# File position of the I/O thread: XXX\n"
        )

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        # Kill the servers that are only for this test.
        kill_list = ['rep_master_binlog_purge',
                     'rep_slave1_binlog_purge',
                     'rep_slave2_binlog_purge',
                     'rep_slave3_binlog_purge']
        return self.kill_server_list(kill_list)
