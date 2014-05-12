#
# Copyright (c) 2013, 2014, Oracle and/or its affiliates. All rights reserved.
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
copy_db_fkeys_errors test.
"""

import os

import mutlib

from mysql.utilities.exception import MUTLibError, UtilError, UtilDBError


class test(mutlib.System_test):
    """simple db clone
    This test executes a simple clone of a database on a single server with
    foreign keys enabled.
    """

    server1 = None
    server2 = None

    def check_prerequisites(self):
        self.check_gtid_unsafe()
        return self.check_num_servers(1)

    def setup(self):
        # Spawn required servers
        num_servers = self.servers.num_servers()
        if num_servers < 3:
            try:
                self.servers.spawn_new_servers(3)
            except MUTLibError as err:
                raise MUTLibError(
                    "Cannot spawn needed servers: {0}".format(err.errmsg))
            # Set spawned servers
        self.server1 = self.servers.get_server(1)
        self.server2 = self.servers.get_server(2)
        data_file = os.path.normpath("./std_data/fkeys.sql")
        self.drop_all()
        self.server1.disable_foreign_key_checks(True)
        try:
            self.server1.read_and_exec_SQL(data_file, self.debug)
        except UtilError as err:
            raise MUTLibError("Failed to read commands from file "
                              "{0}: {1}".format(data_file, err.errmsg))
        self.server1.disable_foreign_key_checks(False)
        return True

    def run(self):
        self.res_fname = "result.txt"

        conn_str1 = self.build_connection_string(self.server1)
        conn_str2 = self.build_connection_string(self.server2)
        from_conn = "--source={0}".format(conn_str1)
        to_conn = "--destination={0}".format(conn_str2)

        cmd_str = ("mysqldbcopy.py --skip-gtid "
                   "{0} {1} ".format(from_conn, to_conn))

        test_num = 1
        cmd_opts = "util_test_fk:util_test_fk_copy"
        comment = ("Test Case {0} - copy database with FK and try to delete "
                   "a referenced row. Error: {1}")
        try:
            res = self.exec_util(cmd_str + cmd_opts, self.res_fname)
            self.results.append(res)
            return res == 0
        except UtilDBError as err:
            raise MUTLibError(comment.format(test_num, err.errmsg))

    def get_result(self):
        if self.server2 and self.results[0] == 0:
            query = "DELETE FROM `util_test_fk_copy`.t1 WHERE d = 1"
            try:
                self.server2.exec_query(query)
                # If FK constraints were cloned, it it should throw an
                # exception
            except UtilDBError as err:
                # Check if the reason the deletion failed was because of FK
                # constraints
                i = err[0].find(
                    "Cannot delete or update a parent row: a foreign")
                if i != -1:
                    return True, None
                else:
                    raise MUTLibError(err.errmsg)
            return (False, ("Result failure.\n", "FK constraints "
                                                 "were not copied"))
        return False, ("Result failure.\n", "Database copy not found.\n")

    def record(self):
        # Not a comparative test, returning True
        return True

    def drop_all(self):
        """Drops all databases created.
        """
        drop_dbs_s1 = ["util_test_fk2", "util_test_fk3", "util_test_fk"]
        drop_dbs_s2 = ["util_test_fk_copy"]
        drop_results_s1 = []
        drop_results_s2 = []
        for db in drop_dbs_s1:
            drop_results_s1.append(self.drop_db(self.server1, db))

        for db in drop_dbs_s2:
            drop_results_s2.append(self.drop_db(self.server2, db))

        return all(drop_results_s1) and all(drop_results_s2)

    def cleanup(self):
        if self.res_fname:
            os.unlink(self.res_fname)
            # Drop databases and kill spawned servers
        return (self.drop_all() and self.kill_server(
            self.server1.role) and self.kill_server(self.server2.role))
