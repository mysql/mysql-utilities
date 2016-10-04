#
# Copyright (c) 2010, 2016, Oracle and/or its affiliates. All rights reserved.
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
show_rpl_errors test.
"""

import os

import show_rpl
import mutlib

from mysql.utilities.exception import UtilError, MUTLibError


class test(show_rpl.test):
    """show replication topology - error testing
    This test runs the mysqlrplshow utility on a known master-slave topology
    with errors. It uses the show_rpl test as a parent for
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

        test_num = 1
        cmd_str = "mysqlrplshow.py --master=wikiwakawonky --disco=root:root"
        comment = ("Test case {0} - error: cannot parse master "
                   "string".format(test_num))
        res = mutlib.System_test.run_test_case(self, 2, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        cmd_str = ("mysqlrplshow.py --disco=root:root --master=wanda:fish@"
                   "localhost:{0}".format(self.server_list[0].port))
        comment = ("Test case {0} - error: invalid login to "
                   "master".format(test_num))
        res = mutlib.System_test.run_test_case(self, 1, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        show_rpl.test.stop_replication(self.server_list[4])
        show_rpl.test.stop_replication(self.server_list[3])
        show_rpl.test.stop_replication(self.server_list[2])
        show_rpl.test.stop_replication(self.server_list[1])

        cmd = "mysqlreplicate.py --rpl-user=rpl:rpl "
        try:
            self.exec_util(cmd + master_str + slave_str,
                           self.res_fname)
        except UtilError as err:
            raise MUTLibError(err.errmsg)

        test_num += 1
        cmd_str = "mysqlrplshow.py --disco=root:root {0} ".format(master_str)
        comment = "Test case {0} - show topology - bad format".format(test_num)
        cmd_opts = "  --show-list --recurse --format=XXXXXX"
        res = mutlib.System_test.run_test_case(self, 2, cmd_str + cmd_opts,
                                               comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Create a user to test error for not enough permissions
        self.server_list[2].exec_query("CREATE USER 'josh'@'localhost'")

        test_num += 1
        cmd_str = ("mysqlrplshow.py --disco=root:root --master=josh@localhost:"
                   "{0}".format(self.server_list[2].port))
        if self.server_list[2].socket is not None:
            cmd_str = "{0}:{1}".format(cmd_str, self.server_list[2].socket)

        comment = ("Test case {0}a - show topology - not enough "
                   "permissions".format(test_num))
        cmd_opts = "  --show-list --recurse "
        res = mutlib.System_test.run_test_case(self, 1, cmd_str + cmd_opts,
                                               comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        self.server_list[2].exec_query("GRANT REPLICATION SLAVE ON *.* TO "
                                       "'josh'@'localhost'")

        comment = ("Test case {0}b - show topology - not enough "
                   "permissions".format(test_num))
        cmd_opts = "  --show-list --recurse "
        res = mutlib.System_test.run_test_case(self, 0, cmd_str + cmd_opts,
                                               comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - show topology - bad "
                   "max-depth".format(test_num))
        cmd_opts = "  --show-list --recurse --max-depth=-1"
        res = mutlib.System_test.run_test_case(self, 2, cmd_str + cmd_opts,
                                               comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - show topology - large "
                   "max-depth".format(test_num))
        cmd_opts = "  --show-list --recurse --max-depth=9999"
        res = mutlib.System_test.run_test_case(self, 0, cmd_str + cmd_opts,
                                               comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - show topology - discover-slaves-login "
                   "missing".format(test_num))
        cmd_str = "mysqlrplshow.py --master=josh@localhost:{0}".format(
            self.server_list[2].port)
        cmd_opts = "  --show-list --recurse --max-depth=9999"
        res = mutlib.System_test.run_test_case(self, 2, cmd_str + cmd_opts,
                                               comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        show_rpl.test.do_replacements(self)

        self.replace_substring("Error 1045:", "Error")

        self.replace_result("mysqlrplshow: error: Master connection "
                            "values invalid",
                            "mysqlrplshow: error: Master connection "
                            "values invalid\n")

        show_rpl.test.stop_replication(self.server_list[1])

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        self.server_list[2].exec_query("DROP USER 'josh'@'localhost'")
        if self.res_fname:
            os.unlink(self.res_fname)
        kill_list = ['rep_master_show', 'rep_slave_show']
        return self.kill_server_list(kill_list)
