#
# Copyright (c) 2010, 2014, Oracle and/or its affiliates. All rights reserved.
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
replicate_parameters test.
"""

import replicate

from mysql.utilities.exception import MUTLibError, UtilError


class test(replicate.test):
    """check parameters for the replicate utility
    This test executes the replicate utility parameters. It uses the
    replicate test as a parent for setup and teardown methods.
    """

    def check_prerequisites(self):
        return replicate.test.check_prerequisites(self)

    def setup(self):
        return replicate.test.setup(self)

    def run(self):
        self.mask_global = False  # Turn off global masks
        self.res_fname = "result.txt"

        test_num = 1
        comment = "Test case {0} - use the test feature".format(test_num)
        res = self.run_rpl_test(self.server2, self.server1, self.s2_serverid,
                                comment, "--test-db=db_not_there_yet", True)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        try:
            self.server2.exec_query("STOP SLAVE")
        except UtilError as err:
            raise MUTLibError("Cannot stop slave: {0}".format(err.errmsg))

        test_num += 1
        comment = "Test case {0} - show the help".format(test_num)
        res = self.run_rpl_test(self.server1, self.server2, self.s1_serverid,
                                comment, "--help", True)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Remove version information
        self.remove_result_and_lines_after("MySQL Utilities mysqlreplicate "
                                           "version", 6)

        test_num += 1
        comment = "Test case {0} - use the verbose feature".format(test_num)
        res = self.run_rpl_test(self.server2, self.server1, self.s2_serverid,
                                comment, " --verbose", True)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        try:
            self.server2.exec_query("STOP SLAVE")
        except UtilError as err:
            raise MUTLibError("Cannot stop slave: {0}".format(err.errmsg))

        test_num += 1
        comment = ("Test case {0} - use the start-from-beginning "
                   "feature".format(test_num))
        res = self.run_rpl_test(self.server2, self.server1, self.s2_serverid,
                                comment, " --start-from-beginning", True)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        self.remove_result("# status:")
        self.remove_result("# error: ")
        self.remove_result("# CHANGE MASTER TO MASTER_HOST")
        self.mask_result("# master id =", "= ", "= XXX")
        self.mask_result("#  slave id =", "= ", "= XXX")
        self.replace_result("# master uuid = ",
                            "# master uuid = XXXXX\n")
        self.replace_result("#  slave uuid = ",
                            "#  slave uuid = XXXXX\n")

        # Remove status data that might appear when connection to master takes
        # more time (slower)
        self.remove_result("# IO status: Connecting to master")
        self.remove_result("# IO thread running: Connecting")
        self.remove_result("# IO error: None")
        self.remove_result("# SQL thread running: Yes")
        self.remove_result("# SQL error: None")
        self.remove_result("# Waiting for slave to synchronize with master")

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        return replicate.test.cleanup(self)
