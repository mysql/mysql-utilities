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
rpl_sync_errors_sql_mode test.
"""

import os

import rpl_sync
from rpl_sync_ansi_quotes import MYSQL_OPTS_DEFAULT

from mysql.utilities.exception import MUTLibError


class test(rpl_sync.test):
    """Test replication synchronization checker errors.

    This test checks the mysqlrplsync utility known error conditions when the
    SQL mode is not the same among all the servers.
    """

    def setup(self):
        self.res_fname = "result.txt"

        # Spawn servers.
        self.server0 = self.servers.get_server(0)
        mysqld = MYSQL_OPTS_DEFAULT.format(port=self.servers.view_next_port(),
                                           mode='MSSQL') # ANSI_QUOTES
        self.server1 = self.servers.spawn_server("rpl_master_gtid_aq", mysqld,
                                                 True)
        mysqld = MYSQL_OPTS_DEFAULT.format(port=self.servers.view_next_port(),
                                           mode="''")
        self.server2 = self.servers.spawn_server("rpl_slave1_gtid_aq", mysqld,
                                                 True)
        mysqld = MYSQL_OPTS_DEFAULT.format(port=self.servers.view_next_port(),
                                           mode='ORACLE')
        self.server3 = self.servers.spawn_server("rpl_slave2_gtid_aq", mysqld,
                                                 True)
        mysqld = MYSQL_OPTS_DEFAULT.format(port=self.servers.view_next_port(),
                                           mode='NO_ENGINE_SUBSTITUTION')
        self.server4 = self.servers.spawn_server("rpl_slave3_gtid_aq", mysqld,
                                                 True)

        # Reset spawned servers (clear binary log and GTID_EXECUTED set)
        self.reset_master([self.server1, self.server2, self.server3,
                           self.server4])

        # Set replication topology.
        self.reset_topology([self.server2, self.server3, self.server4])

        return True

    def run(self):
        self.mask_global = False  # Turn off global masks
        cmd_base = "mysqlrplsync.py"
        master_con = self.build_connection_string(self.server1).strip(' ')
        slave1_con = self.build_connection_string(self.server2).strip(' ')
        slave2_con = self.build_connection_string(self.server3).strip(' ')
        slave3_con = self.build_connection_string(self.server4).strip(' ')
        slaves_con = "{0},{1},{2}".format(slave1_con, slave2_con, slave3_con)

        # Check the data consistency on servers with different SQL modes.
        test_num = 1
        comment = ("Test case {0} - Different sql modes error message."
                   "").format(test_num)
        cmd = "{0} --master={1} --slaves={2}".format(cmd_base, master_con,
                                                     slaves_con)
        res = self.run_test_case(1, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

         # Mask out non-deterministic data
        self.do_masks()

        return True

    def do_masks(self):
        self.replace_substring(str(self.server1.port), "PORT1")
        self.replace_substring(str(self.server2.port), "PORT2")
        self.replace_substring(str(self.server3.port), "PORT3")
        self.replace_substring(str(self.server4.port), "PORT4")

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
            ['rpl_master_gtid_aq', 'rpl_slave1_gtid_aq', 'rpl_slave2_gtid_aq',
             'rpl_slave3_gtid_aq']
        )
        return True
