#
# Copyright (c) 2013, Oracle and/or its affiliates. All rights reserved.
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

from mysql.utilities.common.table import quote_with_backticks
from mysql.utilities.exception import MUTLibError, UtilError


_IMPORT_FILES = ['sakila-schema.sql', 'sakila-data.sql']
_IMPORT_FILES_PATH = '../support/example_data/{0}'


class test(mutlib.System_test):
    """Import Sakila sample database.

    This test executes the mysqldbimport utility on a single server to test
    the import of the sakila sample database.
    Note: The sakila database files are imported from the 'support' folder
    since these files should not be distributed with mysql-utilities.
    """

    def check_prerequisites(self):
        # Check if sakila database files are available.
        for sakila_file in _IMPORT_FILES:
            file_path = os.path.normpath(
                _IMPORT_FILES_PATH.format(sakila_file)
            )
            if not os.path.isfile(file_path):
                raise MUTLibError('Sakila database files not available: '
                                  '{0}'.format(file_path))

        # Need at least a base server.
        return self.check_num_servers(1)

    def setup(self):
        # Check available cloned servers and spawn one if needed.
        if self.servers.num_servers() < 2:
            try:
                self.servers.spawn_new_servers(2)
            except MUTLibError as err:
                raise MUTLibError("Cannot spawn needed servers: "
                                  "{0}".format(err.errmsg))
        # Get first cloned server (only one needed).
        self.server1 = self.servers.get_server(1)

        return True

    def run(self):
        self.res_fname = "result.txt"

        # Define base import command.
        cmd_base = "mysqldbimport.py --server={0}".format(
            self.build_connection_string(self.server1)
        )

        # Import sakila schema.
        test_num = 1
        comment = "Test case {0} - Import sakila schema.".format(test_num)
        import_file = os.path.normpath(
            _IMPORT_FILES_PATH.format(_IMPORT_FILES[0])
        )
        # By default: --import=definitions
        cmd = "{0} {1}".format(cmd_base, import_file)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Import sakila data (and remaining definitions).
        test_num += 1
        comment = "Test case {0} - Import sakila data.".format(test_num)
        import_file = os.path.normpath(
            _IMPORT_FILES_PATH.format(_IMPORT_FILES[1])
        )
        # --import=both because the data file also include some definitions.
        cmd = "{0} {1} --import=both".format(cmd_base, import_file)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Confirm import success as suggested in the sakila guide (section 4):
        # http://dev.mysql.com/doc/sakila/en/sakila-installation.html
        test_num += 1
        self.results.append("Test case {0} - Confirm import success."
                            "\n".format(test_num))
        # USE sakila;
        self.server1.exec_query("USE sakila")
        # SHOW TABLES; (expected result: 23 rows)
        res = self.server1.exec_query("SHOW TABLES")
        self.results.append('a) SHOW TABLES ({0} rows returned):'
                            '\n'.format(len(res)))
        for row in res:
            self.results.append('{0}\n'.format(row[0]))
        # SELECT COUNT(*) FROM film; (expected result: 1000)
        res = self.server1.exec_query("SELECT COUNT(*) FROM film")
        self.results.append('\n')
        self.results.append('b) SELECT COUNT(*) FROM film: {0}.'
                            '\n'.format(res[0][0]))
        # SELECT COUNT(*) FROM film_text; (expected result: 1000)
        res = self.server1.exec_query("SELECT COUNT(*) FROM film_text")
        self.results.append('\n')
        self.results.append('c) SELECT COUNT(*) FROM film_text: {0}.'
                            '\n'.format(res[0][0]))

        return True

    def get_result(self):
        return self.compare(__name__, self.results)
    
    def record(self):
        return self.save_result_file(__name__, self.results)

    # This following method should be moved to mutlib module (to be reused).
    def drop_db(self, server, db):
        # Check before you drop to avoid warning.
        try:
            server.exec_query("SHOW DATABASES LIKE '{0}'".format(db))
        except UtilError:
            return True  # Ok to exit here as there weren't any dbs to drop.
        try:
            q_db = quote_with_backticks(db)
            server.exec_query("DROP DATABASE {0}".format(q_db))
        except UtilError:
            return False
        return True

    def cleanup(self):
        # Remove temporary result file.
        try:
            os.unlink(self.res_fname)
        except OSError:
            pass
        # Remove imported database.
        return self.drop_db(self.server1, 'sakila')
