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

_DEFAULT_MYSQL_OPTS = ('"--log-bin=mysql-bin --skip-slave-start '
                       '--log-slave-updates --gtid-mode=on '
                       '--enforce-gtid-consistency '
                       '--sync-master-info=1 --master-info-repository=table"')

_FORMATS = ['sql', 'csv', 'tab', 'grid', 'vertical']


class test(mutlib.System_test):
    """check gtid operation for export/import utilities
    This test executes a series of export database operations using a variety
    of --skip-gtid and gtid and non-gtid servers.
    """

    def check_prerequisites(self):
        # Check MySQL server version - Must be 5.6.9 or higher
        if not self.servers.get_server(0).check_version_compat(5, 6, 9):
            raise MUTLibError("Test requires server version 5.6.9 or higher")
        return self.check_num_servers(1)

    def setup(self):
        self.server0 = self.servers.get_server(0)
        self.server1 = None
        self.server2 = None
        self.server3 = None

        index = self.servers.find_server_by_name("with_gtids_1")
        if index >= 0:
            self.server1 = self.servers.get_server(index)
            try:
                res = self.server1.show_server_variable("server_id")
            except UtilError as err:
                raise MUTLibError("Cannot get gtid enabled server 1 "
                                  "server_id: {0}".format(err.errmsg))
            self.s1_serverid = int(res[0][1])
        else:
            self.s1_serverid = self.servers.get_next_id()
            res = self.servers.spawn_new_server(
                self.server0, self.s1_serverid, "with_gtids_1",
                _DEFAULT_MYSQL_OPTS)
            if not res:
                raise MUTLibError("Cannot spawn gtid enabled server 1.")
            self.server1 = res[0]
            self.servers.add_new_server(self.server1, True)

        index = self.servers.find_server_by_name("with_gtids_2")
        if index >= 0:
            self.server2 = self.servers.get_server(index)
            try:
                res = self.server2.show_server_variable("server_id")
            except UtilError as err:
                raise MUTLibError("Cannot get gtid enabled server 2 "
                                  "server_id: {0}".format(err.errmsg))
            self.s2_serverid = int(res[0][1])
        else:
            self.s2_serverid = self.servers.get_next_id()
            res = self.servers.spawn_new_server(
                self.server0, self.s2_serverid, "with_gtids_2",
                _DEFAULT_MYSQL_OPTS)
            if not res:
                raise MUTLibError("Cannot spawn gtid enabled server 2.")
            self.server2 = res[0]
            self.servers.add_new_server(self.server2, True)

        index = self.servers.find_server_by_name("no_gtids")
        if index >= 0:
            self.server3 = self.servers.get_server(index)
            try:
                res = self.server3.show_server_variable("server_id")
            except UtilError as err:
                raise MUTLibError("Cannot get non-gtid server server_id: "
                                  "{0}".format(err.errmsg))
            self.s3_serverid = int(res[0][1])
        else:
            self.s3_serverid = self.servers.get_next_id()
            res = self.servers.spawn_new_server(self.server0, self.s3_serverid,
                                                "no_gtids",
                                                '"--log-bin=mysql-bin "')
            if not res:
                raise MUTLibError("Cannot spawn non-gtid server.")
            self.server3 = res[0]
            self.servers.add_new_server(self.server3, True)

        return True

    def exec_export_import(self, server1, server2, exp_cmd, imp_cmd,
                           test_num, test_case, ret_val=True, reset=True,
                           load_data=True):
        conn1 = "--server={0}".format(self.build_connection_string(server1))
        conn2 = "--server={0}".format(self.build_connection_string(server2))
        if load_data:
            try:
                server1.read_and_exec_SQL(self.data_file, self.debug)
            except UtilError as err:
                raise MUTLibError("Failed to read commands from file {0}: "
                                  "{1}".format((self.data_file, err.errmsg)))

        comment = "Test case {0} (export phase) {1}".format(test_num,
                                                            test_case)
        cmd_str = "{0}{1} > {2}".format(exp_cmd, conn1, self.export_file)
        res = mutlib.System_test.run_test_case(self, 0, cmd_str, comment)
        if not res:
            for row in self.results:
                print row,
            raise MUTLibError("{0}: failed".format(comment))

        # Display the export file if in debug mode
        if self.debug:
            with open(self.export_file.strip()) as f:
                for row in f:
                    print row,

        comment = "Test case {0} (import phase) {1}".format(test_num,
                                                            test_case)
        if reset:
            server2.exec_query("RESET MASTER")  # reset GTID_EXECUTED
        cmd_str = "{0}{1} {2}".format(imp_cmd, conn2, self.export_file)
        res = mutlib.System_test.run_test_case(self, 0, cmd_str, comment)
        if not res == ret_val:
            for row in self.results:
                print row,
            raise MUTLibError("{0}: failed".format(comment))
        self.drop_all()

    def run(self):
        self.res_fname = "result.txt"
        self.export_file = "export.txt"
        self.data_file = os.path.normpath("./std_data/basic_data.sql")

        export_cmd_str = ("mysqldbexport.py util_test --export=both "
                          "--skip=events,grants,procedures,functions,views "
                          "--format={0} ")
        import_cmd_str = "mysqldbimport.py --import=both --format={0} "

        # Test cases:
        # for each type in [sql, csv, tab, grid, vertical]
        # - gtid -> gtid
        # - gtid -> non-gtid
        # - non-gtid -> gtid
        # Format: server1, server2, test_case (label)
        _TEST_CASES = [
            (self.server1, self.server2, "gtid->gtid"),
            (self.server1, self.server3, "gtid->non_gtid"),
            (self.server3, self.server1, "non_gtid->gtid"),
        ]

        test_num = 1
        for test_case in _TEST_CASES:
            for format_ in _FORMATS:
                self.exec_export_import(
                    test_case[0], test_case[1], export_cmd_str.format(format_),
                    import_cmd_str.format(format_), test_num,
                    "{0}, format={1}".format(test_case[2], format_))
                test_num += 1

        # Now do the warnings for GTIDs:
        # - GTIDS but partial backup
        # - GTIDS on but --skip-gtid option present

        # Need to test for all formats to exercise warning detection code
        for format_ in _FORMATS:
            self.server1.exec_query("CREATE DATABASE util_test2")
            self.exec_export_import(self.server1, self.server2,
                                    export_cmd_str.format(format_),
                                    import_cmd_str.format(format_),
                                    test_num,
                                    "partial backup w/{0}".format(format_))
            test_num += 1

        self.exec_export_import(self.server1, self.server2,
                                export_cmd_str.format("sql --skip-gtid"),
                                import_cmd_str.format("sql --skip-gtid"),
                                test_num, "skip gtids")
        test_num += 1

        # Now test for the gtid_executed error
        # Now show the error for gtid_executed not empty.
        self.server1.exec_query("RESET MASTER")
        self.server1.exec_query("CREATE DATABASE util_test")
        self.server1.exec_query("CREATE TABLE util_test.t3 (a int)")
        self.server2.exec_query("RESET MASTER")
        self.server2.exec_query("CREATE DATABASE util_test")
        self.exec_export_import(self.server1, self.server2,
                                export_cmd_str.format("sql "),
                                import_cmd_str.format("sql "),
                                test_num, "gtid_executed error",
                                False, False, False)

        self.replace_result("# GTID operation: SET @@GLOBAL.GTID_PURGED",
                            "# GTID operation: SET @@GLOBAL.GTID_PURGED = ?\n")

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        try:
            os.unlink(self.res_fname)
        except (OSError, AttributeError):
            pass
        try:
            os.unlink(self.export_file)
        except (OSError, AttributeError):
            pass

        # Kill the servers that are no longer used
        kill_list = ['with_gtids_1', 'with_gtids_2', 'no_gtids']
        return self.drop_all() and self.kill_server_list(kill_list)

    def drop_all(self):
        servers = [self.server1, self.server2, self.server3]
        for server in servers:
            try:
                self.drop_db(server, "util_test")
                self.drop_db(server, "util_test2")
                server.exec_query("DROP USER 'joe'@'user'")
            except UtilError:
                pass
        return True
