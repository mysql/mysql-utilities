#
# Copyright (c) 2013, Oracle and/or its affiliates. All rights reserved.
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
from mysql.utilities.exception import MUTLibError, UtilError, UtilDBError


class test(mutlib.System_test):
    """simple db clone
    This test executes a simple clone of a database on a single server with
    foreign keys enabled.
    """

    def check_prerequisites(self):
        self.check_gtid_unsafe()
        return self.check_num_servers(1)

    def setup(self):
        # Spawn required servers
        num_servers = self.servers.num_servers()
        if num_servers < 2:
            try:
                self.servers.spawn_new_servers(2)
            except MUTLibError as err:
                raise MUTLibError(
                    "Cannot spawn needed servers: {0}".format(err.errmsg)
                )
        # Set spawned servers
        self.server1 = self.servers.get_server(1)
        data_file = os.path.normpath("./std_data/fkeys.sql")
        self.drop_all()
        self.server1.disable_foreign_key_checks(True)
        try:
            res = self.server1.read_and_exec_SQL(data_file, self.debug)
        except UtilError as e:
            raise MUTLibError("Failed to read commands from file "
                              "{0}: {1}".format(data_file, e.errmsg))
        self.server1.disable_foreign_key_checks(False)
        return True

    def run(self):
        self.res_fname = "result.txt"

        conn_str = self.build_connection_string(self.server1)
        from_conn = "--source={0}".format(conn_str)
        to_conn = "--destination={0}".format(conn_str)

        cmd_str = "mysqldbcopy.py --skip-gtid {0} {1} ".format(from_conn,
                                                               to_conn)

        test_num = 1
        cmd_opts = "util_test_fk:util_test_fk_clone"
        comment = ("Test Case {0} - clone database with FK and try to delete "
                   "a referenced row. Error: {1}")
        try:
            # Must disconnect to avoid deadlock when copying fkey tables
            # using INSERT ... SELECT
            self.server1.disconnect()
            res = self.exec_util(cmd_str + cmd_opts, self.res_fname)
            self.results.append(res)
            return res == 0
        except UtilDBError as e:
            raise MUTLibError(comment.format(test_num, e.errmsg))

    def get_result(self):
        # Reconnect to check status of test case
        self.server1.connect()
        if self.server1 and self.results[0] == 0:
            query = "DELETE FROM `util_test_fk_clone`.t1 WHERE d = 1"
            try:
                res = self.server1.exec_query(query)
                # IF FK constraints were cloned, it it should throw an exception
            except UtilDBError as e:
                # Check if the reason the deletion failed was because of FK
                # constraints
                i = e[0].find("Cannot delete or update a parent row: a "
                              "foreign")
                if i != -1:
                    return (True,None)
                else:
                    raise MUTLibError(e.errmsg)
            return False, ("Result failure.\n", "FK constraints not cloned")
        return False, ("Result failure.\n", "Database clone not found.\n")

    def record(self):
        # Not a comparative test, returning True
        return True

    def drop_all(self):
        drop_dbs = ["util_test_fk2", "util_test_fk_clone", "util_test_fk",
                    "util_test_fk3"]
        drop_results = []
        for db in drop_dbs:
            drop_results.append(self.drop_db(self.server1, db))
        return all(drop_results)

    def cleanup(self):
        if self.res_fname:
            os.unlink(self.res_fname)
        # Drop databases and kill spawned servers
        return self.drop_all() and self.kill_server(self.server1.role)
