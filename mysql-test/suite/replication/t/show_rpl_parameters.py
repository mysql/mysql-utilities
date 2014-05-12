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
show_rpl_parameters test.
"""

import os

import show_rpl
import mutlib

from mysql.utilities.exception import UtilError, MUTLibError


class test(show_rpl.test):
    """show replication topology - parameter testing
    This test runs the mysqlrplshow utility on a known master-slave topology
    with a variety of parameters. It uses the show_rpl test as a parent for
    setup and teardown methods.
    """

    def check_prerequisites(self):
        return show_rpl.test.check_prerequisites(self)

    def setup(self):
        self.server_list[0] = self.servers.get_server(0)
        self.server_list[1] = self.get_server("rep_slave_show")
        if self.server_list[1] is None:
            return False
        self.server_list[2] = self.get_server("rep_master_show")
        if self.server_list[2] is None:
            return False

        self.port_repl = []
        self.port_repl.append(self.server_list[1].port)
        self.port_repl.append(self.server_list[2].port)
        return True

    def run(self):
        self.res_fname = "result.txt"

        master_str = "--master={0}".format(
            self.build_connection_string(self.server_list[2]))
        slave_str = " --slave={0}".format(
            self.build_connection_string(self.server_list[1]))

        show_rpl.test.stop_replication(self.server_list[4])
        show_rpl.test.stop_replication(self.server_list[3])
        show_rpl.test.stop_replication(self.server_list[2])
        show_rpl.test.stop_replication(self.server_list[1])

        # On Windows, we must force replication to stop.
        if os.name == 'nt':
            res = self.server_list[2].exec_query("SHOW FULL PROCESSLIST")
            for row in res:
                if row[4].lower() == "binlog dump":
                    self.server_list[2].exec_query("KILL CONNECTION "
                                                   "{0}".format(row[0]))

        cmd = "mysqlreplicate.py --rpl-user=rpl:rpl "
        try:
            self.exec_util(cmd + master_str + slave_str, self.res_fname)
        except UtilError as err:
            raise MUTLibError(err.errmsg)

        cmd = "mysqlshow_rpl.py --rpl-user=rpl:rpl "
        try:
            self.exec_util(cmd + master_str + slave_str, self.res_fname)
        except UtilError as err:
            raise MUTLibError(err.errmsg)

        cmd_str = "mysqlrplshow.py --disco=root:root " + master_str

        test_num = 1
        comment = ("Test case {0} - show topology - without "
                   "list".format(test_num))
        cmd_opts = "  --recurse "
        res = mutlib.System_test.run_test_case(self, 0, cmd_str + cmd_opts,
                                               comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = "Test case {0} - show topology - with list".format(test_num)
        cmd_opts = "  --recurse --show-list"
        res = mutlib.System_test.run_test_case(self, 0, cmd_str + cmd_opts,
                                               comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - show topology - with list and "
                   "quiet".format(test_num))
        cmd_opts = "  --recurse --quiet --show-list"
        res = mutlib.System_test.run_test_case(self, 0, cmd_str + cmd_opts,
                                               comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - show topology - with format and without "
                   "list".format(test_num))
        cmd_opts = "  --recurse --format=CSV"
        res = mutlib.System_test.run_test_case(self, 0, cmd_str + cmd_opts,
                                               comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = "Test case {0} - show topology - help".format(test_num)
        cmd_opts = " --help"
        res = mutlib.System_test.run_test_case(self, 0, cmd_str + cmd_opts,
                                               comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Remove version information
        self.remove_result_and_lines_after("MySQL Utilities mysqlrplshow "
                                           "version", 6)

        _FORMATS = ("CSV", "TAB", "GRID", "VERTICAL")
        test_num = 6
        for format_ in _FORMATS:
            comment = ("Test Case {0} : Testing show topology with {1} "
                       "format ".format(test_num, format_))
            cmd_opts = "  --recurse --show-list --format={0}".format(format_)
            res = mutlib.System_test.run_test_case(self, 0, cmd_str + cmd_opts,
                                                   comment)
            if not res:
                raise MUTLibError("{0}: failed".format(comment))

            test_num += 1

        show_rpl.test.stop_replication(self.server_list[1])

        show_rpl.test.do_replacements(self)

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        if self.res_fname:
            os.unlink(self.res_fname)
        # Kill the show_rpl_servers that are no longer used
        kill_list = ['rep_slave_show', 'rep_master_show']
        return self.kill_server_list(kill_list)
