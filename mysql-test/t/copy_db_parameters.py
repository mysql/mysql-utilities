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
copy_db_parameters test.
"""

import os

import copy_db

from mysql.utilities.exception import MUTLibError
from mysql.utilities.exception import UtilError

_SYSTEM_DATABASES = ['MYSQL', 'INFORMATION_SCHEMA', 'PERFORMANCE_SCHEMA']


class test(copy_db.test):
    """check parameters for clone db
    This test executes a series of clone database operations on a single
    server using a variety of parameters. It uses the copy_db test
    as a parent for setup and teardown methods.
    """

    server3 = None

    def check_prerequisites(self):
        # Check MySQL server version - Must be 5.1.0 or higher
        if not self.servers.get_server(0).check_version_compat(5, 1, 0):
            raise MUTLibError("Test requires server version 5.1.0 or higher")
        self.check_gtid_unsafe()
        self.server1 = None
        self.server2 = None
        self.server3 = None
        self.need_server = False
        if not self.check_num_servers(3):
            self.need_server = True
        return self.check_num_servers(1)

    def setup(self):
        self.server1 = self.servers.get_server(0)
        if self.need_server:
            try:
                self.servers.spawn_new_servers(3)
            except MUTLibError as err:
                raise MUTLibError("Cannot spawn needed "
                                  "servers: {0}".format(err.errmsg))
        self.server2 = self.servers.get_server(1)
        self.drop_all()
        data_file = os.path.normpath("./std_data/basic_data.sql")
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

        self.server3 = self.servers.get_server(2)
        # Drop all databases on server3
        try:
            rows = self.server3.exec_query("SHOW DATABASES")
            for row in rows:
                if not row[0].upper() in _SYSTEM_DATABASES:
                    self.drop_db(self.server3, row[0])
            self.server3.exec_query("CREATE DATABASE wesaysocorp")
        except UtilError as err:
            raise MUTLibError("Failed to drop databases: "
                              "{0}".format(err.errmsg))

        try:
            self.server3.read_and_exec_SQL(data_file, self.debug)
        except UtilError as err:
            raise MUTLibError("Failed to read commands from file {0}: "
                              "{1}".format(data_file, err.errmsg))

        return True

    def run(self):
        self.res_fname = "result.txt"

        from_conn = "--source={0}".format(
            self.build_connection_string(self.server1))
        to_conn = "--destination={0}".format(
            self.build_connection_string(self.server2))

        cmd_str = "mysqldbcopy.py  --skip-gtid {0} {1} ".format(from_conn,
                                                                to_conn)

        # In this test, we execute a series of commands saving the results
        # from each run to perform a comparative check.

        test_num = 1
        cmd_opts = "util_test:util_db_clone"
        comment = "Test case {0} - normal run".format(test_num)
        res = self.run_test_case(0, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - operation fails - need "
                   "overwrite".format(test_num))
        res = self.run_test_case(1, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        cmd_opts = "--help"
        comment = "Test case {0} - help".format(test_num)
        res = self.run_test_case(0, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Remove version information
        self.remove_result_and_lines_after("MySQL Utilities mysqldbcopy.py "
                                           "version", 6)

        # We exercise --drop-first here to ensure skips don't interfere
        test_num += 1
        cmd_opts = "--drop-first --skip=data util_test:util_db_clone"
        comment = "Test case {0} - no data".format(test_num)
        res = self.run_test_case(0, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        self.results.append(self.check_objects(self.server1, "util_db_clone"))

        test_num += 1
        cmd_opts = "--drop-first --skip=data --quiet util_test:util_db_clone"
        comment = "Test case {0} - quiet copy".format(test_num)
        res = self.run_test_case(0, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        from_conn = "--source=" + self.build_connection_string(self.server3)

        cmd_str = "mysqldbcopy.py  --skip-gtid {0} {1} ".format(from_conn,
                                                                to_conn)

        test_num += 1
        cmd_opts = "--drop-first --skip=data --all "
        comment = ("Test case {0} - copy all databases - but only "
                   "the utils".format(test_num))
        res = self.run_test_case(0, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Mask socket for destination server
        self.replace_result("# Destination: root@localhost:",
                            "# Destination: root@localhost:[] ... connected\n")

        # Mask known source and destination host name.
        self.replace_result("# Source on ",
                            "# Source on XXXX-XXXX: ... connected.\n")
        self.replace_result("# Destination on ",
                            "# Destination on XXXX-XXXX: ... connected.\n")

        # Ignore GTID messages (skipping GTIDs in this test)
        self.remove_result("# WARNING: The server supports GTIDs")

        # Mask version
        self.replace_result(
            "MySQL Utilities mysqldbcopy version",
            "MySQL Utilities mysqldbcopy version X.Y.Z "
            "(part of MySQL Workbench ... XXXXXX)\n"
        )

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        self.drop_db(self.server1, 'util_test')
        self.drop_db(self.server1, 'db`:db')
        self.drop_db(self.server2, 'util_test')
        self.drop_db(self.server2, 'db`:db')
        self.drop_db(self.server2, 'wesaysocorp')
        self.drop_db(self.server3, 'wesaysocorp')

        return copy_db.test.cleanup(self)
