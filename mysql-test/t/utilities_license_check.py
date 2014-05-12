#
# Copyright (c) 2012, 2014, Oracle and/or its affiliates. All rights reserved.
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
utilities_license_check test.
"""

import os

import mutlib

from mysql.utilities.exception import MUTLibError
from mysql.utilities import AVAILABLE_UTILITIES


_BASE_COMMENT = "Test Case {0}: {1}"


class test(mutlib.System_test):
    """mysql utilities license check test
    This test executes tests over all utilities to verify the license
    parameter by passing the --license parameter and verify the print values.
    """

    server0 = None

    def check_prerequisites(self):
        return self.check_num_servers(0)

    def setup(self):

        return True

    def do_test(self, test_num, comment, command):
        """Do test.

        test_num[in]    Test number.
        comment[in]     Comment.
        command[in]     Command.
        """
        res = self.run_test_case(0, command,
                                 _BASE_COMMENT.format(test_num, comment))
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

    def run(self):
        self.res_fname = "result.txt"

        test_num = 1
        for utility in AVAILABLE_UTILITIES:
            cmd_opt = '--license'
            cmd_str = "{0}.py {1}".format(utility, cmd_opt)
            self.do_test(test_num, "license {0}".format(utility), cmd_str)
            test_num += 1

            cmd_opt = '--version'
            cmd_str = "{0}.py {1}".format(utility, cmd_opt)
            self.do_test(test_num, "version {0}".format(utility), cmd_str)
            test_num += 1
            self.results.append("\n")

        # Remove version information#
        for utility in AVAILABLE_UTILITIES:
            self.replace_result(
                "MySQL Utilities {0} version".format(utility),
                "MySQL Utilities {0} version X.Y.Z (part of MySQL Workbench "
                "... XXXXXX)\n".format(utility)
            )

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        if self.res_fname:
            os.unlink(self.res_fname)
        return True
