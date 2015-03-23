#
# Copyright (c) 2014, Oracle and/or its affiliates. All rights reserved.
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
This tests the export and import of a databases with composite keys in multiple
output formats.
"""

import os
import sys

import import_basic

from mysql.utilities.exception import MUTLibError
from mysql.utilities.exception import UtilError
from mysql.utilities.command.dbcompare import database_compare


class test(import_basic.test):
    """Import databases with composite keys
    This test executes the import utility on a single server on data with
    foreign keys.
    It uses the mysqldbexport utility to generate files for importing.
    """

    database_list = None

    def setup(self):
        self.export_import_file = "test_run.txt"
        if self.need_servers:
            try:
                self.servers.spawn_new_servers(3)
            except MUTLibError as err:
                raise MUTLibError("Cannot spawn needed servers: {0}".format(
                    err.errmsg))

        self.server1 = self.servers.get_server(1)
        self.server2 = self.servers.get_server(2)
        self.database_list = ['util_test_fk', 'util_test_fk2', 'util_test_fk3']
        self.drop_all()
        self.server1.disable_foreign_key_checks(True)
        data_file = os.path.normpath("./std_data/fkeys.sql")
        try:
            self.server1.read_and_exec_SQL(data_file, self.debug)
        except UtilError as err:
            raise MUTLibError("Failed to read commands from file"
                              " {0}: {1}".format(data_file, err.errmsg))
        self.server1.disable_foreign_key_checks(False)
        return True

    def run(self):
        self.mask_global = False
        self.res_fname = "result.txt"
        s1_conn_str = self.build_connection_string(self.server1)
        s2_conn_str = self.build_connection_string(self.server2)
        from_conn = "--server={0}".format(s1_conn_str)
        to_conn = "--server={0}".format(s2_conn_str)
        cmp_options = {"no_checksum_table": False,
                       "run_all_tests": True,
                       "quiet": True}

        # There is a bug with the rest of the formats, after fixed we should
        # enable them.
        _FORMATS = ("SQL", "CSV", "TAB", "GRID", "VERTICAL")
        _DISPLAYS = ("BRIEF", "FULL")  # We will do "NAMES" in import_errors
        test_num = 1
        res = True
        for display in _DISPLAYS:
            for frmt in _FORMATS:
                # Run import test for each database in the list.
                for db in self.database_list:
                    comment = ("Test Case {0} : Testing import with {1} "
                               "format and {2} display for database "
                               "'{3}'.").format(test_num, frmt, display, db)
                    if self.verbose:
                        print("\nEXECUTING {0}".format(comment))
                    # We test DEFINITIONS and DATA only in other tests
                    self.run_import_test(
                        0, from_conn, to_conn, db,
                        frmt, "BOTH", comment, " --display={0}".format(display)
                    )
                    old_stdout = sys.stdout
                    try:
                        # redirect stdout to prevent database_compare prints
                        # to reach the MUT output.
                        if not self.debug:
                            sys.stdout = open(os.devnull, 'w')
                        # Test correctness of data
                        res = database_compare(s1_conn_str, s2_conn_str, db,
                                               db, cmp_options)
                        if not res:
                            break
                    finally:
                        # restore stdout
                        if not self.debug:
                            sys.stdout.close()
                        sys.stdout = old_stdout
                    test_num += 1

                # Drop databases to import them again from file
                self.server2.disable_foreign_key_checks(True)
                for db in self.database_list:
                    self.drop_db(self.server2, db, self.debug)
                if not res:
                    raise MUTLibError("{0} failed".format(comment))
                self.server2.disable_foreign_key_checks(False)

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def drop_all(self):
        """Drops all databases created.
        """
        drop_results_s1 = []
        drop_results_s2 = []
        self.server1.disable_foreign_key_checks(True)
        self.server2.disable_foreign_key_checks(True)
        for db in self.database_list:
            drop_results_s1.append(self.drop_db(self.server1, db))
            drop_results_s2.append(self.drop_db(self.server2, db))
        self.server1.disable_foreign_key_checks(False)
        self.server2.disable_foreign_key_checks(False)

        return all(drop_results_s1) and all(drop_results_s2)

    def cleanup(self):
        if self.res_fname:
            os.unlink(self.res_fname)
        if self.export_import_file:
            os.unlink(self.export_import_file)
        # Drop databases and kill spawned servers
        return (self.drop_all() and self.kill_server(self.server1.role)
                and self.kill_server(self.server2.role))
