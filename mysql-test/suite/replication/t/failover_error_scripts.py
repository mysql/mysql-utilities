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
failover_error_scripts test.
"""

import os

import failover

from mysql.utilities.exception import MUTLibError

FAILOVER_LOG = "{0}fail_log.txt"


class test(failover.test):
    """test replication failover utility
    This test exercises the mysqlfailover utility known error conditions.
    Note: this test requires GTID enabled servers.
    """

    def check_prerequisites(self):
        if os.name == "nt":
            raise MUTLibError("Test requires non-Windows platform.")
        return failover.test.check_prerequisites(self)

    def setup(self):
        return failover.test.setup(self)

    def run(self):
        self.res_fname = "result.txt"

        master_conn = self.build_connection_string(self.server1).strip(' ')

        self.test_cases = []
        self.test_results = []
        self.fail_event_script = os.path.normpath("./std_data/fail_event.sh")

        # Run once for the before script and after_script. Same logic is
        # using in the pre/post fail so we're Ok if these two cases are
        # the only ones checked. Besides, the failover test uses the post
        # fail script as part of its check.
        before_script = "'./std_data/failover_before_bad.sh'"
        after_script = "'./std_data/failover_after_bad.sh'"

        # Before script test
        test_num = 1
        master_str = "--master={0}".format(master_conn)
        failover_cmd = ("python ../scripts/mysqlfailover.py --interval=10 "
                        "--discover-slaves-login=root:root {0} --log={1} "
                        "--timeout=5 --exec-before='{2}' --exec-after='{3}' "
                        "--exec-post-fail='{4}'")
        cmd = failover_cmd.format(master_str, FAILOVER_LOG.format('1'),
                                  before_script, after_script,
                                  self.fail_event_script)
        if self.debug:
            print(cmd)

        self.test_cases.append(
            (self.server1, cmd, True, FAILOVER_LOG.format('1'),
             "Test case {0} - Before script fails".format(test_num),
             ["Before script failed!", "After script failed!"], False)
        )

        failover.test.debug = self.debug
        for test_case in self.test_cases:
            res = self.test_failover_console(test_case)
            if res is not None:
                self.test_results.append(res)
            else:
                raise MUTLibError("{0}: failed".format(test_case[4]))

        return True

    def get_result(self):
        return failover.test.get_result(self)

    def record(self):
        return True

    def cleanup(self):
        self.kill_server('rep_slave1_gtid')
        self.kill_server('rep_slave2_gtid')
        return failover.test.cleanup(self)
