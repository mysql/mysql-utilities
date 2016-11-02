#
# Copyright (c) 2016, Oracle and/or its affiliates. All rights reserved.
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
show_rpl_socket test.
"""

import os

import show_rpl

from mysql.utilities.exception import UtilError, MUTLibError


class test(show_rpl.test):
    """show replication topology
    This test runs the mysqlrplshow utility on a known master-slave topology
    to print the topology using sockets.
    """

    server_list = None
    port_repl = None

    def check_prerequisites(self):
        if os.name == "nt":
            raise MUTLibError("Test requires non-Windows platform.")
        return show_rpl.test.check_prerequisites(self)

    def setup(self):
        return show_rpl.test.setup(self)

    def run(self):
        self.mask_global = False  # Turn off global masks
        self.res_fname = "result.txt"

        master_con = self.build_connection_string(self.server_list[2])
        master_str = "--master={0}".format(master_con)

        slave_con = self.build_connection_string(self.server_list[1])
        slave_str = "--slave={0}".format(slave_con)

        relay_slave_con = self.build_connection_string(self.server_list[3])
        relay_slave_slave = "--slave={0}".format(relay_slave_con)
        relay_slave_master = "--master={0}".format(relay_slave_con)

        slave_leaf_con = self.build_connection_string(self.server_list[4])
        slave_leaf = " --slave={0}".format(slave_leaf_con)

        test_num = 1
        cmd = "mysqlreplicate.py --rpl-user=rpl:rpl {0} {1}"
        try:
            self.exec_util(cmd.format(master_str, slave_str),
                           self.res_fname)
            self.exec_util(cmd.format(master_str, relay_slave_slave),
                           self.res_fname)
            self.exec_util(cmd.format(relay_slave_master, slave_leaf),
                           self.res_fname)
        except UtilError as err:
            raise MUTLibError(err.errmsg)

        master_socket = self.server_list[2].show_server_variable('socket')
        self.server_list[2].exec_query("SET sql_log_bin = 0")
        try:
            self.server_list[2].exec_query("DROP USER 'root_me'@'localhost'")
        except:
            pass   # Ok if user doesn't exist
        self.server_list[2].exec_query("CREATE USER 'root_me'@'localhost'")
        self.server_list[2].exec_query("GRANT ALL ON *.* TO "
                                       "'root_me'@'localhost'")
        self.server_list[2].exec_query("SET sql_log_bin = 1")
        self.create_login_path_data('test_master_socket', 'root_me',
                                    'localhost', None,
                                    "'{0}'".format(master_socket[0][1]))
        cmd_str = ("mysqlrplshow.py --disco=root:root "
                   "--master=test_master_socket --show-list")
        comment = ("Test case {0} - show list with socket"
                   "".format(test_num))
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        show_rpl.test.do_replacements(self)

        for i in range(6, 0, -1):
            self.stop_replication(self.server_list[i])

        self.remove_login_path_data('test_master_socket')

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        return show_rpl.test.cleanup(self)
