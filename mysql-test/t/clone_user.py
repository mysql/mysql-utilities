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
clone_user test.
"""

import os

import mutlib

from mysql.utilities.common.user import User
from mysql.utilities.exception import MUTLibError, UtilDBError, UtilError


class test(mutlib.System_test):
    """clone user
    This test clones a user on a single server copying all grants.
    """

    server1 = None

    def check_prerequisites(self):
        return self.check_num_servers(1)

    def setup(self):
        # Check available cloned servers and spawn one if needed.
        if self.servers.num_servers() < 2:
            try:
                self.servers.spawn_new_servers(2)
            except MUTLibError as err:
                raise MUTLibError("Cannot spawn needed servers: "
                                  "{0}".format(err.errmsg))
        # Get first cloned server (only one needed).
        self.server1 = self.servers.get_server(1)

        # Load users data for test.
        data_file = "./std_data/basic_users.sql"
        try:
            self.server1.read_and_exec_SQL(data_file, self.debug)
        except (MUTLibError, UtilError) as err:
            raise MUTLibError(
                "Failed to read commands from file {0}: {1}".format(
                    data_file, err.errmsg))
        return True

    def show_user_grants(self, user):
        """Show user grants.

        user[in]    Database user.
        """
        query = "SHOW GRANTS FOR {0}".format(user)
        try:
            res = self.server1.exec_query(query)
            if res is not None:
                for row in res:
                    self.results.append(row[0] + "\n")
        except UtilDBError as err:
            raise MUTLibError("Failed to get grants for {0}: {1}".format(
                user, err.errmsg))

    def run(self):
        self.res_fname = "result.txt"

        from_conn = "--source={0}".format(
            self.build_connection_string(self.server1))
        to_conn = "--destination={0}".format(
            self.build_connection_string(self.server1))
        cmd_str = "mysqluserclone.py {0} {1} ".format(from_conn, to_conn)

        test_num = 1
        # Test case 1 - clone a user to a single user
        comment = ("Test case {0} - clone a single user joe_pass@user to "
                   "a single user: jill@user".format(test_num))
        res = self.run_test_case(0, cmd_str + " joe_pass@user jill:duh@user",
                                 comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        self.show_user_grants("'jill'@'user'")

        # Test case 2 - clone a user to a multiple users
        test_num += 1
        comment = ("Test case {0} - clone a single user amy_nopass@user to "
                   "multiple users: jack@user and john@user".format(test_num))
        res = self.run_test_case(0, cmd_str + (" amy_nopass@user jack:duh@user"
                                               " john@user"), comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        self.show_user_grants("jack@user")
        self.show_user_grants("john@user")

        # Test case 3 - attempt to clone a non-existant user
        test_num += 1
        comment = ("Test case {0} - attempt to clone a non-existant "
                   "user".format(test_num))
        res = self.run_test_case(1, cmd_str + " nosuch@user jack@user",
                                 comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Test case 4 - attempt to clone a user to a user that already exists
        test_num += 1
        comment = ("Test case {0} - attempt to clone a user to a user that "
                   "already exists".format(test_num))
        res = self.run_test_case(1, cmd_str + " joe_pass@user joe_nopass@user",
                                 comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Test case 5 - attempt to clone a user to a user that already exists
        #               with overwrite
        test_num += 1
        self.show_user_grants("joe_nopass@user")
        comment = ("Test case {0} - attempt to clone a user to a user that "
                   "already exists with --force".format(test_num))
        res = self.run_test_case(0, cmd_str + (" joe_pass@user "
                                               "joe_nopass@user --force"),
                                 comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Now show overwritten grants
        self.show_user_grants("joe_nopass@user")

        # Now show how --include-global-privileges works.
        try:
            self.server1.exec_query("CREATE USER 'joe_pass'@'%'")
        except UtilError as err:
            raise MUTLibError("Unable to create user:{0}".format(err.errmsg))
        try:
            self.server1.exec_query("GRANT ALL ON util_test.* TO "
                                    "'joe_pass'@'%'")
        except UtilError as err:
            raise MUTLibError("Cannot create user with global "
                              "grants: {0}".format(err.errmsg))

        test_num += 1
        comment = ("Test case {0} - show clone without "
                   "--include-global-privileges".format(test_num))
        res = self.run_test_case(0, cmd_str + (" -v joe_pass@user "
                                               "joe_nopass@user --force "),
                                 comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - show clone with "
                   "--include-global-privileges".format(test_num))
        res = self.run_test_case(0,
                                 cmd_str + (" -v joe_pass@user joe_nopass@user"
                                            " --force "
                                            "--include-global-privileges"),
                                 comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        from_conn = "--source=" + self.build_connection_string(self.server1)
        cmd_str = "mysqluserclone.py {0} --force ".format(from_conn)

        test_num += 1
        comment = ("Test case {0} - clone a single user joe_pass@user to "
                   "a single user: jill@user with only source "
                   "specified".format(test_num))
        res = self.run_test_case(0, cmd_str + " joe_pass@user jill:duh@user",
                                 comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - mysqluserclone --list with "
                   "--destination".format(test_num))
        cmd_str = ("mysqluserclone.py --list --format=csv {0} {1}"
                   "".format(from_conn, to_conn))
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - mysqluserclone --dump with "
                   "--destination".format(test_num))
        cmd_str = ("mysqluserclone.py -d joe_pass@user {0} {1}".format(
            from_conn, to_conn))
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - mysqluserclone --dump user "
                   "with global privileges".format(test_num))
        cmd_str = ("mysqluserclone.py {0} -d remote@'%' ".format(
            from_conn))
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Mask known source and destination host name.
        self.replace_result("# Source on ",
                            "# Source on XXXX-XXXX: ... connected.\n")
        self.replace_result("# Destination on ",
                            "# Destination on XXXX-XXXX: ... connected.\n")
        # Mask root,localhost (should exist on all MySQL server versions).
        self.replace_result("root,localhost", "ROOT,LOCALHOST\n")
        # Remove all other root users with different hosts (not localhost).
        self.remove_result("root,")
        # Remove possible leftovers from other tests.
        self.remove_result("joe_wildcard,")
        # Mask windows output, remove single quotes around hostname
        if os.name == 'nt':
            self.replace_result("# Dumping grants for user remote@'%'",
                                "# Dumping grants for user remote@%\n")

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    @staticmethod
    def drop_user(user_name, server):
        """Drop user from database.

        user_name[in]   Database user.
        server[in]      Server instance.
        """
        user = User(server, user_name)
        if user.exists():
            res = user.drop()
            if not res:
                print("cleanup: failed to drop user {0}".format(user_name))
        return True

    def cleanup(self):
        if self.res_fname:
            os.unlink(self.res_fname)
        query = "DROP DATABASE util_test"
        try:
            self.server1.exec_query(query)
        except UtilError:
            return False
        users = ["'joe_pass'@'%'", "joe_pass@user", "'joe_nopass'@'user'",
                 "'amy_nopass'@'user'", "'jill'@'user'", "'jack'@'user'",
                 "'john'@'user'", "'joe_wildcard'@'%'", "'remote'@'%'", ]

        dropped_users = [self.drop_user(user, self.server1) for user in users]

        return all(dropped_users)
