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
clone_db_exclude test.
"""

import clone_db

from mysql.utilities.exception import MUTLibError


class test(clone_db.test):
    """check exclude parameter for clone db
    This test executes a series of clone database operations on a single
    server using a variety of --exclude options. It uses the clone_db test
    as a parent for setup and teardown methods.
    """

    def check_prerequisites(self):
        return clone_db.test.check_prerequisites(self)

    def setup(self):
        return clone_db.test.setup(self)

    def run(self):
        self.server1 = self.servers.get_server(0)
        self.res_fname = "result.txt"

        from_conn = "--source={0}".format(
            self.build_connection_string(self.server1))
        to_conn = "--destination={0}".format(
            self.build_connection_string(self.server1))

        cmd_str = "mysqldbcopy.py --skip-gtid {0} {1} --skip=grants ".format(
            from_conn, to_conn)
        cmd_str = "{0}util_test:util_db_clone ".format(cmd_str)

        test_num = 1
        comment = "Test case {0} - exclude by name".format(test_num)
        cmd_opts = "--exclude=util_test.v1 --exclude=util_test.t4"
        res = self.run_test_case(0, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        self.drop_db(self.server1, 'util_db_clone')

        test_num += 1
        comment = "Test case {0} - exclude by regex".format(test_num)
        cmd_opts = "--exclude=^e --exclude=4$ --regex "
        res = self.run_test_case(0, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        self.drop_db(self.server1, 'util_db_clone')

        test_num += 1
        comment = "Test case {0} - exclude by name and regex".format(test_num)
        cmd_opts = ("--exclude=^e --exclude=4$ --regex "
                    "--exclude=v1 --exclude=util_test.trg")
        res = self.run_test_case(0, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Mask known source and destination host name.
        self.replace_result("# Source on ",
                            "# Source on XXXX-XXXX: ... connected.\n")
        self.replace_result("# Destination on ",
                            "# Destination on XXXX-XXXX: ... connected.\n")

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        return clone_db.test.cleanup(self)
