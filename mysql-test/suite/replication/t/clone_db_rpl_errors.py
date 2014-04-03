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
clone_db_rpl_errors test.
"""

import clone_db

from mysql.utilities.exception import MUTLibError, UtilError


class test(clone_db.test):
    """check errors for clone db
    This test ensures the known error conditions are tested. It uses the
    clone_db test as a parent for setup and teardown methods.
    """

    def check_prerequisites(self):
        return clone_db.test.check_prerequisites(self)

    def setup(self):
        self.server1 = self.servers.get_server(0)
        try:
            self.server1.exec_query("DROP DATABASE IF EXISTS util_clone")
            self.server1.exec_query("CREATE DATABASE util_clone")
        except MUTLibError as err:
            raise MUTLibError("Failed to create test database :"
                              " {0}".format(err.errmsg))
        return True

    def run(self):
        self.server1 = self.servers.get_server(0)
        self.res_fname = "result.txt"

        from_conn = "--source={0}".format(
            self.build_connection_string(self.server1))
        to_conn = "--destination={0}".format(
            self.build_connection_string(self.server1))

        test_num = 1
        # Check --rpl option errors
        cmd_str = "mysqldbcopy.py {0} {1} util_clone:util_clone2 ".format(
            to_conn, from_conn)
        comment = "Test case {0} - error: --rpl-user=root but no --rpl".format(
            test_num)
        res = self.run_test_case(2, cmd_str + "--rpl-user=root", comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        test_num += 1

        # Attempt to use --rpl while cloning
        cmd_str = ("mysqldbcopy.py {0} {1} util_clone:util_clone2 "
                   "--rpl=slave".format(to_conn, from_conn))
        comment = "Test case {0} - error: using --rpl with cloning".format(
            test_num)
        res = self.run_test_case(2, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        try:
            self.server1.exec_query("DROP DATABASE util_clone")
            self.server1.exec_query("DROP DATABASE util_clone2")
        except UtilError:
            pass
        return True
