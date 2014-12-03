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
binlog_rotate parameters test.
"""

import binlog_rotate
from binlog_rotate import binlog_file_exists

from mysql.utilities.exception import MUTLibError


class test(binlog_rotate.test):
    """Tests the rotate binlog utility
    This test executes the rotate binlog utility parameters.
    """

    def run(self):
        self.res_fname = "result.txt"
        from_conn = "--server={0}".format(
            self.build_connection_string(self.server1)
        )

        cmd_str = "mysqlbinlogrotate.py {0}".format(from_conn)

        test_num = 1
        comment = ("Test case {0} - do the help"
                   "".format(test_num))
        cmd = "{0} --help".format(cmd_str)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - rotate and verbose option (-vv)"
                   "".format(test_num))
        cmd = "{0} -vv".format(cmd_str)
        res = self.run_test_case(0, cmd, comment)
        if not res or not binlog_file_exists(self.server1_datadir,
                                             "mysql-bin.000002", self.debug):
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - rotate and min_size option (-vv)"
                   "".format(test_num))
        cmd = "{0} -vv --min-size={1}".format(cmd_str, 100)
        res = self.run_test_case(0, cmd, comment)
        if not res or not binlog_file_exists(self.server1_datadir,
                                             "mysql-bin.000003", self.debug):
            raise MUTLibError("{0}: failed".format(comment))

        # Remove version information
        self.remove_result_and_lines_after("MySQL Utilities mysqlbinlogrotate"
                                           " version", 6)

        self.replace_result(
            "# Rotating Binary log on Server: ",
            "# Rotating Binary log on Server: XXXXXX:XXXX\n"
        )

        self.replace_result(
            "# Active binlog file: ",
            "# Active binlog file: 'XXXXX-XXX:XXXXXX' (size: XXX bytes)\n"
        )

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)
