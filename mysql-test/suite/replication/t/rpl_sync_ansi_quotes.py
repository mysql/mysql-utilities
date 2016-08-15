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
rpl_sync test.
"""

import os

import rpl_sync


MYSQL_OPTS_DEFAULT = ('"--log-bin=mysql-bin --skip-slave-start '
                      '--log-slave-updates --gtid-mode=on '
                      '--enforce-gtid-consistency '
                      '--report-host=localhost --report-port={port} '
                      '--sync-master-info=1 --master-info-repository=TABLE '
                      '--sql_mode={mode}"')


class test(rpl_sync.test):
    """Test replication synchronization checker.

    This test runs the mysqlrplsync utility to test base sync features.

    NOTE: Test requires servers of version >= 5.6.14 (like the utility),
    because there is a known issue for START SLAVE UNTIL with the
    SQL_AFTER_GTIDS option for versions prior to 5.6.14. More information:
    https://dev.mysql.com/doc/refman/5.6/en/start-slave.html
    """

    def setup(self):
        self.res_fname = "result.txt"

        # Spawn servers
        self.server0 = self.servers.get_server(0)
        mysqld = MYSQL_OPTS_DEFAULT.format(port=self.servers.view_next_port(),
                                           mode='ANSI_QUOTES')
        self.server1 = self.servers.spawn_server("rep_master_gtid_aq", mysqld,
                                                 True)
        mysqld = MYSQL_OPTS_DEFAULT.format(port=self.servers.view_next_port(),
                                           mode="'ANSI_QUOTES'")
        self.server2 = self.servers.spawn_server("rep_slave1_gtid_aq", mysqld,
                                                 True)
        mysqld = MYSQL_OPTS_DEFAULT.format(port=self.servers.view_next_port(),
                                           mode='ANSI_QUOTES')
        self.server3 = self.servers.spawn_server("rep_slave2_gtid_aq", mysqld,
                                                 True)

        # Reset spawned servers (clear binary log and GTID_EXECUTED set)
        self.reset_master([self.server1, self.server2, self.server3])

        # Set replication topology.
        self.reset_topology([self.server2, self.server3])

        return True

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
            ['rep_master_gtid_aq', 'rep_slave1_gtid_aq', 'rep_slave2_gtid_aq']
        )
        return True
