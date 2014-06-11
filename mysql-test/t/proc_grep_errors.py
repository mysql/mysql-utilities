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
proc_grep_errors test.
"""

import proc_grep

from mysql.utilities.exception import MUTLibError


class test(proc_grep.test):
    """Check errors for process grep
    This test executes the process grep utility errors.
    It uses the proc_grep test as a parent for setup and teardown methods.
    """

    def check_prerequisites(self):
        return proc_grep.test.check_prerequisites(self)

    def setup(self):
        return proc_grep.test.setup(self)

    def run(self):
        self.res_fname = "result.txt"

        from_conn = self.build_connection_string(self.server1)
        conn_val = self.get_connection_values(self.server1)
        cmd_base = "mysqlprocgrep.py --server={0}".format(from_conn)

        test_num = 1
        comment = "Test case {0} - invalid --character-set".format(test_num)
        cmd = ("{0} --match-user={1} --character-set=unsupported_charset"
               "".format(cmd_base, conn_val[0]))
        res = self.run_test_case(2, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = "Test case {0} - invalid user".format(test_num)
        cmd_base = "mysqlprocgrep.py --server=nope@nada"
        cmd = ("{0} --match-user={1} "
               "".format(cmd_base, conn_val[0]))
        res = self.run_test_case(2, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        self.replace_result("ERROR: 2003: Can't connect to MySQL server",
                            "ERROR: 2003: Can't connect to XXXX\n")

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        return proc_grep.test.cleanup(self)
