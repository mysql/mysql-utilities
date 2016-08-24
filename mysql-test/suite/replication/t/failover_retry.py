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
failover master retry test.
"""

import os
import subprocess
import tempfile
import time

import failover

FAILOVER_LOG = "{0}fail_log.txt"


class test(failover.test):
    """test replication failover console
    This test exercises the mysqlfailover utility master retry option.
    It uses the failover test for operation (timeout is much longer).
    """

    def run(self):
        self.res_fname = "result.txt"

        master_conn = self.build_connection_string(self.server1).strip(' ')
        slave1_conn = self.build_connection_string(self.server2).strip(' ')
        slave2_conn = self.build_connection_string(self.server3).strip(' ')
        slave3_conn = self.build_connection_string(self.server4).strip(' ')

        master_str = "--master=" + master_conn
        slaves_str = "--slaves=" + \
                     ",".join([slave1_conn, slave2_conn, slave3_conn])

        self.test_results = []
        self.test_cases = []

        failover_cmd = ("python ../scripts/mysqlfailover.py --interval=10 "
                        " --discover-slaves-login=root:root {0} --failover-"
                        'mode={1} --log={2} --exec-post-fail="' +
                        self.fail_event_script + '" --timeout=5 ' +
                        '--master-fail-retry=5 ')

        conn_str = " ".join([master_str, slaves_str])
        str_ = failover_cmd.format(conn_str, 'auto', FAILOVER_LOG.format('1'))
        str_ = "{0} --candidates={1} ".format(str_, slave1_conn)
        test_num = 1
        self.test_cases.append(
            (self.server1, str_, True, FAILOVER_LOG.format('1'),
             "Test case {0} - Simple failover with "
             "--master-fail-retry.".format(test_num),
             "Master is still not reachable.", False)
        )
        for test_case in self.test_cases:
            res = self.test_failover_console(test_case, 60)
            if res is not None:
                self.test_results.append(res)
            else:
                raise MUTLibError("{0}: failed".format(test_case[4]))

        return True
