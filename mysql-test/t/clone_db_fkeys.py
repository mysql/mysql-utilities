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
import os
import mutlib
from collections import namedtuple
from mysql.utilities.exception import MUTLibError, UtilDBError, UtilError


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
                    "Cannot spawn needed servers: {0}".format(err.errmsg))

        # Set spawned servers
        self.server1 = self.servers.get_server(1)
        data_file = os.path.normpath("./std_data/fkeys.sql")
        self.drop_all()
        self.server1.disable_foreign_key_checks(True)
        try:
            self.server1.read_and_exec_SQL(data_file, self.debug)
        except UtilError as err:
            raise MUTLibError("Failed to read commands from file {0}: "
                              "{1}".format(data_file, err.errmsg))
        self.server1.disable_foreign_key_checks(False)
        return True

    def run(self):
        self.result_boundaries = [0]
        self.res_fname = "result.txt"

        from_conn = "--source={0}".format(
            self.build_connection_string(self.server1))
        to_conn = "--destination={0}".format(
            self.build_connection_string(self.server1))

        self.test_num = 1
        comment = ("Test case {0} - clone a sample database with foreign keys "
                   "dependencies without multiprocessing".format(self.test_num))
        cmd_opts = ["mysqldbcopy.py", "--skip-gtid", from_conn, to_conn,
                    "util_test_fk2:util_test_fk2_clone"]
        cmd = " ".join(cmd_opts)
        try:
            # Must disconnect to avoid deadlock when copying fkey tables
            # using INSERT ... SELECT
            self.server1.disconnect()
            res = self.run_test_case(0, cmd, comment)
            # store test output boundary
            self.result_boundaries.append(len(self.results))
            self.server1.connect()
            if not res:
                raise MUTLibError("{0}: failed".format(comment))
        except MUTLibError as err:
            raise MUTLibError(err.errmsg)

        self.test_num += 1
        comment = ("Test case {0} - clone a sample database with foreign keys "
                   "dependencies using multiprocessing".format(self.test_num))
        cmd_opts = ["mysqldbcopy.py", "--skip-gtid", from_conn, to_conn,
                    "util_test_fk2:util_test_fk2_clone_mp", "--multiprocess=2"]

        cmd = " ".join(cmd_opts)
        try:
            # Must disconnect to avoid deadlock when copying fkey tables
            # using INSERT ... SELECT
            self.server1.disconnect()
            res = self.run_test_case(0, cmd, comment)
            # store test output boundary
            self.result_boundaries.append(len(self.results))
            self.server1.connect()
            if not res:
                raise MUTLibError("{0}: failed".format(comment))
        except MUTLibError as err:
            raise MUTLibError(err.errmsg)
        return True

    def get_result(self):
        query_ori = "SHOW CREATE TABLE `util_test_fk2`.a2"
        test_tuple = namedtuple("test_tuple", "query, test_num")
        test_tuples = [
            test_tuple("SHOW CREATE TABLE `util_test_fk2_clone`.a2", 1),
            test_tuple("SHOW CREATE TABLE `util_test_fk2_clone_mp`.a2", 2),
        ]

        # Test create table statements
        try:
            res_ori = self.server1.exec_query(query_ori)
            for tpl in test_tuples:
                res_clo = self.server1.exec_query(tpl.query)
                # Check if create table statements are equal and if there were
                # no errors in the cloning operation
                if not (res_ori and res_clo and
                        res_clo[0][1] == res_ori[0][1]):
                    return False, ("Result failure. Table definitions are not"
                                   " equal for test case {0}"
                                   "".format(tpl.test_num))
        except UtilDBError as err:
            raise MUTLibError(err.errmsg)

        # Now test output for query errors
        query_error = "Query failed"
        for test_num in range(1, self.test_num+1):
            start = self.result_boundaries[test_num - 1]
            end = self.result_boundaries[test_num]
            for line in self.results[start:end]:
                    if query_error in line:
                        return False, ("Test case {0} result failure.\nQuery "
                                       "error found: {1}"
                                       "\n".format(test_num, line))
        return True, None

    def record(self):
        # Not a comparative test, returning True
        return True

    def drop_all(self):
        drop_dbs = ['util_test_fk2', 'util_test_fk2_clone',
                    'util_test_fk2_clone_mp', 'util_test_fk',
                    'util_test_fk3']
        drop_results = []
        for db in drop_dbs:
            drop_results.append(self.drop_db(self.server1, db))
        return all(drop_results)

    def cleanup(self):
        if self.res_fname:
            os.unlink(self.res_fname)
            # Drop databases and kill spawned servers
        return self.drop_all() and self.kill_server(self.server1.role)
