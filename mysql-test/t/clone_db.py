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
clone_db test.
"""

import os

import mutlib

from mysql.utilities.exception import MUTLibError
from mysql.utilities.exception import UtilDBError
from mysql.utilities.exception import UtilError


class test(mutlib.System_test):
    """simple db clone
    This test executes a simple clone of a database on a single server.
    """

    server1 = None

    def check_prerequisites(self):
        self.check_gtid_unsafe()
        return self.check_num_servers(1)

    def setup(self):
        self.server1 = self.servers.get_server(0)
        data_file = os.path.normpath("./std_data/basic_data.sql")
        self.drop_all()
        try:
            self.server1.read_and_exec_SQL(data_file, self.debug)
        except UtilError as err:
            raise MUTLibError("Failed to read commands from file {0}: "
                              "{1}".format(data_file, err.errmsg))

        # Create backtick database (with weird names)
        data_file_backticks = os.path.normpath("./std_data/backtick_data.sql")
        try:
            self.server1.read_and_exec_SQL(data_file_backticks, self.debug)
        except UtilError as err:
            raise MUTLibError("Failed to read commands from file {0}: "
                              "{1}".format(data_file_backticks, err.errmsg))

        # Create database with test views (with dependencies)
        data_file_db_copy_views = os.path.normpath(
            "./std_data/db_copy_views.sql")
        try:
            self.server1.read_and_exec_SQL(data_file_db_copy_views,
                                           self.debug)
        except UtilError as err:
            raise MUTLibError("Failed to read commands from file "
                              "{0}: {1}".format(data_file_db_copy_views,
                                                err.errmsg))

        return True

    def run(self):
        self.server1 = self.servers.get_server(0)
        self.res_fname = "result.txt"

        from_conn = "--source={0}".format(
            self.build_connection_string(self.server1))
        to_conn = "--destination={0}".format(
            self.build_connection_string(self.server1))

        # Test case 1 - clone a sample database
        cmd_base = "mysqldbcopy.py --skip-gtid {0} {1} {2}"
        cmd = cmd_base.format(from_conn, to_conn, "util_test:util_db_clone")
        res = self.exec_util(cmd, self.res_fname)
        if res:  # i.e., res != 0
            raise MUTLibError(
                "'{0}' failed. Return code: {1}".format(cmd, res))

        # Test case 2 - clone a sample database with weird names (backticks)
        # Set input parameter with appropriate quotes for the OS
        if os.name == 'posix':
            cmd_arg = "'`db``:db`:`db``:db_clone`'"
        else:
            cmd_arg = '"`db``:db`:`db``:db_clone`"'
        cmd = cmd_base.format(from_conn, to_conn, cmd_arg)
        res = self.exec_util(cmd, self.res_fname)
        self.results.append(res)
        if res:  # i.e., res != 0
            raise MUTLibError(
                "'{0}' failed. Return code: {1}".format(cmd, res))

        # Test case 3 - clone a sample database with views dependencies
        cmd = cmd_base.format(from_conn, to_conn,
                              "views_test:views_test_clone")
        res = self.exec_util(cmd, self.res_fname)
        self.results.append(res)
        if res:  # i.e., res != 0
            raise MUTLibError(
                "'{0}' failed. Return code: {1}".format(cmd, res))

        # Now, do a deeper test of view dependencies
        # Create database with test views (with dependencies)
        data_file_db_copy_views = os.path.normpath(
            "./std_data/db_copy_views_dependencies.sql")
        try:
            self.server1.exec_query("DROP DATABASE views_test")
            self.server1.read_and_exec_SQL(data_file_db_copy_views,
                                           self.debug)
        except UtilError as err:
            raise MUTLibError("Failed to read commands from file "
                              "{0}: {1}".format(data_file_db_copy_views,
                                                err.errmsg))

        # Test case 4 - clone another sample database with views dependencies
        cmd = cmd_base.format(from_conn, to_conn,
                              "views_test:views_test_clone --drop")
        res = self.exec_util(cmd, self.res_fname)
        self.results.append(res)
        if res:  # i.e., res != 0
            raise MUTLibError(
                "'{0}' failed. Return code: {1}".format(cmd, res))

        return True

    def compare_object_counts(self, server, db1, db2):
        """Compare the object counts between databases

        server[in]   Server object
        db1[in]      Name of the first database
        db2[in]      Name of the second database

        Returns a message with the result failure if not equal or None if equal
        """
        db1_objects_str = self.check_objects(server, db1)
        db2_objects_str = self.check_objects(server, db2)
        if db1_objects_str != db2_objects_str:
            return ("Result failure.\n"
                    "The object counts in the databases differ.\n"
                    "'{0}': {1}'{2}': {3}".format(db1, db1_objects_str,
                                                  db2, db2_objects_str))
        return None

    def get_result(self):
        if self.server1:
            query = "SHOW DATABASES LIKE 'util_db_clone'"
            try:
                res = self.server1.exec_query(query)
            except UtilDBError as err:
                raise MUTLibError(err.errmsg)
            if not res or res[0][0] != 'util_db_clone':
                return (False, ("Result failure.\n",
                                "Database clone 'util_db_clone' not found.\n"))

            res = self.compare_object_counts(self.server1, "util_test",
                                             "util_db_clone")
            if res:
                return (False, res)

            query = "SHOW DATABASES LIKE 'db`:db_clone'"
            try:
                res = self.server1.exec_query(query)
            except UtilDBError as err:
                raise MUTLibError(err.errmsg)
            if not res and res[0][0] != 'db`:db_clone':
                return (False, ("Result failure.\n",
                                "Database clone 'db`:db_clone' not found.\n"))

            res = self.compare_object_counts(self.server1, "db`:db",
                                             "db`:db_clone")
            if res:
                return (False, res)

            query = "SHOW DATABASES LIKE 'views_test_clone'"
            try:
                res = self.server1.exec_query(query)
            except UtilDBError as err:
                raise MUTLibError(err.errmsg)
            if not res and res[0][0] != 'views_test_clone':
                return (False, ("Result failure.\n"
                                "Database clone 'views_test_clone' "
                                "not found.\n"))

            res = self.compare_object_counts(self.server1, "views_test",
                                             "views_test_clone")
            if res:
                return (False, res)
        else:
            return False, ("Result failure.\n",
                           ("Test server no longer available to verify "
                            "cloning results.\n"))
        return True, None

    def record(self):
        # Not a comparative test, returning True
        return True

    def drop_all(self):
        """Drops all databases and users created.
        """
        res = self.drop_db(self.server1, "util_test")
        res = res and self.drop_db(self.server1, 'db`:db')
        res = res and self.drop_db(self.server1, "util_db_clone")
        res = res and self.drop_db(self.server1, "db`:db_clone")
        res = res and self.drop_db(self.server1, "views_test")
        res = res and self.drop_db(self.server1, "views_test_clone")

        drop_user = ["DROP USER 'joe'@'user'", "DROP USER 'joe_wildcard'@'%'"]
        for drop in drop_user:
            try:
                self.server1.exec_query(drop)
            except UtilError:
                pass
        return res

    def cleanup(self):
        if self.res_fname:
            os.unlink(self.res_fname)
        return self.drop_all()
