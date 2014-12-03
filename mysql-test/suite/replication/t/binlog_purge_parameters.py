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
binlog_purge_parameters test.
"""

import binlog_purge
from binlog_rotate import binlog_range_files_exists

from mysql.utilities.exception import MUTLibError


class test(binlog_purge.test):
    """check parameters for the binlog_purge utility
    This test executes the check index utility parameters on a single server.
    It uses the binlog_purge test as a parent for setup and teardown methods.
    """

    def setup(self):
        binlog_purge.test.setup(self)
        self.server1.exec_query("FLUSH LOGS")
        return True

    def run(self):
        self.res_fname = "result.txt"
        from_conn = "--server={0}".format(
            self.build_connection_string(self.server1))

        cmd_str = "mysqlbinlogpurge.py {0}".format(from_conn)

        test_num = 1
        comment = "Test case {0} - do the help".format(test_num)
        cmd = "{0} --help".format(cmd_str)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} -mysqlbinlogpurge with verbose (-vv)"
                   "".format(test_num))
        cmd = "{0} -vv".format(cmd_str)
        res = self.run_test_case(0, cmd, comment)
        # Binlog Files 1 and 2 must not exists
        if not res or True in binlog_range_files_exists((1, 2),
                                                        self.server1_datadir,
                                                        debug=self.debug):
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} -mysqlbinlogpurge No binlog files to purge"
                   "".format(test_num))
        cmd = "{0}".format(cmd_str)
        res = self.run_test_case(0, cmd, comment)
        # Binlog File 3 must exists, no binlog was flushed
        if not res or False in binlog_range_files_exists((3, 3),
                                                         self.server1_datadir,
                                                         debug=self.debug):
            raise MUTLibError("{0}: failed".format(comment))

        # Flush master binary logs
        self.server1.exec_query("FLUSH LOGS")

        test_num += 1
        comment = ("Test case {0} -mysqlbinlogpurge dry-run (-d)"
                   "".format(test_num))
        cmd = "{0} -d".format(cmd_str)
        res = self.run_test_case(0, cmd, comment)
        # Binlog File 3 must exists (-d used)
        if not res or False in binlog_range_files_exists((3, 3),
                                                         self.server1_datadir,
                                                         debug=self.debug):
            raise MUTLibError("{0}: failed".format(comment))

        for _ in range(3):
            self.server1.exec_query("FLUSH LOGS")

        test_num += 1
        comment = ("Test case {0} -mysqlbinlogpurge --binlog option"
                   "".format(test_num))
        cmd = "{0} --binlog={1} -vv".format(cmd_str, "mysql-bin.000004")
        res = self.run_test_case(0, cmd, comment)
        # Binlog File 3 must not exists
        if not res or True in binlog_range_files_exists((3, 3),
                                                        self.server1_datadir,
                                                        debug=self.debug):
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} -mysqlbinlogpurge --binlog option"
                   " warning not found".format(test_num))
        cmd = "{0} --binlog={1} -vv".format(cmd_str, "mysql-bin.000003")
        res = self.run_test_case(0, cmd, comment)
        # Binlog Files 4 to 7 must exists
        if not res or False in binlog_range_files_exists((4, 7),
                                                         self.server1_datadir,
                                                         debug=self.debug):
            raise MUTLibError("{0}: failed".format(comment))

        # Remove version information
        self.remove_result_and_lines_after("MySQL Utilities mysqlbinlogpurge"
                                           " version", 6)

        self.replace_result(
            "WARNING: Could not find the given binlog name: ",
            "WARNING: Could not find the given binlog name: 'mysql-bin.000003'"
            " in the binlog files listed in the server: XXXX-XXXX:XXXX\n"
        )
        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)
