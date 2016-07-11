#
# Copyright (c) 2016, Oracle and/or its affiliates. All rights reserved.
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
binlog_purge_rpl test for ms test and BUG#22543517 running binlogpurge
on second master added to slave replication channels
"""

import replicate_ms

from mysql.utilities.exception import MUTLibError

_CHANGE_MASTER = ("CHANGE MASTER TO MASTER_HOST = 'localhost', "
                  "MASTER_USER = 'rpl', MASTER_PASSWORD = 'rpl', "
                  "MASTER_PORT = {0}, MASTER_AUTO_POSITION=1 "
                  "FOR CHANNEL 'master-{1}'")

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


class test(replicate_ms.test):
    """test binlog purge Utility
    This test runs the mysqlbinlogpurge utility on a known topology.
    """

    master_datadir = None
    slaves = None
    mask_ports = []

    def check_prerequisites(self):
        if not self.servers.get_server(0).check_version_compat(5, 7, 6):
            raise MUTLibError("Test requires server version 5.7.6 or later")
        return self.check_num_servers(1)

    def setup(self):
        self.res_fname = "result.txt"
        res = super(test, self).setup()
        if not res:
            return False
        # Setup multiple channels for slave

        m1_dict = self.get_connection_values(self.server2)
        m2_dict = self.get_connection_values(self.server3)

        for master in [self.server2, self.server3]:
            master.exec_query("SET SQL_LOG_BIN= 0")
            master.exec_query("GRANT REPLICATION SLAVE ON *.* TO 'rpl'@'{0}' "
                              "IDENTIFIED BY 'rpl'".format(self.server1.host))
            master.exec_query("SET SQL_LOG_BIN= 1")
        self.server1.exec_query("SET GLOBAL relay_log_info_repository = 'TABLE'")
        self.server1.exec_query(_CHANGE_MASTER.format(m1_dict[3], 1))
        self.server1.exec_query(_CHANGE_MASTER.format(m2_dict[3], 2))
        self.server1.exec_query("START SLAVE")

        return True

    def run(self):
        test_num = 0

        slave_conn = self.build_connection_string(self.server1).strip(' ')
        master1_conn = self.build_connection_string(self.server2).strip(' ')
        master2_conn = self.build_connection_string(self.server3).strip(' ')

        cmd_str = "mysqlbinlogpurge.py --master={0} ".format(master1_conn)
        cmd_opts = "--discover-slaves={0} ".format(master1_conn.split('@')[0])

        test_num += 1
        comment = ("Test case {0} - mysqlbinlogpurge: with discover "
                   "and verbose options - master 1".format(test_num))
        cmds = ("{0} {1} -vv"
                "").format(cmd_str, cmd_opts, "binlog_purge{0}.log".format(1))
        res = self.run_test_case(0, cmds, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        flush_server_logs_(self.server1)

        cmd_str = "mysqlbinlogpurge.py --master={0} ".format(master2_conn)

        test_num += 1
        comment = ("Test case {0} - mysqlbinlogpurge: with discover "
                   "and verbose options - master 2".format(test_num))
        cmds = ("{0} {1} -vv"
                "").format(cmd_str, cmd_opts, "binlog_purge{0}.log".format(2))
        res = self.run_test_case(0, cmds, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        flush_server_logs_(self.server1)

        super(test, self).reset_ms_topology()

        return True

    def get_result(self):
        # If run method executes successfully without throwing any exceptions,
        # then test was successful
        return True, None

    def record(self):
        # Not a comparative test
        return True

    def cleanup(self):
        return super(test, self).cleanup()
