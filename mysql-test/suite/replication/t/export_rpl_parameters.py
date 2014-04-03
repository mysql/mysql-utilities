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
export_rpl_parameters test.
"""

import os

import replicate
import mutlib

from mysql.utilities.exception import MUTLibError


_RPL_FILE = "rpl_test.txt"
_RPL_OPTIONS = ["--comment-rpl", "--rpl-file={0}".format(_RPL_FILE)]


class test(replicate.test):
    """check --rpl parameter for export utility
    This test executes a series of export database operations on a single
    server using a variety of replication options. It uses the replicate test
    as a parent for setup and teardown methods.
    """

    def check_prerequisites(self):
        # Check MySQL server version - Must be 5.1.0 or higher
        if not self.servers.get_server(0).check_version_compat(5, 1, 0):
            raise MUTLibError("Test requires server version 5.1.0 or higher")
        self.check_gtid_unsafe()
        return replicate.test.check_prerequisites(self)

    def setup(self):
        self.res_fname = "result.txt"
        result = replicate.test.setup(self)
        if not result:
            return False

        master_str = "--master={0}".format(
            self.build_connection_string(self.server1))
        slave_str = " --slave={0}".format(
            self.build_connection_string(self.server2))
        conn_str = master_str + slave_str
        self.server2.exec_query("STOP SLAVE")
        self.server2.exec_query("RESET SLAVE")
        self.server1.exec_query("STOP SLAVE")
        self.server1.exec_query("RESET SLAVE")

        data_file = os.path.normpath("./std_data/basic_data.sql")
        try:
            self.server1.exec_query("DROP DATABASE IF EXISTS util_test")
            self.server2.exec_query("DROP DATABASE IF EXISTS util_test")
            self.server1.read_and_exec_SQL(data_file, self.debug)
            self.server2.read_and_exec_SQL(data_file, self.debug)
        except MUTLibError as err:
            raise MUTLibError("Failed to read commands from file {0}: "
                              "{1}".format(data_file, err.errmsg))

        cmd = "mysqlreplicate.py --rpl-user=rpl:rpl {0}".format(conn_str)
        try:
            self.exec_util(cmd, self.res_fname)
        except MUTLibError:
            raise

        return True

    def run(self):
        from_conn = "--server={0}".format(
            self.build_connection_string(self.server1))

        cmd_str = ("mysqldbexport.py util_test --export=both "
                   "--skip=events,grants,procedures,functions,views "
                   "--rpl-user=rpl:rpl --rpl=master {0} ".format(from_conn))

        test_num = 1
        for rpl_opt in _RPL_OPTIONS:
            comment = "Test case {0} : --rpl=master and {1}".format(test_num,
                                                                    rpl_opt)
            cmd_opts = rpl_opt
            res = mutlib.System_test.run_test_case(self, 0,
                                                   cmd_str + cmd_opts,
                                                   comment)
            if not res:
                raise MUTLibError("{0}: failed".format(comment))
            test_num += 1

        comment = "Test case {0} : --rpl=master and {1}".format(
            test_num, " ".join(_RPL_OPTIONS))
        cmd_opts = " {0}".format(" ".join(_RPL_OPTIONS))
        res = mutlib.System_test.run_test_case(self, 0, cmd_str + cmd_opts,
                                               comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        self.replace_result("CHANGE MASTER", "CHANGE MASTER <goes here>\n")
        self.replace_result("# CHANGE MASTER", "# CHANGE MASTER <goes here>\n")

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        try:
            os.unlink(_RPL_FILE)
        except OSError:
            pass
        return replicate.test.cleanup(self)
