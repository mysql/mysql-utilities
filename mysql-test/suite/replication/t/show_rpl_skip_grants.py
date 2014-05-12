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
show_rpl_skip_grants test.
"""

import show_rpl

from mysql.utilities.exception import MUTLibError, UtilError

MASTER_MYSQLD = "--skip-grant-tables --log-bin"
SLAVE_MYSQLD = "{0} --report-port={1} --report-host=localhost"


class test(show_rpl.test):
    """test replication utility with --skip-grant-tables server option
    This test exercises the mysqlrplshow utility against a server
    with grants turned off. It uses the show_rpl tests for helper
    functions.
    """

    def check_prerequisites(self):
        return show_rpl.test.check_prerequisites(self)

    def setup(self):
        self.server_list[0] = self.servers.get_server(0)
        self.server_list[1] = self.get_server("master_no_grants",
                                              MASTER_MYSQLD)
        if self.server_list[1] is None:
            return False
        next_port = self.servers.view_next_port()
        self.server_list[2] = self.get_server(
            "slave1_no_grants", SLAVE_MYSQLD.format(MASTER_MYSQLD, next_port)
        )
        if self.server_list[2] is None:
            return False
        next_port = self.servers.view_next_port()
        self.server_list[3] = self.get_server(
            "slave2_no_grants", SLAVE_MYSQLD.format(MASTER_MYSQLD, next_port)
        )
        if self.server_list[3] is None:
            return False

        self.port_repl.append(self.server_list[1].port)
        self.port_repl.append(self.server_list[2].port)
        self.port_repl.append(self.server_list[3].port)

        return True

    def run(self):
        self.res_fname = "result.txt"

        master_con = self.build_connection_string(self.server_list[1])
        master_str = "--master={0}".format(master_con)

        slave1_con = self.build_connection_string(self.server_list[2])
        slave1_str = "--slave={0}".format(slave1_con)

        slave2_con = self.build_connection_string(self.server_list[3])
        slave2_str = "--slave={0}".format(slave2_con)

        test_num = 1

        cmd = "mysqlreplicate.py --rpl-user=rpl:rpl {0} {1}"
        try:
            self.exec_util(cmd.format(master_str, slave1_str), self.res_fname)
            self.exec_util(cmd.format(master_str, slave2_str), self.res_fname)
        except UtilError as err:
            raise MUTLibError(err.errmsg)

        comment = "Test case {0} - show topology".format(test_num)
        cmd_str = ("mysqlrplshow.py --disco=root:root {0} "
                   "--show-list --format=csv".format(master_str))
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        show_rpl.test.do_replacements(self)

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):

        # Kill all remaining servers (to avoid problems for other tests).
        self.kill_server("master_no_grants")
        self.kill_server("slave1_no_grants")
        self.kill_server("slave2_no_grants")

        return True
