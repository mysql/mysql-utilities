#
# Copyright (c) 2012, 2013, Oracle and/or its affiliates. All rights reserved.
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
import os
import utilities_console_base
from mysql.utilities.exception import MUTLibError

_BASE_COMMENT = "Test Case {0}: "


class test(utilities_console_base.test):
    """mysql utilities console - piped commands
    This test executes tests of commands piped into mysqluc. It uses the
    utilities_console_base for test execution.
    """

    def check_prerequisites(self):
        return True

    def setup(self):
        return True

    def do_test(self, test_num, comment, command):
        res = self.exec_util(command, self.res_fname, True)
        if comment:
            self.results.append(
                _BASE_COMMENT.format(test_num) + comment + "\n")
        self.record_results(self.res_fname)
        if res:
            raise MUTLibError("{0}: failed".format(comment))

    def run(self):
        self.res_fname = "result.txt"

        # Setup options to show
        cmd_str = 'echo "{0}" | python '
        cmd_opt = "{0}/mysqluc.py --width=77 ".format(self.utildir)

        return utilities_console_base.test.do_coverage_tests(self,
                                                             cmd_str + cmd_opt)

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        if self.res_fname:
            os.unlink(self.res_fname)
        return True
