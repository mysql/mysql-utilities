#
# Copyright (c) 2014, Oracle and/or its affiliates. All rights reserved.
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
binlog_purge_privileges test.
"""

import mutlib

import binlog_purge_rpl
from binlog_rotate import binlog_file_exists

from mysql.utilities.exception import MUTLibError
from mysql.utilities.common.user import change_user_privileges


class test(binlog_purge_rpl.test):
    """Tests required privileges to run the purge binlog utility
    This test verify the privileges required to execute the mysqlbinlogpurge
    utility. REPLICATION SLAVE and SUPER privileges are required to run the
    utility.
    """

    server2_datadir = None
    mask_ports = []

    def setup(self):
        super(test, self).setup()

        rows = self.server2.exec_query("SHOW VARIABLES LIKE 'datadir'")
        if not rows:
            raise MUTLibError("Unable to determine datadir of cloned server "
                              "at {0}:{1}".format(self.server2.host,
                                                  self.server2.port))
        self.server2_datadir = rows[0][1]

        return True

    def run(self):
        self.res_fname = "result.txt"

        cmd_str = "mysqlbinlogpurge.py {0}"

        slave1_conn = self.build_connection_string(self.server2).strip(' ')
        slave2_conn = self.build_connection_string(self.server3).strip(' ')
        slave3_conn = self.build_connection_string(self.server4).strip(' ')

        # Flush server binary log to have some logs to purge
        self.server2.exec_query("FLUSH LOGS")

        test_num = 0
        # run tests for server option
        test_num = self.run_set("server", test_num, cmd_str, self.server2,
                                self.server2_datadir)

        # run tests for master option
        ad_opt = "--slaves={0},{1},{2} ".format(slave1_conn, slave2_conn,
                                                slave3_conn)
        self.run_set("master", test_num, cmd_str, self.server1,
                     self.master_datadir, ad_opt=ad_opt)

        return True

    def run_set(self, option_name, test_num, cmd_str, server, datadir,
                ad_opt=""):
        """Runs a set of test for the given option.

        option_name[in]    Option to use along the server connection string
        test_num[in]       Test cane number
        cmd_str[in]        Utility module name to run
        server[in]         Server instance used to run the test
        datadir[in]        the datadir path to check
        ad_opt[in]         Additional command option

        Returns latest test case number used.
        """
        server_con = self.build_custom_connection_string(server, 'a_user',
                                                         'a_pwd')

        # Create user without any privileges.
        if self.debug:
            print("\nCreating user without any privileges on server...")
        change_user_privileges(server, 'a_user', 'a_pwd', server.host,
                               grant_list=None, revoke_list=None,
                               disable_binlog=True, create_user=True)

        # Purge binary logs using a user with no privileges.
        test_num += 1
        comment = ("Test case {0} - Purge binlog using a user without "
                   "privileges, {1} option (fail).".format(test_num,
                                                               option_name))
        cmd = cmd_str.format("--{0}={1} {2}".format(option_name, server_con,
                                                    ad_opt))
        res = self.run_test_case(1, cmd, comment)
        if not res or not binlog_file_exists(datadir, "mysql-bin.000001",
                                             self.debug):
            raise MUTLibError("{0}: failed".format(comment))

        # Grant all required privilege to user (except REPLICATION SLAVE).
        if self.debug:
            print("\nGrant all required privileges except REPLICATION SLAVE.")
        grants = ['SUPER']
        change_user_privileges(server, 'a_user', 'a_pwd', server.host,
                               grant_list=grants, revoke_list=None,
                               disable_binlog=True, create_user=False)

        # Purge binary logs using a user without REPLICATION SLAVE.
        test_num += 1
        comment = ("Test case {0} - Purge binlog using a user without "
                   "REPLICATION SLAVE, {1} option (fail).".format(test_num,
                                                                  option_name))
        cmd = cmd_str.format("--{0}={1} {2}".format(option_name, server_con,
                                                    ad_opt))
        res = self.run_test_case(1, cmd, comment)
        if not res or not binlog_file_exists(datadir, "mysql-bin.000001",
                                             self.debug):
            raise MUTLibError("{0}: failed".format(comment))

        # Grant all required privilege to user (except SUPER).
        if self.debug:
            print("\nGrant all required privileges except SUPER.")
        revokes = ['SUPER']
        grants = ['REPLICATION SLAVE']
        change_user_privileges(server, 'a_user', 'a_pwd', server.host,
                               grant_list=grants, revoke_list=revokes,
                               disable_binlog=True, create_user=False)

        # Purge binary logs using a user without REPLICATION SLAVE.
        test_num += 1
        comment = ("Test case {0} - Purge binlog using a user without "
                   "SUPER, {1} option (fail).".format(test_num, option_name))
        cmd = cmd_str.format("--{0}={1} {2}".format(option_name, server_con,
                                                    ad_opt))
        res = self.run_test_case(1, cmd, comment)
        if not res or not binlog_file_exists(datadir, "mysql-bin.000001",
                                             self.debug):
            raise MUTLibError("{0}: failed".format(comment))

        # Grant all required privilege to user (except SUPER).
        if self.debug:
            print("\nGrant all required privileges (REPLICATION SLAVE and "
                  "SUPER).")
        grants = ['SUPER']
        change_user_privileges(server, 'a_user', 'a_pwd', server.host,
                               grant_list=grants, revoke_list=None,
                               disable_binlog=True, create_user=False)

        # Purge binary logs using a user with all required privileges
        # (REPLICATION SLAVE and SUPER).
        test_num += 1
        comment = ("Test case {0} - Purge binlog using a user with required "
                   "privileges (REPLICATION SLAVE and SUPER)"
                   ", {1} option.".format(test_num, option_name))
        cmd = cmd_str.format("--{0}={1} {2}".format(option_name, server_con,
                                                    ad_opt))
        res = self.run_test_case(0, cmd, comment)
        if not res or binlog_file_exists(datadir, "mysql-bin.000001",
                                         self.debug):
            raise MUTLibError("{0}: failed".format(comment))

        # Mask results
        self.replace_substring("localhost", "XXXX-XXXX")
        p_n = 0
        for port in self.mask_ports:
            p_n += 1
            self.replace_substring(repr(port), "PORT{0}".format(p_n))

        return test_num

    def get_result(self):
        return self.compare(__name__, self.results)
