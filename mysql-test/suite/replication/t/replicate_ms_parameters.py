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
replicate_ms_parameters test.
"""

import os

import mutlib

from mysql.utilities.exception import MUTLibError


class test(mutlib.System_test):
    """Check parameters for the multi-source utility.

    This test executes the multi-source utility parameters.
    """
    def check_prerequisites(self):
        # No prerequisites required.
        return True

    def setup(self):
        return True

    def run(self):
        self.mask_global = False  # Turn off global masks
        self.res_fname = "result.txt"

        test_num = 1
        comment = "Test case {0} - show help".format(test_num)
        cmd = "mysqlrplms.py --help"
        res = mutlib.System_test.run_test_case(self, 0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = "Test case {0} - show warning".format(test_num)
        cmd = ("mysqlrplms.py --masters=root:toor@nohost,"
               "root:root@nope --slave=root:root@nada --rpl-user=rpl:rpl")
        res = mutlib.System_test.run_test_case(self, 1, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Remove version information
        self.remove_result_and_lines_after("MySQL Utilities mysqlrplms "
                                           "version", 6)
        self.replace_any_result(["ERROR: Can't connect",
                                 "Error Can't connect",
                                 "ERROR: Cannot connect"],
                                "ERROR: Can't connect to XXXX\n")

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
        return True
