#
# Copyright (c) 2012, 2016, Oracle and/or its affiliates. All rights reserved.
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
utilities_console_custom_utildir test.
"""

import os
import shutil

import utilities_console_base

from mysql.utilities.exception import MUTLibError
from mysql.utilities.common import utilities as utils


_BASE_COMMENT = "Test Case {0}: "


class test(utilities_console_base.test):
    """mysql utilities console - piped commands
    This test executes tests of commands piped into mysqluc. It uses the
    utilities_console_base for test execution.
    """

    util_file = None
    util_test = None
    tmp_dir = None

    def check_prerequisites(self):
        return True

    def setup(self):
        self.tmp_dir = "tmp_scripts"
        self.util_test = 'mysqlreplicate'
        self.util_file = self.util_test
        self.util_file = self.util_test + ".py"
        if not os.path.isdir(self.tmp_dir):
            os.makedirs(self.tmp_dir)
        shutil.copyfile(os.path.join(self.utildir, self.util_test + ".py"),
                        os.path.join(self.tmp_dir, self.util_file))
        self.write_filtered_script("hello.py")
        self.write_filtered_script("mysqlhello.py")
        return True

    def write_filtered_script(self, file_name):
        """ Writes a script to be filtered.
        """
        with open(os.path.join(self.tmp_dir, file_name), "w") as f:
            f.write("pass")
            f.flush()

    def do_test(self, test_num, comment, command):
        res = self.run_test_case(0, command,
                                 _BASE_COMMENT.format(test_num) + comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        self.replace_result("Usage: mysqlreplicate",
                            "Usage: mysqlreplicate XXXXXXXXXXXXXXXXXXXXX \n")

        # Remove version information
        self.remove_result_and_lines_after("MySQL Utilities mysqlreplica", 6)

        return True

    def run(self):
        self.res_fname = "result.txt"
        test_num = 1
        comment = "Test utilities.get_util_path with custom path \n"
        self.results.append(_BASE_COMMENT.format(test_num) + comment)
        self.results.append("-----\n")
        self.results.append("Custom util path: {0}\n".format(self.tmp_dir))
        new_util_path = utils.get_util_path(self.tmp_dir)
        self.results.append(
            "returned path from get_util_path: {0}\n".format(new_util_path))
        if new_util_path != self.tmp_dir:
            raise MUTLibError("get_util_path fails to get expected path")
        self.results.append("Test Pass \n")
        self.results.append("\n")

        test_num += 1
        comment = "Show help utilities with custom utildir"
        cmd_str = 'mysqluc.py --width=77 --utildir={0} {1} '.format(
            self.tmp_dir, '--execute="{0}"')
        cmd = "help utilities"
        self.do_test(test_num, comment, cmd_str.format(cmd))

        test_num += 1
        comment = "Execute an utility --help on a custom utildir"
        cmd = self.util_test + " --help; help utilities"

        self.do_test(test_num, comment, cmd_str.format(cmd))

        # pylint: disable=W1401
        self.replace_substring("tmp_scripts\mysql", "tmp_scripts/mysql")
        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        if self.res_fname:
            try:
                os.unlink(self.res_fname)
                os.unlink(os.path.join(self.tmp_dir, self.util_file))
                shutil.rmtree(self.tmp_dir)
            except OSError as err:
                raise err
        return True
