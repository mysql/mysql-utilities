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
grant_show_privileges test.
"""
import show_grants
from mysql.utilities.exception import MUTLibError, UtilError


class test(show_grants.test):
    """Test permissions necessary to run mysqlgrants with.

    This test inherits from priv_show base test and shares the same
    prerequisites
    """

    def setup(self):
        self.res_fname = "result.txt"
        if self.need_server:
            try:
                self.servers.spawn_new_servers(2)
            except MUTLibError as err:
                raise MUTLibError("Cannot spawn needed servers: {0}"
                                  "".format(err.errmsg))
        self.server1 = self.servers.get_server(1)
        # Create user with no privileges on the server
        create_user_query = "CREATE USER grant_priv_test@'localhost'"
        try:
            self.server1.exec_query(create_user_query)
        except UtilError as err:
            raise MUTLibError("Failed to execute query: "
                              "{0}".format(err.errmsg))

        return True

    def run(self):
        # build custom connection string
        server_conn = self.build_custom_connection_string(self.server1,
                                                          'grant_priv_test',
                                                          '')
        cmd_base = 'mysqlgrants.py --server={0}'.format(server_conn)

        test_num = 1
        comment = ("Test case {0} - Try to use utility with user without "
                   "any privileges.".format(test_num))
        cmd = ("{0} mysql".format(cmd_base))
        res = self.run_test_case(1, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - Test utility with user with minimum "
                   "privileges.".format(test_num))
        query = "GRANT SELECT on mysql.* to grant_priv_test@localhost"
        try:
            self.server1.exec_query(query)
        except UtilError as err:
            raise MUTLibError("Failed to execute query: "
                              "{0}".format(err.errmsg))
        cmd = ("{0} mysql".format(cmd_base))
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        self.do_masks()

        return True

    def drop_all(self):
        """Drop users created during test."""
        users_to_drop = ["grant_priv_test@'localhost'", ]
        for user in users_to_drop:
            drop_stm = "DROP USER {0}".format(user)
            try:
                self.server1.exec_query(drop_stm)
            except UtilError:
                pass
        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        return self.drop_all()
