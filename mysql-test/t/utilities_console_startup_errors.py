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
utilities_console_startup_errors test.
"""

import os
import sys

import mutlib

from mysql.utilities.command.utilitiesconsole import Utilities


class test(mutlib.System_test):
    """ Test the warnings generated at startup for the console. Test requires
    Python 2.6.
    """

    path_fakeutil = None
    options = None

    def check_prerequisites(self):
        return True

    def setup(self):
        # setup custom options
        PRINT_WIDTH = 75
        UTIL_PATH = "/scripts"
        self.options = {
            'verbosity': "verbosity",
            'quiet': "quiet",
            'width': PRINT_WIDTH,
            'utildir': UTIL_PATH,
            'variables': "build_variable_dictionary_list(args)",
            'prompt': 'mysqluc> ',
            'welcome': "WELCOME_MESSAGE",
            'goodbye': "GOODBYE_MESSAGE",
            'commands': None,
            'custom': True,  # We are using custom commands
        }

        self.path_fakeutil = os.path.join(os.getcwd(), "mysqlfakeutil.py")
        self.write_fake_util(self.path_fakeutil,
                             ["import sys\n", "sys.exit(1)\n"])
        return True

    @staticmethod
    def write_fake_util(util_name, content):
        """Write a fake utility.

        util_name[in]     Util name.
        content[in]       Content.
        """
        with open(util_name, "w") as file_fakeutil:
            file_fakeutil.writelines(content)
            file_fakeutil.flush()

    def run(self):
        self.res_fname = "result.txt"
        bkp_stdout = sys.stdout
        sys.stdout = open(os.path.join(os.getcwd(), self.res_fname), 'w')
        utils = Utilities(self.options)

        test_num = 1
        comment = ("Test case {0} - Test error with non-existent "
                   "utility".format(test_num))
        print(comment)
        cmd = ["python", os.path.join(os.getcwd(), "../scripts/mysqlnotexst")]
        util_name = "mysqlnotexst"
        utils.get_util_info(cmd, util_name)

        test_num += 1
        comment = ("Test case {0} - Test error with wrong "
                   "parameter".format(test_num))
        print(comment)
        utils = Utilities(self.options)
        cmd = ["python", os.path.join(os.getcwd(), "../scripts/mysqldiff.py"),
               "--unreal_option"]
        util_name = "mysqldiff"
        utils.get_util_info(cmd, util_name)

        test_num += 1
        comment = ("Test case {0} - Test errorcode returned, and no "
                   "message.".format(test_num))
        print(comment)
        utils = Utilities(self.options)
        cmd = ["python", os.path.join(os.getcwd(), "mysqlfakeutil.py"),
               "--unreal_option"]
        util_name = "mysqlfakeutil"
        utils.get_util_info(cmd, util_name)

        test_num += 1
        self.write_fake_util(self.path_fakeutil,
                             ["import sys\n", "sys.exit(0)\n"])
        comment = ("Test case {0} - Test error trying to parse help from the "
                   "utility".format(test_num))
        print(comment)
        utils = Utilities(self.options)
        cmd = ["python", os.path.join(os.getcwd(), "mysqlfakeutil.py"),
               "--unreal_option"]
        util_name = "mysqlfakeutil"
        utils.get_util_info(cmd, util_name)

        sys.stdout.flush()
        sys.stdout.close()
        sys.stdout = bkp_stdout
        with open(os.path.join(os.getcwd(), self.res_fname)) as file_res:

            self.results = [line.replace("\r", "")
                            for line in file_res.readlines()]

            self.replace_any_result([("The execution of the command "
                                      "returned: /"),
                                     ("The execution of the command "
                                      "returned: python: can't open file")],
                                    ("The execution of the command "
                                     "returned: python: can't open file "
                                     "...\n"))

        if self.debug:
            print("\n")
            for res in self.results:
                print(res.replace("\n", ""))
        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        if self.res_fname:
            os.unlink(self.res_fname)
            os.unlink(self.path_fakeutil)
        return True
