#
# Copyright (c) 2013, 2014, Oracle and/or its affiliates. All rights reserved.
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
utilities_console_errors test.
"""

import os
import shutil

import mutlib

from mysql.utilities.exception import MUTLibError


fakeutil_help_tc_5 = """Usage: mysqlfakeutil.py --option

mysqlfakeutil - a mock of an utility

Options:
  --version             show program's version number and exit
  --help                display a help message and exit
  -v, --verbose         control how much information is displayed. e.g.,
                        -v =verbose, -vv = more verbose, -vvv = debug"""


class test(mutlib.System_test):
    """ Test the warnings generated at startup for the console. Test requires
    Python 2.6.
    """

    tmp_dir = None
    path_fakeutil = None
    fakeutility = None
    util_needle = None
    options = None

    def check_prerequisites(self):
        return True

    def setup(self):
        self.tmp_dir = "tmp_scripts"
        self.util_needle = 'mysqlreplicate.py'
        if not os.path.isdir(self.tmp_dir):
            os.makedirs(self.tmp_dir)
        shutil.copyfile(os.path.join(self.utildir, self.util_needle),
                        os.path.join(self.tmp_dir, self.util_needle))
        self.fakeutility = "mysqlfakeutility.py"
        shutil.copyfile(os.path.join("std_data", self.fakeutility),
                        os.path.join(self.tmp_dir, self.fakeutility))
        # setup custom options
        PRINT_WIDTH = 75
        UTIL_PATH = self.utildir
        self.options = {
            'verbosity': "verbosity",
            'quiet': False,
            'width': PRINT_WIDTH,
            'utildir': UTIL_PATH,
            'variables': {},
            'prompt': 'mysqluc> ',
            'welcome': "WELCOME_MESSAGE",
            'goodbye': "GOODBYE_MESSAGE",
            'commands': None,
            'custom': True,  # We are using custom commands
        }

        self.path_fakeutil = os.path.join(self.tmp_dir, "mysqlfakeutil.py")
        self.write_fake_util(self.path_fakeutil,
                             ["import sys\n", "sys.exit(1)\n"])
        return True

    @staticmethod
    def write_fake_util(util_name, content):
        """Write a fake utility.
        """
        with open(util_name, "w") as file_fakeutil:
            file_fakeutil.writelines(content)
            file_fakeutil.flush()

    def run(self):
        if self.debug:
            print("\n")
        self.res_fname = "result.txt"
        hide_utils = "--hide-utils"
        add_util = "--add-util=mysqlfakeutility"
        cmd_str = 'mysqluc.py --width=77 --utildir={0} {1} {2}'

        test_num = 1
        comment = ("Test case {0} - Test {1} missing "
                   "{2} option".format(test_num, hide_utils, add_util))
        execute = "help utilities"
        command = cmd_str.format(self.tmp_dir, hide_utils, '--execute="{0}"')
        res = self.run_test_case(2, command.format(execute), comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - Test {1} with {2}"
                   " option".format(test_num, hide_utils, add_util))
        execute = "help utilities"
        params = "{0} {1}".format(hide_utils, add_util)
        command = cmd_str.format(self.tmp_dir, params, '--execute="{0}"')
        res = self.run_test_case(0, command.format(execute), comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - Test {1} option without "
                   "{2}".format(test_num, add_util, hide_utils))
        execute = "help utilities"
        command = cmd_str.format(self.tmp_dir, add_util, '--execute="{0}"')
        res = self.run_test_case(0, command.format(execute), comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - Test {1} execute --help option".format(
            test_num, add_util))
        execute = "fakeutility --help"
        params = "{0} {1}".format(hide_utils, add_util)
        command = cmd_str.format(self.tmp_dir, params, '--execute="{0}"')
        res = self.run_test_case(0, command.format(execute), comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - Test fakeutility --return-code=1".format(
            test_num))
        execute = "fakeutility --return-code=1"
        params = "{0} {1}".format(hide_utils, add_util)
        command = cmd_str.format(self.tmp_dir, params, '--execute="{0}"')
        res = self.run_test_case(0, command.format(execute), comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - Test fakeutility --return-code=2 "
                   "and no message".format(test_num))
        execute = "fakeutility  -e2 --message-error=' '"
        params = "{0} {1}".format(hide_utils, add_util)
        command = cmd_str.format(self.tmp_dir, params, '--execute="{0}"')
        res = self.run_test_case(0, command.format(execute), comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        self.replace_result(("The execution of the command returned: "
                             "python: can't open file"),
                            ("The execution of the command returned: "
                             "python: can't open file ...\n"))

        # pylint: disable=W1401
        self.replace_substring("\r", "")
        self.replace_substring("tmp_scripts\mysql", "tmp_scripts/mysql")
        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        if self.res_fname:
            os.unlink(self.res_fname)
            os.unlink(self.path_fakeutil)
            shutil.rmtree(self.tmp_dir)
        return True
