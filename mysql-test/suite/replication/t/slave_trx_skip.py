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
Test the main features of the mysqlslavetrx utility.
"""

import os

import rpl_sync

from mysql.utilities.common.gtid import gtid_set_union
from mysql.utilities.exception import MUTLibError, UtilError

# Required options to enable GTIDs.
MYSQL_OPTS_DEFAULT = ('"--log-bin=mysql-bin --log-slave-updates '
                      '--enforce-gtid-consistency '
                      '--gtid-mode=on"')


def check_gtid_executed(servers, expected_gtid_set):
    """Check the GTID executed set on specified servers.

    This method checks if the GTID_EXECUTED set for all given server match
    the one specified. An UtilError is raised if one of the GTID executed sets
    does not match the expected value.

    servers[in]             List of server instances to check.
    expected_gtid_set[in]   Expected GTID_EXECUTED set.
    """
    for srv in servers:
        # Get GTID_EXECUTED and concatenate all rows (removing any newline).
        gtid_set = ''.join(srv.get_gtid_executed().splitlines())
        if gtid_set != expected_gtid_set:
            raise UtilError(
                "Unexpected GTID executed set for server {0}:{1}.\n"
                "Expected: {2}\n"
                "Found: {3}".format(srv.host, srv.port, expected_gtid_set,
                                    gtid_set))


class test(rpl_sync.test):
    """Test the mysqlslavetrx utility.

    This test runs the mysqlslavetrx utility to test its base features.
    """

    def check_prerequisites(self):
        """ Check prerequisites to execute test.

        Return True if all prerequisites are met, otherwise a MUTLibError is
        issued.
        """
        # Check required server version.
        # Reason: GTID requires servers >  5.6.9.
        if not self.servers.get_server(0).check_version_compat(5, 6, 9):
            raise MUTLibError("Test requires server version >= 5.6.9")
        return self.check_num_servers(1)

    def setup(self):
        """ Setup the test before the execution.

        Return True if the setup completes successfully, otherwise a
        MUTLibError is issued.
        """
        self.res_fname = "result.txt"

        # Spawn servers
        self.server0 = self.servers.get_server(0)
        test_servers = {}
        for srv_name in ['rpl_server1', 'rpl_server2', 'rpl_server3']:
            srv = self.servers.spawn_server(srv_name, MYSQL_OPTS_DEFAULT,
                                            True)
            uuid = srv.get_server_uuid()
            test_servers[uuid] = srv

        # Sort UUIDs alphabetically to set servers to use as master and slaves,
        # ensuring that master_uuid < slave1_uuid < slave2_uuid.
        # Note: Technique used to remove non-determinism of the test output.
        # GTIDs are always retrieved from server variable in alphabetic order
        # (of the UUID sets).
        sorted_uuids = sorted(test_servers.keys())
        self.server1 = test_servers[sorted_uuids[0]]
        self.server2 = test_servers[sorted_uuids[1]]
        self.server3 = test_servers[sorted_uuids[2]]

        # Reset spawned servers (clear binary log and GTID_EXECUTED set)
        self.reset_master([self.server1, self.server2, self.server3])

        # Set replication topology.
        self.reset_topology([self.server2, self.server3])

        return True

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
        comment = ("Test case {0} - Skip specified GTIDs on all slaves"
                   ".").format(test_num)
        gtid_set = "{0}:7,{1}:7,{2}:7".format(*uuids)
        cmd = "{0} --slaves={1} --gtid-set={2}".format(cmd_base, slaves_con,
                                                       gtid_set)
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
            check_gtid_executed([self.server2, self.server3], expected_gtids)
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

    def cleanup(self):
        """Cleanup at the end of the test execution.

        Return True if the cleanup succeeds.
        """
        if self.res_fname:
            try:
                os.unlink(self.res_fname)
            except OSError:
                pass
        # Kill all spawned servers.
        self.kill_server_list(
            ['rpl_server1', 'rpl_server2', 'rpl_server3']
        )
        return True
