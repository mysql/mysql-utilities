#
# Copyright (c) 2013 Oracle and/or its affiliates. All rights reserved.
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

import os

import mutlib

from mysql.utilities.common.user import User
from mysql.utilities.exception import MUTLibError
from mysql.utilities.exception import UtilError


class test(mutlib.System_test):
    """clone user
    This test clones a user on a single server copying all grants.
    """

    def check_prerequisites(self):
        # Check if the required tools are accessible
        self.check_mylogin_requisites()

        return self.check_num_servers(1)

    def setup(self):
        self.server1 = self.servers.get_server(0)

        # Get connection values
        con_val = self.get_connection_values(self.server1)
        if con_val[1]:
            raise MUTLibError("The use of password in the connection string "
                              "is not supported for automatic generation of "
                              "login-path data. Please specify a user to "
                              "connect to the server that does not require a "
                              "password.")

        # Create login_path_data
        self.create_login_path_data('test_mylogin_clone_user', con_val[0],
                                    con_val[2])

        # Build connection string <login-path>[:<port>][:<socket>]
        self.server1_con_str = 'test_mylogin_clone_user'
        if con_val[3]:
            self.server1_con_str = "{0}:{1}".format(self.server1_con_str,
                                                    con_val[3])
        if con_val[4]:
            self.server1_con_str = "{0}:{1}".format(self.server1_con_str,
                                                    con_val[4])

        # Load users data
        data_file = "./std_data/basic_users.sql"
        try:
            self.server1.read_and_exec_SQL(data_file, self.debug)
        except UtilError as err:
            raise MUTLibError("Failed to read commands from file {0}: "
                              "{1}".format(data_file, err.errmsg))
        return True

    def show_user_grants(self, user):
        query = "SHOW GRANTS FOR {0}".format(user)
        try:
            res = self.server1.exec_query(query)
            if res is not None:
                for row in res:
                    self.results.append(row[0] + '\n')
        except UtilError as err:
            raise MUTLibError("Failed to get grants for {0}: "
                              "{1}.".format(user, err.errmsg))

    def run(self):
        self.res_fname = "result.txt"

        cmd_str = ("mysqluserclone.py --source={0} "
                   "--destination={0} ".format(self.server1_con_str))

        # Test case 1 - clone a user to a single user (using login-path)
        test_num = 1
        comment = ("Test case {0} - Clone one user to another "
                   "(using login-path)".format(test_num))
        res = self.run_test_case(0, cmd_str + " joe_pass@user jill:duh@user",
                                 comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        self.show_user_grants("'jill'@'user'")

        # Test case 2 - clone a user to a multiple users (using login-path)
        test_num += 1
        comment = ("Test case {0} - Clone a user to multiple users "
                   "(using login-path)".format(test_num))
        res = self.run_test_case(0,
                                 cmd_str + " amy_nopass@user " +
                                 "jack:duh@user john@user",
                                 comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        self.show_user_grants("jack@user")
        self.show_user_grants("john@user")

        # Test case 3 - clone a user with only --source (using login-path)
        test_num += 1
        cmd_str = ("mysqluserclone.py --source={0} --force ".format(
            self.server1_con_str))

        comment = ("Test case {0} - Clone one user to another (using "
                   "login-path) with only source specified".format(test_num))
        res = self.run_test_case(0, cmd_str + " joe_pass@user jill:duh@user",
                                 comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Mask known source and destination host name.
        self.replace_substring("on localhost", "on XXXX-XXXX")
        self.replace_substring("on [::1]", "on XXXX-XXXX")

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def drop_user(self, user_name, server):
        user = User(server, user_name)
        if user.exists():
            res = user.drop()
            if not res:
                print("cleanup: failed to drop user {0}".format(user_name))
        return True

    def cleanup(self):
        self.remove_login_path_data('test_mylogin_clone_user')
        if self.res_fname:
            os.unlink(self.res_fname)
        query = "DROP DATABASE util_test"
        try:
            self.server1.exec_query(query)
        except UtilError:
            return False
        users = ["'joe_pass'@'%'", "joe_pass@user", "'joe_nopass'@'user'",
                 "'amy_nopass'@'user'", "'jill'@'user'", "'jack'@'user'",
                 "'john'@'user'"]

        users_dropped = [self.drop_user(user, self.server1) for user in users]

        return all(users_dropped)
