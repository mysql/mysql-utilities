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
Test privileges to run the mysqlslavetrx utility.
"""

import slave_trx_skip

from mysql.utilities.common.gtid import gtid_set_union
from mysql.utilities.common.user import change_user_privileges
from mysql.utilities.exception import MUTLibError, UtilError


class test(slave_trx_skip.test):
    """Test privileges for the mysqlslavetrx utility.

    This test verify the privileges required to execute the mysqlslavetrx
    utility.

    No specific privilege is required.

    NOTE: Test extend the base slave_trx_skip test, having the same
    prerequisites.
    """

    def run(self):
        """ Run the test cases.

        Return True if all tests pass, otherwise a MUTLibError is issued.
        """
        cmd_base = "mysqlslavetrx.py"

        # Create user to test privileges on slaves.
        # No privileges granted to user on slave.
        if self.debug:
            print("\nCreating user without any privileges on slaves...")
        for srv in [self.server2, self.server3]:
            change_user_privileges(srv, 's_user', 's_pwd',
                                   srv.host, grant_list=None,
                                   revoke_list=None, disable_binlog=True,
                                   create_user=True)

        slave1_con = self.build_custom_connection_string(self.server2,
                                                         's_user', 's_pwd')
        slave2_con = self.build_custom_connection_string(self.server3,
                                                         's_user', 's_pwd')
        slaves_con = ",".join([slave1_con, slave2_con])

        if self.debug:
            print("\nGet UUID of each server:")
        uuids = []
        for srv in [self.server1, self.server2, self.server3]:
            uuids.append(srv.get_server_uuid())
        if self.debug:
            for uuid in uuids:
                print("- {0}".format(uuid))

        # Wait for slaves to catch up to ensure that the GTID_EXECUTED is the
        # same on all servers.
        if self.debug:
            print("\nWait for slaves to catch up with master.")
        self.wait_for_slaves()

        test_num = 1
        comment = ("Test case {0} - Skip GTIDs (fail) using 's_user': no "
                   "privileges on all slaves.").format(test_num)
        gtid_set = "{0}:7,{1}:7,{2}:7".format(*uuids)
        cmd = "{0} --slaves={1} --gtid-set={2}".format(cmd_base, slaves_con,
                                                       gtid_set)
        res = self.run_test_case(1, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Grant all required privileges (SUPER) to user on Slave 1.
        if self.debug:
            print("\nGrant all required privileges (SUPER) on Slave 1.")
        slave_grants = ['SUPER']
        change_user_privileges(self.server2, 's_user', 's_pwd',
                               self.server2.host, grant_list=slave_grants,
                               revoke_list=None, disable_binlog=True,
                               create_user=False)

        test_num += 1
        comment = ("Test case {0} - Skip GTIDs (fail) using 's_user': "
                   "SUPER for slave1 and no privileges for slave2."
                   "").format(test_num)
        res = self.run_test_case(1, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Grant all required privileges (SUPER) to user on Slave 2.
        if self.debug:
            print("\nGrant all required privileges (SUPER) on Slave 2.")
        change_user_privileges(self.server3, 's_user', 's_pwd',
                               self.server3.host, grant_list=slave_grants,
                               revoke_list=None, disable_binlog=True,
                               create_user=False)

        test_num += 1
        comment = ("Test case {0} - Skip GTIDs (succeed) using 's_user': "
                   "SUPER for all slaves."
                   "").format(test_num)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Computed expected GTID_EXECUTED set for all slaves.
        master_gtid_executed = self.server1.get_gtid_executed()
        expected_gtids = gtid_set_union(master_gtid_executed, gtid_set)
        if self.debug:
            print("\nExpected GTID_EXECUTED set: {0}".format(expected_gtids))
        # Check if GTID_EXECUTED match the expected value on all slaves.
        try:
            slave_trx_skip.check_gtid_executed([self.server2, self.server3],
                                               expected_gtids)
        except UtilError as err:
            raise MUTLibError("{0}: failed\n{1}".format(comment, err.errmsg))

        # Mask non-deterministic output.
        self.replace_substring(str(self.server1.port), "PORT1")
        self.replace_substring(str(self.server2.port), "PORT2")
        self.replace_substring(str(self.server3.port), "PORT3")

        # Mask UUID values in GTIDs.
        self.replace_substring(uuids[0], "UUID_m")
        self.replace_substring(uuids[1], "UUID_s1")
        self.replace_substring(uuids[2], "UUID_s2")

        return True

    def get_result(self):
        """ Get the test results.

        Return the result of the comparison of the test execution with the
        ".result" file.
        """
        return self.compare(__name__, self.results)

    def record(self):
        """Save the test output to a ".result" file.

        Return True if the record operation succeeds.
        """
        return self.save_result_file(__name__, self.results)
