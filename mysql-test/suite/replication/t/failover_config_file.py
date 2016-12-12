#
# Copyright (c) 2010, 2016, Oracle and/or its affiliates. All rights reserved.
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
failover test.
"""

import os
import time

import failover

from mysql.utilities.common.messages import (MSG_UTILITIES_VERSION)
from mysql.utilities.common.tools import check_python_version
from mysql.utilities.exception import MUTLibError
from mysql.utilities import VERSION_STRING


FAILOVER_LOG = "{0}fail_log.txt"
_TIMEOUT = 30
_UTILITIES_VERSION_PHRASE = MSG_UTILITIES_VERSION.format(
    utility="mysqlfailover", version=VERSION_STRING)


class test(failover.test):
    """test replication failover console with config file for Python 2.6
    testing bug for unicode strings
    """
    def check_prerequisites(self):
        if not check_python_version((2, 6, 0), (2, 6, 99), False,
                                    None, False, False, False):
            raise MUTLibError("Test requires Python 2.6.")
        return failover.test.check_prerequisites(self)

    def setup(self):
        return failover.test.setup(self)

    def run(self):
        self.res_fname = "result.txt"

        groups = [
            ('master', self.server1.port),
            ('slave1', self.server2.port),
            ('slave2', self.server3.port),
            ('slave3', self.server4.port),
        ]
        config = open("./tmp.cnf", 'w')
        for group in groups:
            config.write("[{0}]\n".format(group[0]))
            config.write("port={0}\n".format(group[1]))
            config.write("user=root\n")
            config.write("password=root\n")
            config.write("host=localhost\n")
        config.close()

        # Note: test should pass without any errors. If the start or stop
        #       timeout, the test case has failed and the log will contain
        #       the error.
        test_num = 0
        comment = "Test case {0} - test config file".format(test_num)
        if self.debug:
            print comment

        failover_cmd = ("python ../scripts/mysqlfailover.py --interval=10 "
                        " --slaves=./tmp.cnf[slave1],./tmp.cnf[slave2],"
                        "./tmp.cnf[slave3] --force --master=./tmp.cnf[master]"
                        " --log={0}".format(FAILOVER_LOG.format('1')))

        if self.debug:
            print failover_cmd

        # Launch the console in stealth mode
        proc, f_out = self.start_process(failover_cmd)

        # Wait for console to load
        if self.debug:
            print "# Waiting for console to start."
        i = 1
        time.sleep(1)
        while proc.poll() is not None:
            time.sleep(1)
            i += 1
            if i > _TIMEOUT:
                if self.debug:
                    print "# Timeout console to start."
                raise MUTLibError("{0}: failed - timeout waiting for "
                                  "console to start.".format(comment))

        # Need to poll here and wait for console to really end.
        self.stop_process(proc, f_out, True)
        # Wait for console to end
        if self.debug:
            print "# Waiting for console to end."
        i = 0
        while proc.poll() is None:
            time.sleep(1)
            i += 1
            if i > _TIMEOUT:
                if self.debug:
                    print "# Timeout console to end."
                raise MUTLibError("{0}: failed - timeout waiting for "
                                  "console to end.".format(comment))

        return True

    def get_result(self):
        return True, ''  # Not a comparative test

    def record(self):
        return True  # Not a comparative test

    def cleanup(self):
        # Kill all remaining servers (to avoid problems for other tests).
        self.kill_server('rep_slave3_gtid')
        self.kill_server('rep_slave4_gtid')

        # Remove all log files
        for log in self.log_range:
            try:
                os.unlink(FAILOVER_LOG.format(log))
            except OSError:
                pass
        try:
            os.unlink("tmp.cnf")
        except OSError:
            pass

        return failover.test.cleanup(self)
