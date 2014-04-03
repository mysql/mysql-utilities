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
rpl_sync_privileges test.
"""

import os

import rpl_sync

from mysql.utilities.common.user import change_user_privileges
from mysql.utilities.exception import MUTLibError


class test(rpl_sync.test):
    """Test replication synchronization checker privileges.
    This test verify the privileges required by servers to execute the
    mysqlrplsync utility.
    On master: SUPER or REPLICATION CLIENT, LOCK TABLES and SELECT
    On slaves: SUPER and SELECT

    NOTE: Test extend the base rpl_sync test and it has the same prerequisites.
    """

    def setup(self):
        self.res_fname = "result.txt"

        # Spawn servers.
        self.server0 = self.servers.get_server(0)
        mysqld = rpl_sync.MYSQL_OPTS_DEFAULT.format(
            port=self.servers.view_next_port()
        )
        self.server1 = self.spawn_server("rep_master_gtid", mysqld, True)
        mysqld = rpl_sync.MYSQL_OPTS_DEFAULT.format(
            port=self.servers.view_next_port()
        )
        self.server2 = self.spawn_server("rep_slave1_gtid", mysqld, True)

        # Reset spawned servers (clear binary log and GTID_EXECUTED set).
        self.reset_master([self.server1, self.server2])

        # Set replication topology.
        self.reset_topology([self.server2])

        return True

    def run(self):
        # Create user to test privileges on master and slave.
        # Missing privilege on the master (SUPER and REPLICATION CLIENT).
        if self.debug:
            print("\nCreate user with missing privileges (SUPER and "
                  "REPLICATION CLIENT) on master.")
        master_grants = ['LOCK TABLES', 'SELECT']
        change_user_privileges(self.server1, 'm_user', 'm_pwd',
                               self.server1.host, grant_list=master_grants,
                               revoke_list=None, disable_binlog=True,
                               create_user=True)
        if self.debug:
            print("\nCreate user with all required privileges on slave.")
        slave_grants = ['SUPER', 'SELECT']
        change_user_privileges(self.server2, 's_user', 's_pwd',
                               self.server1.host, grant_list=slave_grants,
                               revoke_list=None, disable_binlog=True,
                               create_user=True)

        master_con = self.build_custom_connection_string(self.server1,
                                                         'm_user', 'm_pwd')
        slave1_con = self.build_custom_connection_string(self.server2,
                                                         's_user', 's_pwd')

        cmd_base = "mysqlrplsync.py --master={0} --slaves={1}".format(
            master_con, slave1_con
        )

        if self.debug:
            print("\nCreate test database and tables on master.")
        rpl_sync.create_test_db(self.server1)

        if self.debug:
            print("\nWait for slaves to catch up with master.")
        self.wait_for_slaves([self.server2])

        # Test sync using a master user with missing privilege: SUPER and
        # REPLICATION CLIENT.
        test_num = 1
        comment = ("Test case {0} - sync (fail) using 'm_user' without: "
                   "SUPER and REPLICATION CLIENT.".format(test_num))
        res = self.run_test_case(1, cmd_base, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Grant all required privileges except LOCK TABLES to user on master.
        if self.debug:
            print("\nGrant required privileges except LOCK TABLES on master.")
        master_grants = ['SUPER']
        master_revokes = ['LOCK TABLES']
        change_user_privileges(self.server1, 'm_user', 'm_pwd',
                               self.server1.host, grant_list=master_grants,
                               revoke_list=master_revokes, disable_binlog=True,
                               create_user=False)

        # Test sync using a master user with missing privilege: LOCK TABLES.
        test_num += 1
        comment = ("Test case {0} - sync (fail) using 'm_user' without: "
                   "LOCK TABLES.".format(test_num))
        res = self.run_test_case(1, cmd_base, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Grant all required privileges except SELECT to user on master.
        if self.debug:
            print("\nGrant required privileges except SELECT on master.")
        master_grants = ['LOCK TABLES']
        master_revokes = ['SELECT']
        change_user_privileges(self.server1, 'm_user', 'm_pwd',
                               self.server1.host, grant_list=master_grants,
                               revoke_list=master_revokes, disable_binlog=True,
                               create_user=False)

        # Test sync using a master user with missing privilege: LOCK TABLES.
        test_num += 1
        comment = ("Test case {0} - sync (fail) using 'm_user' without: "
                   "SELECT.".format(test_num))
        res = self.run_test_case(1, cmd_base, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Grant all required privileges to user on master.
        if self.debug:
            print("\nGrant required privileges on master.")
        master_grants = ['SELECT']
        change_user_privileges(self.server1, 'm_user', 'm_pwd',
                               self.server1.host, grant_list=master_grants,
                               revoke_list=None, disable_binlog=True,
                               create_user=False)

        # Grant all required privileges except SUPER to user on slave.
        if self.debug:
            print("\nGrant required privileges except SUPER on slave.")
        slave_revokes = ['SUPER']
        change_user_privileges(self.server2, 's_user', 's_pwd',
                               self.server2.host, grant_list=None,
                               revoke_list=slave_revokes, disable_binlog=True,
                               create_user=False)

        # Test sync using a slave user with missing privilege: SUPER.
        test_num += 1
        comment = ("Test case {0} - sync (fail) using 's_user' without: "
                   "SUPER.".format(test_num))
        res = self.run_test_case(1, cmd_base, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Grant all required privileges except SELECT to user on slave.
        if self.debug:
            print("\nGrant required privileges except SELECT on slave.")
        slave_grants = ['SUPER']
        slave_revokes = ['SELECT']
        change_user_privileges(self.server2, 's_user', 's_pwd',
                               self.server2.host, grant_list=slave_grants,
                               revoke_list=slave_revokes, disable_binlog=True,
                               create_user=False)

        # Test sync using a slave user with missing privilege: SELECT.
        test_num += 1
        comment = ("Test case {0} - sync (fail) using 's_user' without: "
                   "SELECT.".format(test_num))
        res = self.run_test_case(1, cmd_base, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Grant all required privileges to user on slave.
        if self.debug:
            print("\nGrant required privileges on slave.")
        slave_grants = ['SELECT']
        change_user_privileges(self.server2, 's_user', 's_pwd',
                               self.server2.host, grant_list=slave_grants,
                               revoke_list=None, disable_binlog=True,
                               create_user=False)

        # Test sync with master and slave users with all required privileges.
        # Using SUPER (not REPLICATION CLIENT) for master.
        test_num += 1
        comment = ("Test case {0} - sync (succeed) using: 'm_user' with "
                   "SUPER, LOCK TABLES and SELECT; 's_user' with SUPER and "
                   "SELECT.".format(test_num))
        res = self.run_test_case(0, cmd_base, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Replace SUPER with REPLICATION CLIENT for user on master.
        if self.debug:
            print("\nReplace SUPER with REPLICATION CLIENT on master.")
        master_grants = ['REPLICATION CLIENT']
        master_revokes = ['SUPER']
        change_user_privileges(self.server1, 'm_user', 'm_pwd',
                               self.server1.host, grant_list=master_grants,
                               revoke_list=master_revokes, disable_binlog=True,
                               create_user=False)

        # Test sync with master and slave users with all required privileges.
        # Using REPLICATION CLIENT (not SUPER) for master.
        test_num += 1
        comment = ("Test case {0} - sync (succeed) using: 'm_user' with "
                   "REPLICATION CLIENT, LOCK TABLES and SELECT; 's_user' with "
                   "SUPER and SELECT.".format(test_num))
        res = self.run_test_case(0, cmd_base, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Mask out non-deterministic data
        self.do_masks()

        return True

    def do_masks(self):
        self.replace_substring(str(self.server1.port), "PORT1")
        self.replace_substring(str(self.server2.port), "PORT2")

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
            ['rep_master_gtid', 'rep_slave1_gtid']
        )
        return True
