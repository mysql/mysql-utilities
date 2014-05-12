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
alias test.
"""

import socket
import os

import mutlib

from mysql.utilities.exception import MUTLibError, UtilError


_MASTER_ALIASES = ['127.0.0.1', 'localhost']


class test(mutlib.System_test):
    """setup replication
    This test executes a simple replication setup among two servers to check
    the is_alias() method of the server class for comparing slave's master
    host to the master's alias list.
    """

    server0 = None
    server1 = None
    server2 = None
    s1_serverid = None
    s2_serverid = None

    def check_prerequisites(self):
        return self.check_num_servers(1)

    def setup(self):
        self.server0 = self.servers.get_server(0)
        self.server1 = None
        self.server2 = None
        self.s1_serverid = None
        self.s2_serverid = None

        index = self.servers.find_server_by_name("rep_slave")
        if index >= 0:
            self.server1 = self.servers.get_server(index)
            try:
                res = self.server1.show_server_variable("server_id")
            except MUTLibError as err:
                raise MUTLibError("Cannot get replication slave "
                                  "server_id: {0}".format(err.errmsg))
            self.s1_serverid = int(res[0][1])
        else:
            self.s1_serverid = self.servers.get_next_id()
            res = self.servers.spawn_new_server(
                self.server0, self.s1_serverid, "rep_slave",
                ' --mysqld="--log-bin=mysql-bin "')
            if not res:
                raise MUTLibError("Cannot spawn replication slave server.")
            self.server1 = res[0]
            self.servers.add_new_server(self.server1, True)

        index = self.servers.find_server_by_name("rep_master")
        if index >= 0:
            self.server2 = self.servers.get_server(index)
            try:
                res = self.server2.show_server_variable("server_id")
            except MUTLibError as err:
                raise MUTLibError("Cannot get replication master "
                                  "server_id: {0}".format(err.errmsg))
            self.s2_serverid = int(res[0][1])
        else:
            self.s2_serverid = self.servers.get_next_id()
            res = self.servers.spawn_new_server(
                self.server0, self.s2_serverid, "rep_master",
                ' --mysqld="--log-bin=mysql-bin "')
            if not res:
                raise MUTLibError("Cannot spawn replication slave server.")
            self.server2 = res[0]
            self.servers.add_new_server(self.server2, True)

        self.server1.exec_query("GRANT ALL ON *.* TO 'root'@'{0}' IDENTIFIED "
                                "BY 'root'".format(self.server1.host))

        host_ip = socket.gethostbyname_ex(socket.gethostname())
        _MASTER_ALIASES.append(host_ip[2][0])
        _MASTER_ALIASES.append(host_ip[0])

        for ip in host_ip[2]:
            self.server2.exec_query("GRANT ALL ON *.* TO 'root'@'{0}' "
                                    "IDENTIFIED BY 'root'".format(ip))
            self.server2.exec_query("GRANT REPLICATION SLAVE ON *.* TO "
                                    "'rpl'@'{0}' IDENTIFIED BY "
                                    "'rpl'".format(ip))

        for alias in _MASTER_ALIASES:
            self.server2.exec_query("GRANT ALL ON *.* TO 'root'@'{0}' "
                                    "IDENTIFIED BY 'root'".format(alias))
            self.server2.exec_query("GRANT REPLICATION SLAVE ON *.* TO "
                                    "'rpl'@'{0}' IDENTIFIED BY "
                                    "'rpl'".format(alias))

        return True

    # pylint: disable=W0221
    def run_test_case(self, master_host, comment):

        master_str = "--master=root:root@{0}:{1}".format(master_host,
                                                         self.server2.port)
        slave_str = " --slave=root:root@{0}:{1}".format(self.server1.host,
                                                        self.server1.port)
        conn_str = master_str + slave_str

        if self.debug:
            print comment

        # Stop and reset the slave
        try:
            self.server1.exec_query("STOP SLAVE")
            self.server1.exec_query("RESET SLAVE")
        except UtilError:
            raise MUTLibError("{0}: Failed to stop/reset slave.".format(
                comment))

        # Setup replication
        self.results.append('{0}\n'.format(comment))
        cmd = "mysqlreplicate.py --rpl-user=rpl:rpl {0}".format(conn_str)
        if self.debug:
            self.results.append('{0}\n'.format(comment))
        res = self.exec_util(cmd, self.res_fname)
        if res != 0:
            return False

        # Run check replication
        cmd = "mysqlrplcheck.py {0} ".format(conn_str)
        self.results.append('{0}\n'.format(cmd))
        res = self.exec_util(cmd, self.res_fname)
        with open(self.res_fname) as f:
            for line in f:
                self.results.append(line)
            self.results.append("\n")
        if res != 0:
            return False

        return True

    def run(self):
        self.res_fname = "result.txt"

        test_num = 1
        for alias in _MASTER_ALIASES:
            comment = "Test case {0} - master as {1}.".format(test_num, alias)
            res = self.run_test_case(alias, comment)
            if not res:
                raise MUTLibError("{0}: failed".format(comment))
            test_num += 1

        self.replace_substring(str(self.server1.port), "PORT1")
        self.replace_substring(str(self.server2.port), "PORT2")
        self.replace_substring("127.0.0.1", "HOSTNAME")
        self.replace_substring(_MASTER_ALIASES[2], "HOSTNAME")
        self.replace_substring(_MASTER_ALIASES[3], "HOSTNAME")

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        if self.res_fname:
            os.unlink(self.res_fname)
        return self.kill_server_list(['rep_master', 'rep_slave'])
