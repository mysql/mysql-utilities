#
# Copyright (c) 2013, Oracle and/or its affiliates. All rights reserved.
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
import mutlib
from mysql.utilities.exception import MUTLibError
from mysql.utilities.common.tools import check_python_version


class test(mutlib.System_test):
    """ Test the warnings generated at startup for the console. Test requires
    Python 2.6.
    """

    def check_prerequisites(self):
        try:
            check_python_version((2, 6, 0), (2, 6, 99), True)
        except:
            raise MUTLibError("Test requires Python 2.6")
        return True

    def setup(self):
        return True

    def run(self):
        self.res_fname = "result.txt"

        test_num = 1
        comment = ("Test case {0} - Test for warnings at "
                   "startup".format(test_num))
        res = self.run_test_case(0, 'mysqluc.py --width=77 -e "quit"', comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        test_num += 1

        self.replace_result("Welcome to the MySQL Utilities Client",
                            "Welcome to the MySQL Utilities Client\n")
        self.replace_result("Copyright", "Copyright BLAH BLAH BLAH\n")
        self.replace_result("ERROR: The mysqlauditadmin utility",
                            "ERROR: The mysqlauditadmin utility "
                            "<PYTHON ERROR>\n")
        self.replace_result("ERROR: The mysqlauditgrep utility",
                            "ERROR: The mysqlauditgrep utility "
                            "<PYTHON ERROR>\n")

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        if self.res_fname:
            os.unlink(self.res_fname)
        return True
