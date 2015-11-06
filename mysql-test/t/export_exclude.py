#
# Copyright (c) 2010, 2015, Oracle and/or its affiliates. All rights reserved.
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
export_exclude test.
"""

import os

import export_parameters_def

from mysql.utilities.exception import MUTLibError


class test(export_parameters_def.test):
    """check exclude parameter for export utility
    This test executes a series of export database operations on a single
    server using a variety of exclude options. It uses the
    export_parameters_def test as a parent for setup and teardown methods.
    """

    def check_prerequisites(self):
        return export_parameters_def.test.check_prerequisites(self)

    def setup(self):
        return export_parameters_def.test.setup(self)

    def run(self):
        self.res_fname = "result.txt"

        from_conn = "--server={0}".format(
            self.build_connection_string(self.server1))

        cmd_str = ("mysqldbexport.py --skip=events,grants --no-headers {0} "
                   "--format=CSV util_test --skip-gtid".format(from_conn))

        test_num = 1
        comment = "Test case {0} - exclude by name.".format(test_num)
        cmd_opts = ("{0} --exclude=util_test.v1 "
                    "--exclude=util_test.t4".format(cmd_str))
        res = self.run_test_case(0, cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

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

        test_num += 1
        comment = ("Test case {0} - exclude using SQL LIKE "
                   "pattern.".format(test_num))
        cmd_opts = "{0} -x f% -x _4".format(cmd_str)
        res = self.run_test_case(0, cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - exclude using REGEXP "
                   "pattern.".format(test_num))
        cmd_opts = "{0} -x ^f -x 4$ --regexp".format(cmd_str)
        res = self.run_test_case(0, cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - exclude by name and SQL LIKE "
                   "pattern.".format(test_num))
        cmd_opts = ("{0} --exclude=f% --exclude=_4 -x p% --exclude=v1 "
                    "--exclude=util_test.trg".format(cmd_str))
        res = self.run_test_case(0, cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - exclude by name and REGEXP "
                   "pattern.".format(test_num))
        cmd_opts = ("{0} --exclude=^f --exclude=4$ -x ^p --exclude=v1 "
                    "--exclude=util_test.trg --regexp".format(cmd_str))
        res = self.run_test_case(0, cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - exclude everything using SQL LIKE "
                   "pattern.".format(test_num))
        cmd_opts = "{0} -x % ".format(cmd_str)
        res = self.run_test_case(0, cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

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

        comment = ("Test case {0}b - SQL LIKE VS REGEXP pattern (match entire "
                   "value VS match anywhere in value).".format(test_num))
        cmd_opts = "{0} -x 1 -x t --regexp".format(cmd_str)
        res = self.run_test_case(0, cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        export_parameters_def.test._mask_csv(self)

        # Mask known source.
        self.replace_result("# Source on localhost: ... connected.",
                            "# Source on XXXX-XXXX: ... connected.\n")
        self.replace_result("# Source on [::1]: ... connected.",
                            "# Source on XXXX-XXXX: ... connected.\n")
        # Mask GTID warning when servers with GTID enabled are used
        self.remove_result("# WARNING: The server supports GTIDs but you")

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        return export_parameters_def.test.cleanup(self)
