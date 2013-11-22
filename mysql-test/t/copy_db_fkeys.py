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
from mysql.utilities.exception import MUTLibError, UtilDBError, UtilError


class test(mutlib.System_test):
    """simple db copy
    This test executes copy database test cases among two servers with
    foreign keys defined.
    """

    def check_prerequisites(self):
        self.check_gtid_unsafe()
        # Need at least one server.
        return self.check_num_servers(1)

    def setup(self):
        # Spawn required servers
        num_servers = self.servers.num_servers()
        if num_servers < 3:
            try:
                self.servers.spawn_new_servers(3)
            except MUTLibError as err:
                raise MUTLibError("Cannot spawn needed "
                                  "servers: {0}".format(err.errmsg))
            # Set spawned servers without using the one passed to MUT
        self.server1 = self.servers.get_server(1)
        self.server2 = self.servers.get_server(2)
        self.drop_all()
        self.server1.disable_foreign_key_checks(True)
        data_file = os.path.normpath("./std_data/fkeys.sql")
        try:
            res = self.server1.read_and_exec_SQL(data_file, self.debug)
        except UtilError as err:
            raise MUTLibError("Failed to read commands from file"
                              " {0}: {1}".format((data_file, err.errmsg)))
        self.server1.disable_foreign_key_checks(False)
        return True

    def run(self):
        self.res_fname = "result.txt"

        from_conn = "--source={0}".format(
            self.build_connection_string(self.server1))
        to_conn = "--destination={0}".format(
            self.build_connection_string(self.server2))

        test_num = 1
        comment = ("Test case {0} - copy database with foreign "
                   "keys".format(test_num))
        cmd_str = ("mysqldbcopy.py --skip-gtid "
                   "{0} {1} ".format(from_conn, to_conn))
        cmd_opts = "util_test_fk2:util_test_fk2_copy"
        res = self.exec_util(cmd_str + cmd_opts, self.res_fname)
        self.results.append(res)
        if res != 0:
            raise MUTLibError("{0}: failed".format(comment))
        return True

    def get_result(self):
        msg = None
        if self.server2 and self.server1 and self.results[0] == 0:
            query_ori = "SHOW CREATE TABLE `util_test_fk2`.a2"
            query_clo = "SHOW CREATE TABLE `util_test_fk2_copy`.a2"
            try:
                res_ori = self.server1.exec_query(query_ori)
                res_clo = self.server2.exec_query(query_clo)
                # check if create table statements are equal
                if res_ori and res_clo and res_clo[0][1] == res_ori[0][1]:
                    return True, msg
            except UtilDBError as e:
                raise MUTLibError(e.errmsg)
        return (False, ("Result failure.\n", "Create TABLE statements are not"
                                             " equal\n"))

    def record(self):
        # Not a comparative test, returning True
        return True

    def drop_all(self):
        drop_dbs_s1 = ["util_test_fk", "util_test_fk2", "util_test_fk3"]
        drop_dbs_s2 = ["util_test_fk2_copy"]
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
        return (self.drop_all() and self.kill_server(self.server1.role)
                and self.kill_server(self.server2.role))
