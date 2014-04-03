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
clone_db_locks test.
"""

import os

import mutlib

from mysql.utilities.exception import MUTLibError, UtilError

_LOCKTYPES = ['no-locks', 'lock-all', 'snapshot']


class test(mutlib.System_test):
    """simple db clone
    This test executes a simple clone of a database on a single server using
    the locking options.
    """

    server1 = None

    def check_prerequisites(self):
        if self.servers.get_server(0).check_version_compat(5, 6, 5):
            raise MUTLibError("Test requires server version prior to 5.6.5")
        return self.check_num_servers(1)

    def setup(self):
        self.server1 = self.servers.get_server(0)
        data_file = os.path.normpath("./std_data/basic_data.sql")
        self.drop_all()
        try:
            self.server1.read_and_exec_SQL(data_file, self.debug)
        except MUTLibError, err:
            raise MUTLibError(
                "Failed to read commands from file {0}{1}: ".format(
                    data_file, err.errmsg))
        return True

    def run(self):
        self.server1 = self.servers.get_server(0)
        self.res_fname = "result.txt"

        from_conn = "--source={0}".format(
            self.build_connection_string(self.server1))
        to_conn = "--destination={0}".format(
            self.build_connection_string(self.server1))

        test_num = 0
        for locktype in _LOCKTYPES:
            test_num += 1

            comment = "Test case {0} - clone with locking={1}".format(test_num,
                                                                      locktype)
            if self.debug:
                print comment
            self.drop_db(self.server1, "util_db_clone")
            cmd = ("mysqldbcopy.py --skip-gtid {0} {1} util_test:util_db_clone"
                   "  --drop-first --locking={2}".format(from_conn, to_conn,
                                                         locktype))
            try:
                res = self.exec_util(cmd, self.res_fname)
                self.results.append(res)
            except MUTLibError, err:
                raise MUTLibError(err.errmsg)

        return True

    def get_result(self):
        for result in self.results:
            if self.server1 and result == 0:
                query = "SHOW DATABASES LIKE 'util_%'"
                try:
                    res = self.server1.exec_query(query)
                    if res and res[0][0] != 'util_db_clone':
                        return False, ("Result failure.\n",
                                       "Database clone not found.\n")
                except UtilError as err:
                    raise MUTLibError(err.errmsg)
            else:
                return False, "Test case returned wrong result.\n"

        return True, None

    def record(self):
        # Not a comparative test, returning True
        return True

    def drop_all(self):
        """Drops all databases and users created.
        """
        res1 = self.drop_db(self.server1, "util_test")
        res2 = self.drop_db(self.server1, "util_db_clone")

        drop_user = ["DROP USER 'joe'@'user'", "DROP USER 'joe_wildcard'@'%'"]
        for drop in drop_user:
            try:
                self.server1.exec_query(drop)
            except UtilError:
                pass
        return res1 and res2

    def cleanup(self):
        if self.res_fname:
            os.unlink(self.res_fname)
        return self.drop_all()
