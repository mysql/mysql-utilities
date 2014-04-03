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
show_rpl test.
"""

import os

import mutlib

from mysql.utilities.exception import UtilError, MUTLibError


class test(mutlib.System_test):
    """show replication topology
    This test runs the mysqlrplshow utility on a known master-slave topology
    to print the topology.
    """

    server_list = None
    port_repl = None

    def check_prerequisites(self):
        self.server_list = [None, None, None, None, None, None, None]
        self.port_repl = []
        return self.check_num_servers(1)

    def get_server(self, name, mysqld_params=None):
        """Gets a server instance by name.

        name[in]              Name.
        mysqld_params[in]     MySQL server parameters.
        """
        serverid = self.servers.get_next_id()
        if not mysqld_params:
            new_port = self.servers.view_next_port()
            mysqld_params = (' --mysqld="--log-bin=mysql-bin '
                             ' --report-host=localhost '
                             '--report-port={0}"'.format(new_port))
        res = self.servers.spawn_new_server(self.server_list[0], serverid,
                                            name, mysqld_params)
        if not res:
            raise MUTLibError("Cannot spawn replication slave server.")
        server = res[0]
        self.servers.add_new_server(server, True)

        return server

    def setup(self):
        self.server_list[0] = self.servers.get_server(0)
        self.server_list[1] = self.get_server("rep_slave_show")
        if self.server_list[1] is None:
            return False
        self.server_list[2] = self.get_server("rep_master_show")
        if self.server_list[2] is None:
            return False
        self.server_list[3] = self.get_server("rep_relay_slave")
        if self.server_list[3] is None:
            return False
        self.server_list[4] = self.get_server("slave_leaf")
        if self.server_list[4] is None:
            return False
        self.server_list[5] = self.get_server("multi_master1")
        if self.server_list[5] is None:
            return False
        self.server_list[6] = self.get_server("multi_master2")
        if self.server_list[6] is None:
            return False
        self.port_repl.append(self.server_list[1].port)
        self.port_repl.append(self.server_list[2].port)
        self.port_repl.append(self.server_list[3].port)
        self.port_repl.append(self.server_list[4].port)
        self.port_repl.append(self.server_list[5].port)
        self.port_repl.append(self.server_list[6].port)

        return True

    def run(self):
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

        comment = ("Test case {0} - show topology of master with no "
                   "slaves".format(test_num))
        cmd_str = ("mysqlrplshow.py --disco=root:root {0} "
                   "--show-list --recurse".format(master_str))
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

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

        test_num += 1

        comment = "Test case {0} - show topology".format(test_num)
        cmd_str = ("mysqlrplshow.py --disco=root:root {0} "
                   "--show-list --recurse".format(master_str))
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1

        comment = ("Test case {0} - show topology with "
                   "--max-depth".format(test_num))
        cmd_str = ("mysqlrplshow.py --disco=root:root {0} "
                   "--show-list --recurse --max-depth=1".format(master_str))
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        try:
            circle_master = " --master={0}".format(slave_leaf_con)
            circle_slave = " --slave={0}".format(master_con)
            self.exec_util(cmd.format(circle_master, circle_slave),
                           self.res_fname)
        except UtilError as err:
            raise MUTLibError(err.errmsg)

        test_num += 1

        comment = ("Test case {0} - show topology with circular "
                   "replication".format(test_num))
        cmd_str = ("mysqlrplshow.py --disco=root:root {0} "
                   "--show-list --recurse".format(master_str))
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1

        comment = ("Test case {0} - show circular topology with verbose "
                   "option".format(test_num))
        cmd_str = ("mysqlrplshow.py --disco=root:root {0} "
                   "--show-list --recurse --verbose".format(master_str))
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Create a master:master topology
        multi_master1_con = self.build_connection_string(self.server_list[5])
        multi_master2_con = self.build_connection_string(self.server_list[6])
        cmd = "mysqlreplicate.py --rpl-user=rpl:rpl --master={0} --slave={1}"
        try:
            self.exec_util(cmd.format(multi_master1_con, multi_master2_con),
                           self.res_fname)
            self.exec_util(cmd.format(multi_master2_con, multi_master1_con),
                           self.res_fname)
        except UtilError as err:
            raise MUTLibError(err.errmsg)

        test_num += 1

        comment = ("Test case {0} - show topology with master:master "
                   "replication".format(test_num))
        cmd_str = ("mysqlrplshow.py --disco=root:root --master={0} "
                   "--show-list --recurse".format(multi_master1_con))
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Here we need to kill one of the servers to show that the
        # phantom server error from a stale SHOW SLAVE HOSTS is
        # fixed and the slave does *not* show on the graph.

        self.servers.stop_server(self.server_list[4])
        self.servers.remove_server(self.server_list[4])
        self.server_list[4] = None

        test_num += 1

        # This shows there is indeed stale data in the view
        res = self.server_list[3].exec_query("SHOW SLAVE HOSTS")
        self.results.append("Test case {0} : SHOW SLAVE HOSTS contains {1} "
                            "row.\n".format(test_num, len(res)))

        comment = ("Test case {0} - show topology with phantom "
                   "slave".format(test_num))
        cmd_str = ("mysqlrplshow.py --disco=root:root {0}"
                   "--show-list".format(relay_slave_master))
        res = self.run_test_case(0, cmd_str, comment)

        self.do_replacements()

        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        for i in range(6, 0, -1):
            self.stop_replication(self.server_list[i])

        return True

    def do_replacements(self):
        """Do replacements in the result.
        """
        self.replace_substring(" (28000)", "")
        self.replace_substring("127.0.0.1", "localhost")
        i = 1
        for port in self.port_repl:
            self.replace_substring("{0}".format(port), "PORT{0}".format(i))
            i += 1
        # Remove non-deterministic messages (do not appear on all platforms)
        self.replace_result("Error connecting to a slave",
                            "Error connecting to a slave ...\n")

        self.replace_any_result(
            ["Error 2002: Can't connect to", "Error 2003: Can't connect to",
             "Error Can't connect to MySQL server on "],
            "Error ####: Can't connect to local MySQL server\n")

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    @staticmethod
    def stop_replication(server):
        """Stops replication.

        server[in]     Server instance.
        """
        if server is not None:
            server.exec_query("STOP SLAVE")
            server.exec_query("RESET SLAVE")
            server.exec_query("RESET MASTER")

    def cleanup(self):
        if self.res_fname:
            os.unlink(self.res_fname)
        # Kill the servers that are only for this test.
        kill_list = ['rep_relay_slave', 'multi_master1', 'rep_master_show',
                     'multi_master2', 'rep_slave_show']
        return self.kill_server_list(kill_list)
