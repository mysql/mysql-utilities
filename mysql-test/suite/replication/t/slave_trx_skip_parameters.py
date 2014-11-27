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
Test options for the mysqlslavetrx utility.
"""

import slave_trx_skip

from mysql.utilities.common.gtid import gtid_set_union
from mysql.utilities.exception import MUTLibError, UtilError


class test(slave_trx_skip.test):
    """Test the options for the mysqlslavetrx utility.

    This test checks the behaviour of the mysqlslavetrx utility using
    different options.

    NOTE: Test extend the base slave_trx_skip test, having the same
    prerequisites.
    """

    def run(self):
        """ Run the test cases.

        Return True if all tests pass, otherwise a MUTLibError is issued.
        """
        cmd_base = "mysqlslavetrx.py"
        slave1_con = self.build_connection_string(self.server2).strip(' ')
        slave2_con = self.build_connection_string(self.server3).strip(' ')
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
        comment = "Test case {0} - Help.".format(test_num)
        cmd = "{0} --help".format(cmd_base)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - Skip only one GTID on a single slave"
                   ".").format(test_num)
        gtid_set = "{0}:10".format(uuids[0])
        cmd = "{0} --slaves={1} --gtid-set={2}".format(cmd_base, slave1_con,
                                                       gtid_set)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Computed expected GTID_EXECUTED set for target slave.
        master_gtid_executed = self.server1.get_gtid_executed()
        expected_gtids = gtid_set_union(master_gtid_executed, gtid_set)
        if self.debug:
            print("\nExpected GTID_EXECUTED set: {0}".format(expected_gtids))
        # Check if GTID_EXECUTED match the expected value on all slaves.
        try:
            slave_trx_skip.check_gtid_executed([self.server2], expected_gtids)
            # No GTID skipped for server3.
            slave_trx_skip.check_gtid_executed([self.server3],
                                               master_gtid_executed)
        except UtilError as err:
            raise MUTLibError("{0}: failed\n{1}".format(comment, err.errmsg))

        test_num += 1
        comment = ("Test case {0}a - [DRYRUN] Skip GTID set on all slaves "
                   "(previous skipped GTID is ignored).").format(test_num)
        gtid_set = "{0}:8-10:12,{1}:7-9,{2}:7:9".format(*uuids)
        cmd = "{0} --slaves={1} --gtid-set={2} --dryrun".format(
            cmd_base, slaves_con, gtid_set)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Check if GTID_EXECUTED match the expected value on all slaves.
        try:
            # GTID_EXECUTED is expected to be the same using dryrun mode.
            slave_trx_skip.check_gtid_executed([self.server2], expected_gtids)
            slave_trx_skip.check_gtid_executed([self.server3],
                                               master_gtid_executed)
        except UtilError as err:
            raise MUTLibError("{0}: failed\n{1}".format(comment, err.errmsg))

        comment = ("Test case {0}b - Skip GTID set on all slaves "
                   "(previous skipped GTID is ignored).").format(test_num)
        cmd = "{0} --slaves={1} --gtid-set={2}".format(
            cmd_base, slaves_con, gtid_set)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Computed expected GTID_EXECUTED set for target slave.
        expected_gtids = gtid_set_union(master_gtid_executed, gtid_set)
        # Check if GTID_EXECUTED match the expected value on all slaves.
        try:
            # GTID_EXECUTED is expected to be the same using dryrun mode.
            slave_trx_skip.check_gtid_executed([self.server2, self.server3],
                                               expected_gtids)
        except UtilError as err:
            raise MUTLibError("{0}: failed\n{1}".format(comment, err.errmsg))

        test_num += 1
        comment = ("Test case {0} - Repeat previous command "
                   "(No GTIDs will be skipped).").format(test_num)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Check if GTID_EXECUTED match the expected value on all slaves.
        try:
            # GTID_EXECUTED is expected to be the same (no new GTID skipped).
            slave_trx_skip.check_gtid_executed([self.server2, self.server3],
                                               expected_gtids)
        except UtilError as err:
            raise MUTLibError("{0}: failed\n{1}".format(comment, err.errmsg))

        test_num += 1
        comment = ("Test case {0}a - [DRYRUN] Skip GTID set on all slaves "
                   "(with verbose).").format(test_num)
        gtid_set = "{0}:10-13,{1}:8,{2}:8".format(*uuids)
        cmd = "{0} --slaves={1} --gtid-set={2} --dryrun -v".format(
            cmd_base, slaves_con, gtid_set)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Check if GTID_EXECUTED match the expected value on all slaves.
        try:
            # GTID_EXECUTED is expected to be the same using dryrun mode.
            slave_trx_skip.check_gtid_executed([self.server2, self.server3],
                                               expected_gtids)
        except UtilError as err:
            raise MUTLibError("{0}: failed\n{1}".format(comment, err.errmsg))

        comment = ("Test case {0}b - Skip GTID set on all slaves "
                   "(with verbose).").format(test_num)
        cmd = "{0} --slaves={1} --gtid-set={2} -v".format(
            cmd_base, slaves_con, gtid_set)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Computed expected GTID_EXECUTED set for target slave.
        expected_gtids = gtid_set_union(expected_gtids, gtid_set)
        # Check if GTID_EXECUTED match the expected value on all slaves.
        try:
            # GTID_EXECUTED is expected to be the same using dryrun mode.
            slave_trx_skip.check_gtid_executed([self.server2, self.server3],
                                               expected_gtids)
        except UtilError as err:
            raise MUTLibError("{0}: failed\n{1}".format(comment, err.errmsg))

        # Mask non-deterministic output.
        self.replace_substring(str(self.server1.port), "PORT1")
        self.replace_substring(str(self.server2.port), "PORT2")
        self.replace_substring(str(self.server3.port), "PORT3")

        # Remove version information.
        self.remove_result_and_lines_after("MySQL Utilities mysqlslavetrx "
                                           "version", 1)

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
