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
clone_db_fkeys_warnings test.
"""

import os

import mutlib

from mysql.utilities.exception import MUTLibError, UtilError


class test(mutlib.System_test):
    """Tests the mysqldbcopy utility in scenarios where databases with
    foreign key dependencies are cloned.

    """

    server1 = None

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
        # Must disconnect to avoid deadlock when copying fkey tables
        self.server1.disconnect()

        self.res_fname = "result.txt"

        conn_str = self.build_connection_string(self.server1)
        from_conn = "--source={0}".format(conn_str)
        to_conn = "--destination={0}".format(conn_str)

        cmd_str = "mysqldbcopy.py --skip-gtid {0} {1} ".format(from_conn,
                                                               to_conn)

        test_num = 1
        cmd_opts = "util_test_fk2:util_test_fk2_clone"
        comment = ("Test case {0} - Warning message when there are Foreign "
                   "Keys pointing to other databases".format(test_num))

        res = self.run_test_case(0, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        cmd_opts = "util_test_fk:util_test_fk_clone"
        comment = ("Test case {0} - No warning message when there are no"
                   " Foreign Keys pointing to other "
                   "databases".format(test_num))
        res = self.run_test_case(0, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        # Reconnect to drop cloned database
        self.server1.connect()
        self.drop_db(self.server1, 'util_test_fk2_clone')
        self.server1.disconnect()
        cmd_opts = ("util_test_fk2:util_test_fk2_clone "
                    "--new-storage-engine=MYISAM")
        comment = ("Test case {0} - Warning message when FK constraints are "
                   "lost because destination engine is not "
                   "InnoDB".format(test_num))

        res = self.run_test_case(0, cmd_str + cmd_opts, comment)
        # Mask known source and destination host name.

        self.replace_result("# Source on ",
                            "# Source on XXXX-XXXX: ... connected.\n")
        self.replace_result("# Destination on ",
                            "# Destination on XXXX-XXXX: ... connected.\n")

        self.server1.connect()

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def drop_all(self):
        """Drops all databases.
        """
        drop_dbs = ["util_test_fk2", "util_test_fk2_clone", "util_test_fk",
                    "util_test_fk_clone", "util_test_fk3"]
        drop_results = []
        for db in drop_dbs:
            drop_results.append(self.drop_db(self.server1, db))
        return all(drop_results)

    def cleanup(self):
        if self.res_fname:
            os.unlink(self.res_fname)
            # Drop databases and kill spawned servers
        return self.drop_all() and self.kill_server(self.server1.role)
