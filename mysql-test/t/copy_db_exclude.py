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
copy_db_exclude test.
"""

import os

import copy_db

from mysql.utilities.exception import MUTLibError


class test(copy_db.test):
    """check exclude parameter for clone db
    This test executes a series of clone database operations on a single
    server using a variety of --exclude options. It uses the copy_db test
    as a parent for setup and teardown methods.
    """

    def check_prerequisites(self):
        return copy_db.test.check_prerequisites(self)

    def setup(self):
        return copy_db.test.setup(self)

    def run(self):
        self.res_fname = "result.txt"

        from_conn = "--source={0}".format(
            self.build_connection_string(self.server1))
        to_conn = "--destination={0}".format(
            self.build_connection_string(self.server2))

        cmd_str = ("mysqldbcopy.py --skip-gtid {0} {1} --skip=grants "
                   "{2}".format(from_conn, to_conn, "util_test:util_db_clone"))

        test_num = 1
        comment = "Test case {0} - exclude by name".format(test_num)
        cmd_opts = ("{0} --exclude=util_test.v1 "
                    "--exclude=util_test.t4".format(cmd_str))
        res = self.run_test_case(0, cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        self.drop_db(self.server2, 'util_db_clone')

        test_num += 1
        comment = ("Test case {0} - exclude by name using "
                   "backticks.".format(test_num))
        if os.name == 'posix':
            cmd_opts = ("{0} --exclude='`util_test`.`v1`' "
                        "--exclude='`util_test`.`t4`'".format(cmd_str))
        else:
            cmd_opts = ('{0} --exclude="`util_test`.`v1`" '
                        '--exclude="`util_test`.`t4`"'.format(cmd_str))
        res = self.run_test_case(0, cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        self.drop_db(self.server2, 'util_db_clone')

        test_num += 1
        comment = ("Test case {0} - exclude using SQL LIKE "
                   "pattern.".format(test_num))
        cmd_opts = "{0} --exclude=e% --exclude=_4".format(cmd_str)
        res = self.run_test_case(0, cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        self.drop_db(self.server2, 'util_db_clone')

        test_num += 1
        comment = ("Test case {0} - exclude using REGEXP "
                   "pattern.".format(test_num))
        cmd_opts = "{0} --exclude=^e --exclude=4$ --regexp".format(cmd_str)
        res = self.run_test_case(0, cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        self.drop_db(self.server2, 'util_db_clone')

        test_num += 1
        comment = ("Test case {0} - exclude by name and SQL LIKE "
                   "pattern.".format(test_num))
        cmd_opts = ("{0} --exclude=e% --exclude=_4 "
                    "--exclude=v1 --exclude=util_test.trg".format(cmd_str))
        res = self.run_test_case(0, cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        self.drop_db(self.server2, 'util_db_clone')

        test_num += 1
        comment = ("Test case {0} - exclude by name and REGEXP "
                   "pattern.".format(test_num))
        cmd_opts = ("{0} --exclude=^e --exclude=4$ --regexp "
                    "--exclude=v1 --exclude=util_test.trg".format(cmd_str))
        res = self.run_test_case(0, cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        self.drop_db(self.server2, 'util_db_clone')

        test_num += 1
        comment = ("Test case {0} - exclude everything using SQL LIKE "
                   "pattern.".format(test_num))
        cmd_opts = "{0} -x % ".format(cmd_str)
        res = self.run_test_case(0, cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        self.drop_db(self.server2, 'util_db_clone')

        test_num += 1
        comment = ("Test case {0} - exclude everything using REGEXP "
                   "pattern.".format(test_num))
        if os.name == 'posix':
            cmd_opts = "{0} -x '.*' --regexp".format(cmd_str)
        else:
            cmd_opts = '{0} -x ".*" --regexp'.format(cmd_str)
        res = self.run_test_case(0, cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        self.drop_db(self.server2, 'util_db_clone')

        # Note: Unlike SQL LIKE pattern that matches the entire value, with a
        # SQL REGEXP pattern match succeeds if the pattern matches anywhere in
        # the value being tested.
        # See: http://dev.mysql.com/doc/en/pattern-matching.html
        test_num += 1
        comment = ("Test case {0}a - SQL LIKE VS REGEXP pattern (match entire "
                   "value VS match anywhere in value).".format(test_num))
        cmd_opts = "{0} -x 1 -x t".format(cmd_str)
        res = self.run_test_case(0, cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        self.drop_db(self.server2, 'util_db_clone')

        comment = ("Test case {0}b - SQL LIKE VS REGEXP pattern (match entire "
                   "value VS match anywhere in value).".format(test_num))
        # Exclude all tables except table t5, because view v2 depends on it
        quotes = '"' if os.name == 'nt' else ''
        cmd_opts = "{0} -x 1 -x {1}t[^5]{1} --regexp".format(cmd_str, quotes)
        res = self.run_test_case(0, cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Mask known source and destination host name.
        self.replace_result("# Source on ",
                            "# Source on XXXX-XXXX: ... connected.\n")
        self.replace_result("# Destination on ",
                            "# Destination on XXXX-XXXX: ... connected.\n")

        # Ignore GTID messages (skipping GTIDs in this test)
        self.remove_result("# WARNING: The server supports GTIDs")

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        return copy_db.test.cleanup(self)
