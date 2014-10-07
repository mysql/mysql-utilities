#
# Copyright (c) 2010, 2014, Oracle and/or its affiliates. All rights reserved.
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
check_index test.
"""

import os

import mutlib

from mysql.utilities.exception import MUTLibError, UtilError


class test(mutlib.System_test):
    """check indexes for duplicates and redundancies
    This test executes the check index utility on a single server.
    """

    server1 = None

    def check_prerequisites(self):
        return self.check_num_servers(1)

    def setup(self):
        self.server1 = self.servers.get_server(0)
        data_file = "std_data/index_test.sql"
        self.drop_all()
        try:
            self.server1.read_and_exec_SQL(data_file, self.debug)
        except UtilError as err:
            raise MUTLibError("Failed to read commands from file {0}: "
                              "{1}".format(data_file, err.errmsg))
        return True

    def run(self):
        self.mask_global = False  # Turn off global masks
        self.res_fname = "result.txt"

        from_conn = "--server={0}".format(
            self.build_connection_string(self.server1))

        cmd_str = "mysqlindexcheck.py {0}".format(from_conn)

        test_num = 1
        comment = ("Test case {0} - check a table without "
                   "indexes".format(test_num))
        cmd = "{0} util_test_c.t6 -vv".format(cmd_str)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - check a list of tables and "
                   "databases".format(test_num))
        cmd = "{0} util_test_c util_test_a.t1 util_test_b -vv".format(cmd_str)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - check all tables for a single "
                   "database".format(test_num))
        cmd = "{0} util_test_a -vv".format(cmd_str)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - check tables for a non-existant "
                   "database".format(test_num))
        cmd = "{0} util_test_X -vv".format(cmd_str)
        res = self.run_test_case(1, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - check indexes for a non-existant "
                   "table".format(test_num))
        cmd = "{0} nosuch.nosuch -vv".format(cmd_str)
        res = self.run_test_case(1, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - check indexes for a non-existant table "
                   "with skip option".format(test_num))
        cmd = "{0} nosuch.nosuch -vv --skip".format(cmd_str)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - check clustered indexes "
                   "redundancies".format(test_num))
        cmd = "{0} util_test_d -vv".format(cmd_str)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - check PRIMARY key against unique index "
                   "with more columns, show drops".format(test_num))
        cmd = "{0} util_test_f -vv -d".format(cmd_str)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - check redundancy in indexes with multiple "
                   "columns, include drops".format(test_num))
        cmd = "{0} util_test_g -vv -d".format(cmd_str)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Mask known source host name.
        self.replace_result("# Source on ",
                            "# Source on XXXX-XXXX: ... connected.\n")

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def drop_all(self):
        """Drops all databases.
        """
        databases = ["util_test_a", "util_test_b", "util_test_c",
                     "util_test_d", "util_test_e", "util_test_f",
                     "util_test_g"]
        for db in databases:
            try:
                self.server1.exec_query("DROP DATABASE IF EXISTS "
                                        "{0}".format(db))
            except UtilError:
                pass

    def cleanup(self):
        if self.res_fname:
            os.unlink(self.res_fname)
        self.drop_all()
        return True
