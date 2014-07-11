#
# Copyright (c) 2014 Oracle and/or its affiliates. All rights reserved.
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
replicate_ms_errors test.
"""

import os

import mutlib

from mysql.utilities.exception import MUTLibError


class test(mutlib.System_test):
    """Test multi-source replication utility.

    This test exercises the multi-source replication utility known error
    conditions.
    It uses the replicate_ms test for setup and teardown methods.
    """

    def check_prerequisites(self):
        # No prerequisites required.
        return True

    def setup(self):
        self.res_fname = "result.txt"
        # No need to spawn any server.
        return True

    def run(self):
        self.res_fname = "result.txt"

        slave_conn = "user@slave_host:3306"
        master1_conn = "user@master1_host:3306"
        master2_conn = "user@master2_host:3306"

        test_num = 1

        comment = ("Test case {0} - error: option --slave is required"
                   "".format(test_num))
        cmd_str = ("mysqlrplms.py --masters={0} --rpl-user=rpl:rpl"
                   "".format(",".join([master1_conn, master2_conn])))
        res = self.run_test_case(2, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - error: at least two masters are required"
                   "".format(test_num))
        cmd_str = ("mysqlrplms.py --slave={0} --rpl-user=rpl:rpl"
                   "".format(slave_conn))
        res = self.run_test_case(2, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        cmd_opts = (
            "--slave={0}".format(slave_conn),
            "--masters={0}".format(",".join([master1_conn, master2_conn])),
        )

        test_num += 1
        comment = ("Test case {0} - error: invalid --report-values value"
                   "".format(test_num))
        cmd_str = ("mysqlrplms.py --report-values=unknown --rpl-user=rpl:rpl "
                   "{0}")
        res = self.run_test_case(
            2, cmd_str.format(" ".join(cmd_opts)), comment
        )
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - error: invalid --format value"
                   "".format(test_num))
        cmd_str = "mysqlrplms.py --format=unknown --rpl-user=rpl:rpl {0}"
        res = self.run_test_case(
            2, cmd_str.format(" ".join(cmd_opts)), comment
        )
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - error: interval in seconds for reporting "
                   "health is too low".format(test_num))
        cmd_str = "mysqlrplms.py --interval=3 --rpl-user=rpl:rpl {0}"
        res = self.run_test_case(
            2, cmd_str.format(" ".join(cmd_opts)), comment
        )
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - error: switchover interval in seconds for "
                   "switching masters is too low".format(test_num))
        cmd_str = ("mysqlrplms.py --switchover-interval=10 --rpl-user=rpl:rpl "
                   "{0}")
        res = self.run_test_case(
            2, cmd_str.format(" ".join(cmd_opts)), comment
        )
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - Connection error".format(test_num))
        cmd_str = "mysqlrplms.py --rpl-user=rpl:rpl {0}"
        cmd_opts = (
            "--slave=nope@notthere",
            "--masters={0}".format(",".join([master1_conn, master2_conn])),
        )
        res = self.run_test_case(
            1, cmd_str.format(" ".join(cmd_opts)), comment
        )
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - error: option --rpl-user is required"
                   "".format(test_num))
        cmd_opts = (
            "--slave={0}".format(slave_conn),
            "--masters={0}".format(",".join([master1_conn, master2_conn])),
        )
        res = self.run_test_case(
            2, "mysqlrplms.py {0}".format(" ".join(cmd_opts)), comment
        )
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        self.replace_result("ERROR: Can't connect to MySQL server on",
                            "ERROR: Can't connect to MySQL server on XXXX\n")
        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        if self.res_fname:
            try:
                os.unlink(self.res_fname)
            except OSError:
                pass
        return True
