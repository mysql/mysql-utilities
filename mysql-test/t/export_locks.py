#
# Copyright (c) 2010, 2016, Oracle and/or its affiliates. All rights reserved.
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
export_locks test.
"""

import copy_db_parameters

from mysql.utilities.exception import MUTLibError


_LOCKTYPES = ['no-locks', 'lock-all', 'snapshot']


class test(copy_db_parameters.test):
    """Export Data
    This test executes the export utility on a single server using each of the
    locking types. It uses the copy_db_parameters test to setup.
    """

    def check_prerequisites(self):
        return copy_db_parameters.test.check_prerequisites(self)

    def setup(self, spawn_servers=True):
        return copy_db_parameters.test.setup(self)

    def run(self):
        self.res_fname = "result.txt"

        from_conn = "--server={0}".format(
            self.build_connection_string(self.server1))

        cmd = "mysqldbexport.py {0} util_test --skip-gtid ".format(from_conn)

        test_num = 1
        comment = "Test case {0} - export with default locking".format(
            test_num)
        cmd_str = cmd + " --export=both --format=SQL --skip=events "
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        for locktype in _LOCKTYPES:
            test_num += 1
            comment = "Test case {0} - export data with {1} locking".format(
                test_num, locktype)
            cmd_str = cmd + " --export=data --format=SQL --locking={0}".format(
                locktype)
            res = self.run_test_case(0, cmd_str, comment)
            if not res:
                raise MUTLibError("{0}: failed".format(comment))

        self.replace_result("Time:", "Time:       XXXXXX\n")

        _REPLACEMENTS = ("PROCEDURE", "FUNCTION", "TRIGGER", "SQL")

        for replace in _REPLACEMENTS:
            self.mask_result_portion("CREATE", "DEFINER=", replace,
                                     "DEFINER=`XXXX`@`XXXXXXXXX` ")

        self.replace_substring("on [::1]", "on localhost")

        self.remove_result("# WARNING: The server supports GTIDs")

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        return copy_db_parameters.test.cleanup(self)
