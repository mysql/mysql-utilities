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
Test privileges to run the mysqlbinlogmove utility.
"""

import os
import time

import binlogmove

from mysql.utilities.common.user import change_user_privileges
from mysql.utilities.exception import MUTLibError


class test(binlogmove.test):
    """Test binlog relocate utility privileges.

    This test verify the privileges required to execute the mysqlbinlogmove
    utility.

    RELOAD privilege required when the server is used (to flush binary logs),
    otherwise if --skip-flush-binlogs is used or no server is specified no
    privileges are required.

    NOTE: Test extend the base binlogmove test, having the same prerequisites.
    """

    @staticmethod
    def wait_for_file(source_dir, filename, timeout=10):
        """Wait for the creation of the specific file.

        This method checks if the specified file exists and waits for it to
        appear during the specified amount of time (by default 10 seconds).

        source_dir[in]  Source directory where the file is located.
        filename[in]    Name of the file to wait for.
        timeout[in]     Time to wait in seconds (by default 10 seconds).
        """
        file_path = os.path.normpath(os.path.join(source_dir, filename))
        attempts = 0
        while attempts < timeout:
            # Check if the file exists.
            if os.path.isfile(file_path):
                return
            # Wait 1 second before trying again.
            time.sleep(1)
            attempts += 1

    def run(self):
        cmd_base = "mysqlbinlogmove.py"

        # Create user to test privileges on master and slave.
        # No privileges granted to user on master.
        if self.debug:
            print("\nCreating user without any privileges on master...")
        change_user_privileges(self.server1, 'm_user', 'm_pwd',
                               self.server1.host, grant_list=None,
                               revoke_list=None, disable_binlog=True,
                               create_user=True)
        # No privileges granted to user on slave.
        if self.debug:
            print("\nCreating user without any privileges on slave...")
        change_user_privileges(self.server2, 's_user', 's_pwd',
                               self.server2.host, grant_list=None,
                               revoke_list=None, disable_binlog=True,
                               create_user=True)

        master_con = self.build_custom_connection_string(self.server1,
                                                         'm_user', 'm_pwd')
        slave1_con = self.build_custom_connection_string(self.server2,
                                                         's_user', 's_pwd')

        # Disable automatic relay log purging on slave.
        self.server2.exec_query('SET GLOBAL relay_log_purge = 0')

        # Generate multiple binary log files.
        if self.debug:
            print("\nCreate multiple binary logs on all servers "
                  "(FLUSH LOCAL LOGS)...")
        for srv in [self.server1, self.server2]:
            for _ in range(5):
                srv.exec_query('FLUSH LOCAL LOGS')

        # Stop slave to avoid the creation of more relay logs.
        self.server2.exec_query('STOP SLAVE')

        master_src = self.server1.select_variable('datadir')
        if self.debug:
            print("\nServer {0}:{1} source directory (datadir): "
                  "{2}".format(self.server1.host, self.server1.port,
                               master_src))

        # Move all binary log files on master, using a user with no privileges.
        test_num = 1
        comment = ("Test case {0}a - move binary logs (fail) using: "
                   "'m_user' with no privileges.").format(test_num)
        cmd = "{0} --server={1} --log-type=all {2}".format(cmd_base,
                                                           master_con,
                                                           self.master_dir)
        res = self.run_test_case(1, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Grant all required privileges to user on master.
        if self.debug:
            print("\nGrant all required privileges on master.")
        master_grants = ['RELOAD']
        change_user_privileges(self.server1, 'm_user', 'm_pwd',
                               self.server1.host, grant_list=master_grants,
                               revoke_list=None, disable_binlog=True,
                               create_user=False)

        # Move all binary log files on master, using a user with all required
        # privileges (RELOAD).
        test_num += 1
        comment = ("Test case {0}a - move binary logs (succeed) using: "
                   "'m_user' with RELOAD privilege.").format(test_num)
        cmd = "{0} --server={1} --log-type=all {2}".format(cmd_base,
                                                           master_con,
                                                           self.master_dir)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        self.results.append("Test case {0}b - check moved files and changes "
                            "in index file:\n".format(test_num))
        self.check_moved_binlogs(self.master_dir, master_src,
                                 'master-bin.index')

        slave1_src = self.server2.select_variable('datadir')
        if self.debug:
            print("\nServer {0}:{1} source directory (datadir): "
                  "{2}".format(self.server2.host, self.server2.port,
                               slave1_src))

        # Wait for all relay log files to be created on the slave.
        self.wait_for_file(slave1_src, 'slave1-relay-bin.000018')

        # Move all binary log files on slave with --skip-flush-binlogs, using
        # a user with no privileges.
        test_num += 1
        comment = ("Test case {0}a - move binary logs (succeed) with "
                   "--skip-flush-binlogs using: 's_user' with no privileges"
                   ".").format(test_num)
        cmd = ("{0} --server={1} --log-type=all --skip-flush-binlogs "
               "{2}").format(cmd_base, slave1_con, self.slave1_dir)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        self.results.append("Test case {0}b - check moved files and changes "
                            "in index file:\n".format(test_num))
        self.check_moved_binlogs(self.slave1_dir, slave1_src,
                                 'slave1-bin.index', 'slave1-relay-bin',
                                 'slave1-relay-bin.index')

        # Mask non-deterministic data.
        self.replace_substring(str(self.server1.port), "PORT1")
        # Warning messages for older MySQL versions (variables not available).
        self.remove_result("# WARNING: Variable 'relay_log_basename' is not "
                           "available for server ")
        self.remove_result("# WARNING: Variable 'log_bin_basename' is not "
                           "available for server ")

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)
