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
clone_user_errors test.
"""

import os

import clone_user

from mysql.utilities.exception import MUTLibError, UtilDBError


class test(clone_user.test):
    """clone user error conditions
    This test ensures the known error conditions are tested. It uses the
    cloneuser test as a parent for setup and teardown methods.
     """
    server2 = None

    def check_prerequisites(self):
        return clone_user.test.check_prerequisites(self)

    def setup(self):
        super_setup = clone_user.test.setup(self)
        if not super_setup:
            return False
        self.server2 = self.servers.spawn_server("clone_user_errors",
                                                 kill=True, mysqld="")
        # Create accounts on destination server and give them some privileges.
        try:
            self.server2.exec_query("CREATE USER remote@'localhost'")
        except UtilDBError as err:
            print("Unable to create user remote@'localhost': "
                  "{0}".format(err.errmsg))
            return False
        try:
            self.server2.exec_query("GRANT ALL ON *.* to remote@'localhost'")
        except UtilDBError as err:
            print("Unable to grant privileges to user remote@'localhost': "
                  "{0}".format(err.errmsg))
            return False

        try:
            self.server2.exec_query("CREATE USER user1@'localhost'")
        except UtilDBError as err:
            print("Unable to create user user1@'localhost': "
                  "{0}".format(err.errmsg))
            return False
        try:
            self.server2.exec_query("GRANT SELECT ON *.* to "
                                    "user1@'localhost'")
        except UtilDBError as err:
            print("Unable to grant privileges to user user1@'localhost': "
                  "{0}".format(err.errmsg))
            return False
        return True

    def run(self):
        self.res_fname = "result.txt"

        from_conn = "--source={0}".format(
            self.build_connection_string(self.server1))
        to_conn = "--destination={0}".format(
            self.build_connection_string(self.server1))

        cmd_str = ("mysqluserclone.py "
                   "--source=noone:nope@localhost:3306 {0}".format(to_conn))

        test_num = 1
        comment = ("Test case {0} - error: invalid login to source "
                   "server".format(test_num))
        res = self.run_test_case(1, cmd_str + " a@b b@c", comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - error: invalid login to source "
                   "server with --list option".format(test_num))
        res = self.run_test_case(1, cmd_str + " --list", comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        cmd_str = ("mysqluserclone.py "
                   "--destination=noone:nope@localhost:3306 "
                   "{0}".format(from_conn))
        comment = ("Test case {0} - error: invalid login to "
                   "destination server".format(test_num))
        res = self.run_test_case(1, cmd_str + " a@b b@c", comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        cmd_str = "mysqluserclone.py {0} {1} ".format(from_conn, to_conn)
        comment = "Test case {0} - error: no arguments".format(test_num)
        res = self.run_test_case(2, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = "Test case {0} - error: no new user".format(test_num)
        res = self.run_test_case(2, cmd_str + "joenopass@localhost", comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - error: cannot use dump and "
                   "quiet together".format(test_num))
        res = self.run_test_case(2, cmd_str + (" root@localhost  x@f "
                                               "--quiet --dump"),
                                 comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        cmd_str = ("mysqluserclone.py --source=wikiwakawonky "
                   "{0} ".format(to_conn))
        comment = ("Test case {0} - error: cannot parse source "
                   "connection".format(test_num))
        res = self.run_test_case(2, cmd_str + " root@localhost x@f", comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        cmd_str = ("mysqluserclone.py "
                   "--destination=wikiwakawonky {0} ".format(from_conn))

        comment = ("Test case {0} - error: cannot parse "
                   "destination connection".format(test_num))
        res = self.run_test_case(2, cmd_str + " root@localhost x@f", comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        cmd_str = "mysqluserclone.py --list -vvv"
        comment = ("Test case {0} - error: missing source "
                   "option".format(test_num))
        res = self.run_test_case(2, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        to_conn = ("--destination=remote@localhost:"
                   "{0}".format(self.server2.port))
        cmd_str = ("mysqluserclone.py {0} {1} remote@'%' xxx:12345@localhost"
                   "".format(from_conn, to_conn))
        comment = ("Test case {0} - user from destination server does not "
                   "have enough privileges to clone".format(test_num))
        res = self.run_test_case(1, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        to_conn = ("--destination=user1@localhost:"
                   "{0}".format(self.server2.port))
        cmd_str = ("mysqluserclone.py {0} {1} remote@'%' xxx:12345@localhost"
                   "".format(from_conn, to_conn))
        comment = ("Test case {0} - user from destination server does not "
                   "have the privilege to create users".format(test_num))
        res = self.run_test_case(1, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        # give user1 the privilege to create users, however it still lacks
        # the privilege to drop users.
        try:
            self.server2.exec_query("GRANT INSERT ON mysql.* to "
                                    "user1@'localhost'")
        except UtilDBError as err:
            print("Unable to grant privileges to user user1@'localhost': "
                  "{0}".format(err.errmsg))
        to_conn = ("--destination=user1@localhost:"
                   "{0}".format(self.server2.port))
        cmd_str = ("mysqluserclone.py {0} {1} remote@'%' remote@localhost "
                   "--force".format(from_conn, to_conn))
        comment = ("Test case {0} - user from destination server does not "
                   "have the privilege to drop users".format(test_num))
        res = self.run_test_case(1, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Replace error code.
        self.replace_any_result(["Error 1045", "Error 2003",
                                 "ERROR: Can't connect to",
                                 "ERROR: Access denied for user",
                                 "Error Access denied for user"],
                                "Error XXXX: Access denied\n")

        self.replace_result("mysqluserclone: error: Source connection "
                            "values invalid",
                            "mysqluserclone: error: Source connection "
                            "values invalid\n")
        self.replace_result("mysqluserclone: error: Destination connection "
                            "values invalid",
                            "mysqluserclone: error: Destination connection "
                            "values invalid\n")
        # Mask windows output, remove single quotes around hostname
        if os.name == 'nt':
            self.replace_substring_portion("Cloning remote@'%'", "to",
                                           "Cloning remote@% to")

        # Mask known source and destination host name.
        self.replace_substring("on localhost", "on XXXX-XXXX")
        self.replace_substring("on [::1]", "on XXXX-XXXX")

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        return (self.kill_server(self.server2.role) and
                clone_user.test.cleanup(self))
