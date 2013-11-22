#
# Copyright (c) 2010, 2013, Oracle and/or its affiliates. All rights reserved.
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

import meta_grep
from mysql.utilities.exception import MUTLibError


class test(meta_grep.test):
    """Process grep
    This test executes the meta grep utility parameters.
    It uses the meta_grep test as a parent for setup and teardown methods.
    """

    def check_prerequisites(self):
        return meta_grep.test.check_prerequisites(self)

    def setup(self):
        return meta_grep.test.setup(self)

    def run(self):
        self.res_fname = "result.txt"

        cmd_base = "mysqlmetagrep.py "

        test_num = 1
        comment = "Test case {0} - do the help".format(test_num)
        cmd = "{0} --help".format(cmd_base)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Remove version information
        self.remove_result_and_lines_after("MySQL Utilities mysqlmetagrep.py "
                                           "version", 6)

        test_num += 1
        comment = ("Test case {0} - do the SQL for a simple "
                   "search".format(test_num))
        cmd = "{0} --sql -Gb --pattern=t2".format(cmd_base)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - do the SQL for a simple search with "
                   "type".format(test_num))
        cmd = ("{0} --sql --search-objects=table -Gb "
               "--pattern=t2".format(cmd_base))
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - do the SQL for a body search with type "
                   "(VIEW).".format(test_num))
        cmd = ("{0} --sql --search-objects=view -Gb "
               "--pattern=%t1%".format(cmd_base))
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        self.mask_column_result("root:*@localhost", ",", 1, "root[...]")

        # Mask version
        self.replace_result(
                "MySQL Utilities mysqlmetagrep version",
                "MySQL Utilities mysqlmetagrep version X.Y.Z "
                "(part of MySQL Workbench ... XXXXXX)\n"
        )

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        return meta_grep.test.cleanup(self)
