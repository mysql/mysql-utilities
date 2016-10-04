#
# Copyright (c) 2013, 2016, Oracle and/or its affiliates. All rights reserved.
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
import_keys test.
"""

import os

import mutlib

from mysql.utilities.exception import MUTLibError
from mysql.utilities.exception import UtilError


class test(mutlib.System_test):
    """Import Data
    This test executes the import utility on a single server.
    It uses the mysqldbexport utility to generate files for importing.
    """

    server0 = None
    server1 = None
    server2 = None
    need_servers = False
    export_import_file = None
    tables = None
    s1_serverid = None
    s2_serverid = None

    def check_prerequisites(self):
        self.check_gtid_unsafe()
        # Need at least one server.
        self.tables = []
        self.server1 = None
        self.server2 = None
        self.need_servers = False
        if not self.check_num_servers(2):
            self.need_servers = True
        return self.check_num_servers(1)

    def setup(self):
        self.export_import_file = "test_run.txt"
        num_servers = self.servers.num_servers()
        if self.need_servers:
            try:
                self.servers.spawn_new_servers(num_servers)
            except MUTLibError as err:
                raise MUTLibError("Cannot spawn needed servers: {0}".format(
                    err.errmsg))
        self.server0 = self.servers.get_server(0)

        index = self.servers.find_server_by_name("export_basic")
        if index >= 0:
            self.server1 = self.servers.get_server(index)
            try:
                res = self.server1.show_server_variable("server_id")
            except UtilError as err:
                raise MUTLibError("Cannot get export_basic server "
                                  "server_id: {0}".format(err.errmsg))
            self.s1_serverid = int(res[0][1])
        else:
            self.s1_serverid = self.servers.get_next_id()
            res = self.servers.spawn_new_server(self.server0, self.s1_serverid,
                                                "export_basic")
            if not res:
                raise MUTLibError("Cannot spawn export_basic server.")
            self.server1 = res[0]
            self.servers.add_new_server(self.server1, True)

        index = self.servers.find_server_by_name("import_basic")
        if index >= 0:
            self.server2 = self.servers.get_server(index)
            try:
                res = self.server2.show_server_variable("server_id")
            except UtilError as err:
                raise MUTLibError("Cannot get import_basic server "
                                  "server_id: {0}".format(err.errmsg))
            self.s2_serverid = int(res[0][1])
        else:
            self.s2_serverid = self.servers.get_next_id()
            res = self.servers.spawn_new_server(self.server0, self.s2_serverid,
                                                "import_basic",
                                                '"--sql_mode="')
            if not res:
                raise MUTLibError("Cannot spawn import_basic server.")
            self.server2 = res[0]
            self.servers.add_new_server(self.server2, True)

        self.drop_all()

        data_file = os.path.normpath("./std_data/multiple_keys.sql")
        try:
            self.server1.read_and_exec_SQL(data_file, self.debug)
        except UtilError as err:
            raise MUTLibError("Failed to read commands from file "
                              "{0}: {1}".format(data_file, err.errmsg))

        # In case other tests disable it, enable foreign key checks so
        # that the server can record the checks are on at start.
        self.server1.exec_query("SET foreign_key_checks=1")
        self.server1.disable_foreign_key_checks(True)
        data_file = os.path.normpath("./std_data/fkeys.sql")
        try:
            self.server1.read_and_exec_SQL(data_file, self.debug)
        except UtilError as err:
            raise MUTLibError("Failed to read commands from file "
                              "{0}: {1}".format(data_file, err.errmsg))
        self.server1.disable_foreign_key_checks(False)

        return True

    def _check_tables(self, server, db):
        """Check tables.
        """
        for tbl in self.tables:
            res = server.exec_query("SHOW CREATE TABLE "
                                    "{0}.{1}".format(db, tbl))
            self.results.append(" ".join(res[0][1].split("\n")) + "\n")

    def run_import_test(self, expected_res, from_conn, to_conn, db, frmt,
                        imp_type, comment, export_options=None,
                        import_options=None):
        """Runs import test.

        expected_res[in]     Expected result.
        from_conn[in]        Connection string.
        to_conn[in]          Connection string.
        db[in]               Database name.
        frmt[in]             Format.
        imp_type[in]         Import type.
        comment[in]          Comment.
        export_options[in]   Export options.
        import_options[in]   Import options.
        """
        # Set command with appropriate quotes for the OS
        if os.name == 'posix':
            export_cmd = ("mysqldbexport.py  --skip-gtid {0} '{1}' "
                          "--export={2} --format={3} ".format(from_conn, db,
                                                              imp_type, frmt))
        else:
            export_cmd = ('mysqldbexport.py  --skip-gtid {0} "{1}" '
                          '--export={2} --format={3} '.format(from_conn, db,
                                                              imp_type, frmt))
        if export_options is not None:
            export_cmd += export_options
        export_cmd += " > {0}".format(self.export_import_file)

        import_cmd = ("mysqldbimport.py {0} {1} --import={2} --format={3}"
                      " --drop ".format(to_conn, self.export_import_file,
                                        imp_type, frmt))
        if import_options is not None:
            import_cmd += import_options

        self.results.append(comment + "\n")

        # Precheck: check db and save the results.
        self.results.append("BEFORE:\n")
        self._check_tables(self.server1, db)

        # First run the export to a file.
        res = self.run_test_case(0, export_cmd, "Running export...")
        if not res:
            raise MUTLibError("EXPORT: {0}: failed".format(comment))

        # Second, run the import from a file.
        res = self.run_test_case(expected_res, import_cmd, "Running import...")
        if not res:
            raise MUTLibError("IMPORT: {0}: failed".format(comment))

        # Now, check db and save the results.
        if expected_res == 0:
            self.results.append("AFTER:\n")
            self._check_tables(self.server2, db)

    def run(self):
        self.res_fname = "result.txt"

        conn1 = self.build_connection_string(self.server1)
        conn2 = self.build_connection_string(self.server2)
        from_conn = "--server={0}".format(conn1)
        to_conn = "--server={0}".format(conn2)

        _FORMATS = ("CSV", "TAB", "GRID", "VERTICAL")
        self.tables = ['t1', 't2', 't3']
        test_num = 1
        for frmt in _FORMATS:
            comment = ("Test Case {0} : Testing import with {1} format and "
                       "multiple part keys".format(test_num, frmt))
            # We test DEFINITIONS and DATA only in other tests
            self.run_import_test(0, from_conn, to_conn, 'util_test_keys', frmt,
                                 "BOTH", comment)
            self.drop_db(self.server2, "util_test_keys")
            test_num += 1

        self.drop_db(self.server2, 'db`:db')

        # Now test foreign keys
        self.tables = ['t1', 'a1']
        comment = ("Test Case {0} : Testing import with foreign "
                   "keys".format(test_num))
        self.run_import_test(0, from_conn, to_conn, 'util_test_fk', "SQL",
                             "BOTH", comment)
        self.drop_db(self.server2, "util_test_fk")
        test_num += 1

        # Now test foreign keys but this time skip them.
        # But this will fail because the table has fkeys!
        comment = ("Test Case {0} : Testing import with foreign "
                   "keys and --skip-fkey-checks".format(test_num))
        self.run_import_test(1, from_conn, to_conn, 'util_test_fk', "SQL",
                             "BOTH", comment, " --skip-fkey-checks ")
        self.replace_result("ERROR: Query failed. ", "ERROR: Query failed. "
                                                     "Cannot add foreign key "
                                                     "constraint\n")

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def drop_all(self):
        """Drops all databases created.
        """
        self.drop_db(self.server1, "util_test_keys")
        self.drop_db(self.server2, "util_test_keys")
        self.drop_db(self.server1, "util_test_fk")
        self.drop_db(self.server2, "util_test_fk")
        self.drop_db(self.server1, "util_test_fk2")
        self.drop_db(self.server1, "util_test_fk3")
        return True

    def cleanup(self):
        if self.res_fname:
            try:
                os.unlink(self.res_fname)
            except OSError:
                pass
        if self.export_import_file:
            try:
                os.unlink(self.export_import_file)
            except OSError:
                pass
        return self.drop_all()
