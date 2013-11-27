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

from mysql.utilities.exception import MUTLibError, UtilError
from mysql.utilities.common.tools import get_tool_path


class test(mutlib.System_test):
    """Export Data
    This test executes the export utility on a single server and demonstrates
    how to import the result into mysql using the mysql monitor.
    """

    def check_prerequisites(self):
        # Check MySQL server version - Must be 5.1.0 or higher
        if not self.servers.get_server(0).check_version_compat(5, 1, 0):
            raise MUTLibError("Test requires server version 5.1.0 or higher")
        self.check_gtid_unsafe()
        # Need at least one server.
        self.server1 = None
        self.need_servers = False
        if not self.check_num_servers(3):
            self.need_servers = True
        return self.check_num_servers(1)

    def setup(self):
        num_servers = self.servers.num_servers()
        if self.need_servers:
            try:
                self.servers.spawn_new_servers(num_servers + 2)
            except MUTLibError as err:
                raise MUTLibError("Cannot spawn needed servers: {0}".format(
                    err.errmsg))
        else:
            num_servers -= 2  # Get last 2 servers in list
        self.server1 = self.servers.get_server(num_servers)
        self.server2 = self.servers.get_server(num_servers + 1)
        self.drop_all()
        data_file = os.path.normpath("./std_data/basic_data.sql")
        try:
            self.server1.read_and_exec_SQL(data_file, self.debug)
        except MUTLibError as err:
            raise MUTLibError(
                "Failed to read commands from file {0}: {1}".format(
                    data_file, err.errmsg))

        rows = self.server2.exec_query("SHOW VARIABLES LIKE 'basedir'")
        if rows:
            basedir = rows[0][1]
        else:
            raise MUTLibError("Unable to determine basedir of running "
                              "server.")

        self.mysql_path = get_tool_path(basedir, "mysql")

        return True

    def show_data(self, tbl):
        comment = "Showing data for table {0} \n".format(tbl)
        self.results.append(comment)
        if os.name == "posix":
            cmd = "{0} {1} util_test -e 'SELECT  * FROM {2}'".format(
                self.mysql_path, self.server2_conn, tbl)
        else:
            cmd = '{0} {1} util_test -e "SELECT  * FROM {2}"'.format(
                self.mysql_path, self.server2_conn, tbl)
        res = self.exec_util(cmd, self.res_fname, True)
        if res != 0:
            raise MUTLibError("{0}: failed".format(comment))
        with open(self.res_fname) as f:
            for row in f:
                self.results.append(row)

    def run(self):
        self.res_fname = "result.txt"

        from_conn = "--server={0}".format(
            self.build_connection_string(self.server1))
        conn_val = self.get_connection_values(self.server2)
        self.server2_conn = "-u{0} -p{1} ".format(conn_val[0], conn_val[1])
        if conn_val[3] is not None:
            self.server2_conn = "{0}--port={1} ".format(self.server2_conn,
                                                        conn_val[3])
        if conn_val[4] is not None:
            self.server2_conn = "{0}--socket={1} ".format(self.server2_conn,
                                                          conn_val[4])

        cmd = "mysqldbexport.py {0} util_test --skip-gtid ".format(from_conn)

        test_num = 1
        comment = ("Test case {0} - export metadata to new server via the "
                   "mysql monitor".format(test_num))
        cmd_str = cmd + (" --export=definitions --format=SQL --quiet  "
                         "--skip=events,grants | "
                         "{0} {1} ".format(self.mysql_path, self.server2_conn))
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        self.results.append("{0}\n".format(
            self.check_objects(self.server2, "util_test", False)))

        test_num += 1
        comment = ("Test case {0} - export the data to "
                   "new server via the mysql monitor".format(test_num))
        cmd_str = cmd + (" --export=data --format=SQL --quiet  "
                         "--skip=events,grants | "
                         "{0} {1} ".format(self.mysql_path, self.server2_conn))
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        self.show_data("t1")
        self.show_data("t2")
        self.show_data("t3")
        self.show_data("t4")

        try:
            self.server2.exec_query("DROP DATABASE util_test")
        except UtilError:
            raise MUTLibError("Cannot drop database before import.")

        self.results.append("{0}\n".format(
            self.check_objects(self.server2, "util_test", False)))

        test_num += 1
        comment = ("Test case {0} - export all objects and data to new server "
                   "via the mysql monitor".format(test_num))
        cmd_str = cmd + (" --export=both --format=SQL --quiet  "
                         "--skip=events,grants | "
                         "{0} {1} ".format(self.mysql_path, self.server2_conn))
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        self.results.append("{0}\n".format(
            self.check_objects(self.server2, "util_test", False)))

        self.show_data("t1")
        self.show_data("t2")
        self.show_data("t3")
        self.show_data("t4")

        self.remove_result("Warning: Using a password on the")

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def drop_all(self):
        self.drop_db(self.server1, "util_test")

        drop_user = ["DROP USER 'joe'@'user'", "DROP USER 'joe_wildcard'@'%'"]
        for drop in drop_user:
            try:
                self.server1.exec_query(drop)
            except UtilError:
                pass
        return True

    def cleanup(self):
        if self.res_fname:
            os.unlink(self.res_fname)
        return self.drop_all()
