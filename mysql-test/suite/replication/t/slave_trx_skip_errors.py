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
Test errors issued by the mysqlslavetrx utility.
"""

import os

import mutlib

from mysql.utilities.exception import MUTLibError


class test(mutlib.System_test):
    """Test errors for the transactions skip utility.

    This test checks the known error conditions for mysqlslavetrx utility.
    """

    def check_prerequisites(self):
        # No prerequisites required.
        return True

    def setup(self):
        self.res_fname = "result.txt"
        # No need to spawn any server.
        return True

    def run(self):

        cmd_base = "mysqlslavetrx.py"

        test_num = 1
        comment = ("Test case {0} - No option (gtid-set and slaves required)."
                   "").format(test_num)
        res = self.run_test_case(2, cmd_base, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - Missing slaves."
                   "").format(test_num)
        cmd = "{0} --gtid-set=gtid:1".format(cmd_base)
        res = self.run_test_case(2, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - Missing gtid-set."
                   "").format(test_num)
        cmd = "{0} --slaves=root".format(cmd_base)
        res = self.run_test_case(2, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - Invalid gtid-set."
                   "").format(test_num)
        cmd = "{0} --slaves=root --gtid-set=invalid_gtid".format(cmd_base)
        res = self.run_test_case(2, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - Invalid gtid-set (uuid)."
                   "").format(test_num)
        cmd = "{0} --slaves=root --gtid-set=invalid_uuid:1".format(cmd_base)
        res = self.run_test_case(2, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - Invalid gtid-set (interval)."
                   "").format(test_num)
        cmd = ("{0} --gtid-set=ee2655ae-2e88-11e4-b7a3-606720440b68:-1 "
               "--slaves=root").format(cmd_base)
        res = self.run_test_case(2, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - Invalid gtid-set (interval. start = end)."
                   "").format(test_num)
        cmd = ("{0} --gtid-set=ee2655ae-2e88-11e4-b7a3-606720440b68:1-1 "
               "--slaves=root").format(cmd_base)
        res = self.run_test_case(2, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - Invalid gtid-set (interval. start > end)."
                   "").format(test_num)
        cmd = ("{0} --gtid-set=ee2655ae-2e88-11e4-b7a3-606720440b68:5-1 "
               "--slaves=root").format(cmd_base)
        res = self.run_test_case(2, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - Invalid slave connection format."
                   "").format(test_num)
        cmd = ("{0} --gtid-set=ee2655ae-2e88-11e4-b7a3-606720440b68:1-5:7 "
               "--slaves=@:invalid").format(cmd_base)
        res = self.run_test_case(1, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # TODO: GTID disabled

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
