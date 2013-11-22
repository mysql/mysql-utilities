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

from mysql.utilities.exception import MUTLibError
from mysql.utilities.exception import UtilError, UtilDBError


class test(mutlib.System_test):
    """Import Data
    This test executes the import utility on a single server.
    It uses the mysqldbexport utility to generate files for importing.
    """

    def check_prerequisites(self):
        self.check_gtid_unsafe()
        # Need at least one server.
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
                self.servers.spawn_new_servers(num_servers + 1)
            except MUTLibError as err:
                raise MUTLibError("Cannot spawn needed servers: {0}".format(
                    err.errmsg))

        self.server0 = self.servers.get_server(0)

        index = self.servers.find_server_by_name("export_basic")
        if index >= 0:
            self.server1 = self.servers.get_server(index)
            try:
                res = self.server1.show_server_variable("server_id")
            except MUTLibError as err:
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
            except MUTLibError as err:
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
        data_file = os.path.normpath("./std_data/basic_data.sql")
        try:
            self.server1.read_and_exec_SQL(data_file, self.debug)
        except UtilError as err:
            raise MUTLibError("Failed to read commands from file "
                              "{0}: {1}".format(data_file, err.errmsg))

        # Create backtick database (with weird names)
        data_file_backticks = os.path.normpath("./std_data/backtick_data.sql")
        try:
            self.server1.read_and_exec_SQL(data_file_backticks, self.debug)
        except UtilError as err:
            raise MUTLibError("Failed to read commands from file {0}: "
                              "{1}".format(data_file_backticks, err.errmsg))

        # Create database for import tests
        data_file_import = os.path.normpath("./std_data/import_data.sql")
        try:
            self.server1.read_and_exec_SQL(data_file_import, self.debug)
            self.server1.exec_query("COMMIT")  # Commit SQL
        except UtilError as err:
            raise MUTLibError("Failed to read commands from file "
                              "{0}: {1}".format(data_file_import, err.errmsg))

        return True

    def run_import_test(self, expected_res, from_conn, to_conn, db, frmt,
                        imp_type, comment, export_options=None,
                        import_options=None):

        # Set command with appropriate quotes for the OS
        if os.name == 'posix':
            export_cmd = ("mysqldbexport.py --skip-gtid {0} '{1}' --export={2}"
                          " --format={3} ".format(from_conn, db, imp_type,
                                                  frmt))
        else:
            export_cmd = ('mysqldbexport.py --skip-gtid {0} "{1}" --export={2}'
                          ' --format={3} '.format(from_conn, db, imp_type,
                                                  frmt))
        if export_options is not None:
            export_cmd += export_options
        export_cmd = "{0} > {1}".format(export_cmd, self.export_import_file)

        import_cmd = ("mysqldbimport.py {0} {1} --import={2} "
                      "--format={3} ".format(to_conn, self.export_import_file,
                                             imp_type, frmt))
        if import_options is not None:
            import_cmd += import_options

        self.results.append(comment + "\n")

        # Precheck: check db and save the results.
        self.results.append("BEFORE:\n")
        self.results.append(self.check_objects(self.server2, db))

        # First run the export to a file.
        res = self.run_test_case(0, export_cmd, "Running export...")
        if not res:
            raise MUTLibError("EXPORT: {0}: failed".format(comment))

        # Second, run the import from a file.
        res = self.run_test_case(expected_res, import_cmd, "Running import...")
        if not res:
            raise MUTLibError("IMPORT: {0}: failed".format(comment))

        # Now, check db and save the results.
        self.results.append("AFTER:\n")
        self.results.append(self.check_objects(self.server2, db))

    def run_import_raw_csv_test(self, expected_res, from_conn, to_conn, db,
                                table, comment, import_options=None):
        self.results.append("{0}\n".format(comment))
        self.results.append("Running export...\n")

        # Create database and table on server2
        try:
            self.server2.exec_query("CREATE DATABASE `import_test`")
            self.server2.exec_query("CREATE TABLE `import_test`.`customers` "
                                    "(`id` int(10) unsigned NOT NULL, "
                                    "`name` varchar(255) NOT NULL, PRIMARY "
                                    "KEY (`id`)) "
                                    "ENGINE=InnoDB DEFAULT CHARSET=utf8")
        except UtilDBError as err:
            raise MUTLibError(err.errmsg)

        # Build import command
        csv_file = os.path.normpath("./std_data/raw_data.csv")
        import_cmd = (
            "mysqldbimport.py {0} --import=data --format=raw_csv "
            "--table={1}.{2} {3} {4}".format(to_conn, db, table, csv_file,
                                             import_options or "")
        )

        res = self.run_test_case(expected_res, import_cmd, "Running import...")
        if not res:
            raise MUTLibError("IMPORT: {0}: failed".format(comment))

        # Compare databases
        compare_cmd = (
            "mysqldbcompare.py {0} {1} "
            "{2}:{2}".format(from_conn.replace("--server", "--server1"),
                             to_conn.replace("--server", "--server2"), db)
        )
        res = self.run_test_case(0, compare_cmd, "Comparing tables...")
        if not res:
            raise MUTLibError("IMPORT: {0}: failed".format(comment))

    def run_import_csv_no_data_test(self, expected_res, from_conn, comment,
                                    csv_file, import_options):
        self.results.append("{0}\n".format(comment))

        # Build import command
        import_cmd = ("mysqldbimport.py {0} {1} {2}".format(from_conn,
                                                            csv_file,
                                                            import_options))

        res = self.run_test_case(expected_res, import_cmd, "Running import...")
        if not res:
            raise MUTLibError("IMPORT: {0}: failed".format(comment))

    def run(self):
        self.res_fname = "result.txt"

        from_conn = "--server={0}".format(
            self.build_connection_string(self.server1))
        to_conn = "--server={0}".format(
            self.build_connection_string(self.server2))

        _FORMATS = ("SQL", "CSV", "TAB", "GRID", "VERTICAL")
        _FORMATS_BACKTICKS = ("SQL", "CSV", "TAB")
        _DISPLAYS = ("BRIEF", "FULL")  # We will do "NAMES" in import_errors
        test_num = 1
        for display in _DISPLAYS:
            for frmt in _FORMATS:
                comment = ("Test Case {0} : Testing import with {1} format "
                           "and {2} display".format(test_num, frmt, display))
                # We test DEFINITIONS and DATA only in other tests
                self.run_import_test(0, from_conn, to_conn, 'util_test',
                                     frmt, "BOTH", comment,
                                     " --display={0}".format(display))
                self.drop_db(self.server2, "util_test")
                test_num += 1

        # Test database with backticks
        for display in _DISPLAYS:
            for frmt in _FORMATS_BACKTICKS:
                comment = ("Test Case {0} : Testing import with {1} format "
                           "and {2} display (using backticks)".format(
                               test_num, frmt, display))
                self.run_import_test(0, from_conn, to_conn, '`db``:db`', frmt,
                                     "BOTH", comment,
                                     " --display={0}".format(display))
                self.drop_db(self.server2, 'db`:db')
                test_num += 1

        display = 'NAMES'
        frmt = 'SQL'
        comment = ("Test Case {0} : Testing import with {1} format and "
                   "{2} display (using backticks)".format(test_num, frmt,
                                                          display))
        self.run_import_test(0, from_conn, to_conn, '`db``:db`', frmt, "BOTH",
                             comment, " --display={0}".format(display))
        self.drop_db(self.server2, 'db`:db')
        test_num += 1

        comment = ("Test Case {0} : Testing import with RAW_CSV "
                   "format".format(test_num))
        self.run_import_raw_csv_test(0, from_conn, to_conn, "import_test",
                                     "customers", comment)
        self.drop_db(self.server2, 'import_test')
        if os.name != "posix":
            self.replace_result(
                "# Importing data from std_data\\raw_data.csv.",
                "# Importing data from std_data/raw_data.csv.\n")
        test_num += 1

        comment = ("Test Case {0} : Testing import with RAW_CSV format using "
                   "--bulk-insert ".format(test_num))
        self.run_import_raw_csv_test(0, from_conn, to_conn, "import_test",
                                     "customers", comment,
                                     import_options="--bulk-insert")
        self.drop_db(self.server2, 'import_test')
        if os.name != "posix":
            self.replace_result(
                "# Importing data from std_data\\raw_data.csv.",
                "# Importing data from std_data/raw_data.csv.\n")
        test_num += 1

        comment = ("Test Case {0} : Testing import with CSV format with no "
                   "data (using --format=data)".format(test_num))
        import_options = "--import=data --format=csv --skip-rpl"
        csv_file = os.path.normpath("./std_data/no_data.csv")
        self.run_import_csv_no_data_test(0, from_conn, comment, csv_file,
                                         import_options)
        if os.name != "posix":
            self.replace_result("# Importing data from std_data\\no_data.csv.",
                                "# Importing data from std_data/no_data.csv"
                                ".\n")
        test_num += 1

        comment = ("Test Case {0} : Testing import with CSV format with RPL "
                   "statements (using --format=data)".format(test_num))
        import_options = "--import=data --format=csv --skip-rpl"
        csv_file = os.path.normpath("./std_data/rpl_data.csv")
        self.run_import_csv_no_data_test(0, from_conn, comment, csv_file,
                                         import_options)
        if os.name != "posix":
            self.replace_result(
                "# Importing data from std_data\\rpl_data.csv.",
                "# Importing data from std_data/rpl_data.csv.\n")

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def drop_all(self):
        # OK if drop_db fails - they are spawned servers.
        self.drop_db(self.server1, "util_test")
        self.drop_db(self.server1, 'db`:db')
        self.drop_db(self.server1, "import_test")
        self.drop_db(self.server2, "util_test")
        self.drop_db(self.server2, 'db`:db')
        self.drop_db(self.server2, "import_test")

        drop_user = ["DROP USER 'joe'@'user'", "DROP USER 'joe_wildcard'@'%'"]
        for drop in drop_user:
            try:
                self.server1.exec_query(drop)
                self.server2.exec_query(drop)
            except UtilError:
                pass
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
