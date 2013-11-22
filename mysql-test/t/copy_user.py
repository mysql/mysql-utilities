#
# Copyright (c) 2010, 2013, Oracle and/or its affiliates. All rights reserved.
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
from mysql.utilities.exception import MUTLibError, UtilDBError, UtilError


class test(mutlib.System_test):
    """copy user
    This test copies a user from one server to another copying all grants.
    """

    def check_prerequisites(self):
        # Need at least one server.
        self.server1 = None
        self.server2 = None
        self.need_server = False
        if not self.check_num_servers(2):
            self.need_server = True
        return self.check_num_servers(1)

    def setup(self):
        self.server1 = self.servers.get_server(0)
        if self.need_server:
            try:
                self.servers.spawn_new_servers(2)
            except MUTLibError:
                raise MUTLibError("Cannot spawn needed servers.")

        self.server2 = self.servers.get_server(1)
        self.drop_all()
        data_file = "./std_data/basic_users.sql"
        try:
            self.server1.read_and_exec_SQL(data_file, self.debug)
        except MUTLibError as err:
            raise MUTLibError(
                "Failed to read commands from file {0}: "
                "{1}".format(data_file, err.errmsg))
        return True

    def show_user_grants(self, server, user):
        query = "SHOW GRANTS FOR {0}".format(user)
        try:
            res = server.exec_query(query)
            if res is not None:
                for row in res:
                    self.results.append(row[0] + "\n")
        except UtilError:
            raise MUTLibError("Cannot get grants for {0}.".format(user))

    def run(self):
        self.res_fname = "result.txt"

        from_conn = "--source={0}".format(
            self.build_connection_string(self.server1))
        to_conn = "--destination={0}".format(
            self.build_connection_string(self.server2))
        cmd_str = "mysqluserclone.py {0} {1} ".format(from_conn, to_conn)

        # Test case 1 - copy a user to a single user
        test_num = 1
        comment = ("Test case {0} - copy a single user joe_pass@user to a "
                   "single user: jill@user".format(test_num))
        res = self.run_test_case(0, cmd_str + " joe_pass@user jill:duh@user",
                                 comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        self.show_user_grants(self.server2, "'jill'@'user'")

        # Test case 2 - copy a user to a multiple users
        test_num += 1
        comment = ("Test case {0} - copy a single user amy_nopass@user to "
                   "multiple users: jack@user and john@user".format(test_num))
        res = self.run_test_case(0,
                                 cmd_str + " amy_nopass@user " +
                                 "jack:duh@user john@user",
                                 comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        self.show_user_grants(self.server2, "jack@user")
        self.show_user_grants(self.server2, "john@user")

        # Test case 3 - attempt to copy a non-existent user
        test_num += 1
        comment = ("Test case {0} - attempt to copy a non-existent "
                   "user".format(test_num))
        res = self.run_test_case(1, cmd_str + " nosuch@user jack@user",
                                 comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Test case 4 - attempt to copy a user to a user that already exists
        test_num += 1
        comment = ("Test case {0} - attempt to copy a user to a user that "
                   "already exists".format(test_num))
        res = self.run_test_case(1, cmd_str + " joe_pass@user jill:duh@user",
                                 comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Test case 5 - attempt to copy a user to a user that already exists
        #               with overwrite
        test_num += 1
        self.show_user_grants(self.server2, "jill@user")
        comment = ("Test case {0} - attempt to copy a user to a user that "
                   "already exists with --force".format(test_num))
        res = self.run_test_case(0,
                                 cmd_str + " joe_pass@user " +
                                 "jill:duh@user --force",
                                 comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # No show overwritten grants
        self.show_user_grants(self.server2, "jill@user")

        # Now show how --include-global-privileges works.
        try:
            self.server1.exec_query("CREATE USER joe_pass@'%'")
            self.server1.exec_query("GRANT ALL ON util_test.* TO "
                                    "joe_pass@'%'")
        except UtilDBError as err:
            raise MUTLibError("Cannot create user with global grants: "
                              "{0}".format(err.errmsg))

        test_num += 1
        comment = ("Test case {0} - show clone without "
                   "--include-global-privileges".format(test_num))
        res = self.run_test_case(0,
                                 cmd_str + " -v joe_pass@user " +
                                 "joe_nopass@user --force ",
                                 comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - show clone with "
                   "--include-global-privileges".format(test_num))
        res = self.run_test_case(0,
                                 cmd_str + (" -v joe_pass@user "
                                            "joe_nopass@user --force "
                                            "--include-global-privileges"),
                                 comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        self.replace_substring("on [::1]", "on localhost")

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

    def drop_all(self):
        user_drop_lst = ["joe_pass@'%'", "joe_pass@user",
                         "'joe_nopass'@'user'", "'amy_nopass'@'user'",
                         "'jill'@'user'", "'jack'@'user'", "'john'@'user'"]

        for user in user_drop_lst:
            self.drop_user(user, self.server1)
            self.drop_user(user, self.server2)

        query = "DROP DATABASE util_test"
        try:
            self.server1.exec_query(query)
        except UtilError:
            pass
        try:
            self.server2.exec_query(query)
        except UtilError:
            pass

    def cleanup(self):
        try:
            os.unlink(self.res_fname)
        except OSError:
            pass
        self.drop_all()
        return True
