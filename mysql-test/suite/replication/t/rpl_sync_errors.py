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
rpl_sync_errors test.
"""

import os

import mutlib

from mysql.utilities.exception import MUTLibError


class test(mutlib.System_test):
    """Test replication synchronization checker errors.

    This test checks the mysqlrplsync utility known error conditions.
    """

    def check_prerequisites(self):
        # No prerequisites required.
        return True

    def setup(self):
        self.res_fname = "result.txt"
        # No need to spawn any server.
        return True

    def run(self):

        cmd_base = "mysqlrplsync.py"

        test_num = 1
        comment = ("Test case {0} - slaves or discover-slaves required."
                   "").format(test_num)
        res = self.run_test_case(2, cmd_base, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - slaves and discover-slaves cannot be used "
                   "at the same time.").format(test_num)
        cmd = ("{0} --discover-slaves-login=root "
               "--slaves=root:localhost:3306").format(cmd_base)
        res = self.run_test_case(2, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - discover-slaves requires "
                   "--master.").format(test_num)
        cmd = "{0} --discover-slaves-login=root".format(cmd_base)
        res = self.run_test_case(2, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - master cannot be included in slaves."
                   "").format(test_num)
        cmd = ("{0} --slaves=root@localhost:3306,root@localhost:3307 "
               "--master=root@localhost:3306").format(cmd_base)
        res = self.run_test_case(2, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - invalid slave connection."
                   "").format(test_num)
        cmd = "{0} --slaves=root@invalid_host:3306".format(cmd_base)
        res = self.run_test_case(1, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - invalid master connection."
                   "").format(test_num)
        cmd = ("{0} --slaves=root@invalid_host:3306 "
               "--master=not_user@localhost:999999").format(cmd_base)
        res = self.run_test_case(1, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        cmd_base = "mysqlrplsync.py --slaves=root@localhost:3306"

        test_num += 1
        comment = ("Test case {0} - invalid integer for "
                   "--rpl-timeout.").format(test_num)
        cmd = "{0} --rpl-timeout=0.5".format(cmd_base)
        res = self.run_test_case(2, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - value for --rpl-timeout must be "
                   "non-negative.").format(test_num)
        cmd = "{0} --rpl-timeout=-1".format(cmd_base)
        res = self.run_test_case(2, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - invalid integer for "
                   "--checksum-timeout.").format(test_num)
        cmd = "{0} --checksum-timeout=not_a_number".format(cmd_base)
        res = self.run_test_case(2, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - value for --checksum-timeout must be "
                   "non-negative.").format(test_num)
        cmd = "{0} --checksum-timeout=-10".format(cmd_base)
        res = self.run_test_case(2, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - invalid integer for "
                   "--interval.").format(test_num)
        cmd = "{0} --interval=-0.5".format(cmd_base)
        res = self.run_test_case(2, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - value for --interval must be greater than "
                   "zero.").format(test_num)
        cmd = "{0} --interval=-0".format(cmd_base)
        res = self.run_test_case(2, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - value for --exclude cannot be "
                   "empty.").format(test_num)
        cmd = "{0} --exclude=".format(cmd_base)
        res = self.run_test_case(2, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Mask out non-deterministic data
        self.do_masks()

        return True

    def do_masks(self):
        """Masks non deterministic connection error code.
        """
        self.replace_result("ERROR: Can't connect to",
                            "ERROR Can't connect to MySQL XXXXX\n")
        self.replace_any_result(
            ["Error 2003: Can't connect to MySQL server on 'localhost'",
             "Error Can't connect to MySQL server on 'localhost:999999'"],
            "Error 2003: Can't connect to MySQL server on 'localhost'\n")

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
