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
grants_show test.
"""
import os

import mutlib

from mysql.utilities.exception import MUTLibError, UtilError


class test(mutlib.System_test):
    """Test mysqlgrants basic usage.

    This test runs the mysqlgrants utility to test its features.
    """
    server1 = None
    need_server = False

    def check_prerequisites(self):
        # The utility itself works with 5.1 servers, and although the output
        # produced by the tests with a 5.1 server is still correct, it does not
        # match the one for 5.5 and 5.6 servers because the number and name of
        # root users is different. Normalizing the results would
        # require masking a big part of the output which might in turn cause
        # some issues to pass unnoticed. So we decided to run the test only
        # from version 5.5 onwards.

        if not self.servers.get_server(0).check_version_compat(5, 5, 0):
            raise MUTLibError("Test requires server version 5.5")

        if not self.check_num_servers(2):
            self.need_server = True
        return self.check_num_servers(1)

    def setup(self):
        self.res_fname = "result.txt"
        if self.need_server:
            try:
                self.servers.spawn_new_servers(2)
            except MUTLibError as err:
                raise MUTLibError("Cannot spawn needed servers: {0}"
                                  "".format(err.errmsg))
        self.server1 = self.servers.get_server(1)

        # Cleanup databases
        self.drop_all()

        # Load test databases
        data_file = os.path.normpath("./std_data/basic_data.sql")
        try:
            self.server1.read_and_exec_SQL(data_file, self.debug)
        except UtilError as err:
            raise MUTLibError("Failed to read commands from file {0}: {1}"
                              "".format(data_file, err.errmsg))

        data_file_backticks = os.path.normpath("./std_data/backtick_data.sql")
        try:
            self.server1.read_and_exec_SQL(data_file_backticks, self.debug)
        except UtilError as err:
            raise MUTLibError("Failed to read commands from file {0}: {1}"
                              "".format(data_file_backticks, err.errmsg))

        # Create users for the test
        create_user_stms = ["CREATE USER priv_test_user@'%'",
                            "CREATE USER priv_test_user2@'%'",
                            ]
        for user_stm in create_user_stms:
            try:
                self.server1.exec_query(user_stm)
            except UtilError as err:
                raise MUTLibError("Failed to execute query: "
                                  "{0}".format(err.errmsg))

        # Setup grant privileges for tests
        grant_stms = [
            "GRANT SELECT, UPDATE on *.* to priv_test_user@'%'",
            "GRANT SELECT, UPDATE, EXECUTE on *.* to priv_test_user2@'%'",
            "GRANT INSERT, CREATE TEMPORARY TABLES on `db``:db`.* to "
            "priv_test_user@'%' WITH GRANT OPTION",
            "GRANT ALL on `db``:db`.* to priv_test_user2@'%' "
            "WITH GRANT OPTION",
            "GRANT CREATE VIEW on `db``:db`.```t``.``export_2` to "
            "priv_test_user@'%'",
            "GRANT TRIGGER ON util_test.* to priv_test_user@'%' "
            "WITH GRANT OPTION",
            "GRANT SHUTDOWN on *.* to priv_test_user2@'%'",
            "GRANT EXECUTE on util_test.* to priv_test_user@'%'",
            "GRANT ALTER ROUTINE on FUNCTION util_test.f1 to "
            "priv_test_user2@'%' WITH GRANT OPTION",
            "GRANT INSERT, DELETE, CREATE, DROP,REFERENCES, INDEX, "
            "ALTER, CREATE VIEW, SHOW VIEW, TRIGGER on "
            "util_test.t1 to priv_test_user2@'%' WITH GRANT OPTION",
            "GRANT EXECUTE, TRIGGER on *.* to priv_test_user3@'%'",
            "GRANT UPDATE, DELETE, ALTER ROUTINE on util_test.* to "
            "priv_test_user3@'%'",
            "GRANT SELECT on util_test.t3 to priv_test_user3@'%'",
            "GRANT DROP on *.* to priv_test_user3@'%'",
            "GRANT ALTER ROUTINE on PROCEDURE util_test.p1 to "
            "priv_test_user3@'%' WITH GRANT OPTION",
        ]

        for grant_stm in grant_stms:
            try:
                self.server1.exec_query(grant_stm)
            except UtilError as err:
                raise MUTLibError("Failed to execute query: "
                                  "{0}".format(err.errmsg))
        return True

    def run(self):
        cmd_base = 'mysqlgrants.py --server={0}'.format(
            self.build_connection_string(self.server1))

        test_num = 1
        comment = ("Test case {0} - Privileges are inherited from global "
                   "level to db level  and from db level to tables and "
                   "routines".format(test_num))
        cmd = ("{0} util_test util_test.t3 util_test.t2 util_test.p1 "
               "util_test.f1".format(cmd_base))
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - show grantees, using all types of objects:"
                   " tables, databases and stored routines".format(test_num))
        if os.name == 'posix':
            cmd_arg = ("'`db``:db`' '`db``:db`.```t``.``export_2`' "
                       "'`db``:db`.`fu``nc`' '`db``:db`.`pr````oc`' ")
        else:
            cmd_arg = ('"`db``:db`" "`db``:db`.```t``.``export_2`" '
                       '"`db``:db`.`fu``nc`" "`db``:db`.`pr````oc`" ')
        cmd = ("{0} util_test util_test.t1 util_test.t2 "
               "util_test.does_not_exist util_test.v1 db_does_not_exist "
               "util_test.t3 {1}".format(cmd_base, cmd_arg))
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - show grants for all objects of a "
                   "database using wildcard".format(test_num))
        cmd = "{0} util_test.* ".format(cmd_base,)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # mask non deterministic output
        self.do_masks()

        return True

    def do_masks(self):
        """Masks non deterministic output.
        """
        self.replace_substring(str(self.server1.port), "PORT1")
        self.remove_result("# - 'root'@'")

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def drop_all(self):
        """DROPS all databases and users created.
        """
        dbs_to_drop = ["util_test", 'db`:db']
        for db in dbs_to_drop:
            self.drop_db(self.server1, db)

        users_to_drop = ["'joe'@'user'", "'joe_wildcard'@'%'",
                         "priv_test_user@'%'", "priv_test_user2@'%'",
                         "priv_test_user3@'%'", ]
        for user in users_to_drop:
            drop_stm = "DROP USER {0}".format(user)
            try:
                self.server1.exec_query(drop_stm)
            except UtilError:
                pass
        return True

    def cleanup(self):
        if self.res_fname:
            try:
                os.unlink(self.res_fname)
            except OSError:
                pass
        return self.drop_all()
