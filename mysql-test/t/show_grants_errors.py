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
grants_show error test.
"""

import os

import mutlib

from mysql.utilities.exception import MUTLibError


class test(mutlib.System_test):
    """Test mysqlgrants errors.

    This test checks the mysqlgrants utility known error conditions.
    """

    def check_prerequisites(self):
        # No prerequisites required.
        return True

    def setup(self):
        self.res_fname = "result.txt"
        # No need to spawn any server.
        return True

    def run(self):

        cmd_base = "mysqlgrants.py"

        test_num = 1
        comment = ("Test case {0} - no server specified"
                   "").format(test_num)
        res = self.run_test_case(2, cmd_base, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - no objects specified"
                   "").format(test_num)
        cmd = "{0} --server=not_user@localhost:999999 ".format(cmd_base)
        res = self.run_test_case(2, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - Using --show=users without specifying "
                   "a privilege list."
                   "").format(test_num)
        cmd = ("{0} --server=not_user@localhost:999999 --show=users "
               "db".format(cmd_base))
        res = self.run_test_case(2, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - Invalid privilege in the privilege "
                   "list.").format(test_num)
        cmd = ("{0} --server=not_user@localhost:999999 --show=users "
               "--privileges=USAGE,NOT_A_PRIVILEGE db".format(cmd_base))
        res = self.run_test_case(2, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - invalid server connection."
                   "").format(test_num)
        cmd = "{0} --server=not_user@localhost:999999 db".format(cmd_base)
        res = self.run_test_case(1, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Mask out non-deterministic data
        self.do_masks()

        return True

    def do_masks(self):
        """Masks non deterministic connection error code.
        """
        self.replace_any_result(["ERROR: Can't connect to",
                                 "Error Can't connect to MySQL server"],
                                "ERROR Can't connect to MySQL XXXXX\n")

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
