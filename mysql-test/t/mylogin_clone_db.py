#
# Copyright (c) 2013 Oracle and/or its affiliates. All rights reserved.
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
from mysql.utilities.exception import UtilError


class test(mutlib.System_test):
    """Simple db clone using mylogin.cnf
    This test executes a simple clone of a database on a single server.
    """

    def check_prerequisites(self):
        self.check_gtid_unsafe()

        # Check if the required tools are accessible
        self.check_mylogin_requisites()

        return self.check_num_servers(1)

    def setup(self):
        self.server1 = self.servers.get_server(0)

        # Get connection values
        con_val = self.get_connection_values(self.server1)
        if con_val[1]:
            raise MUTLibError("The use of password in the connection string "
                              "is not supported for automatic generation of "
                              "login-path data. Please specify a user to "
                              "connect to the server that does not require a "
                              "password.")

        # Create login_path_data
        self.create_login_path_data('test_mylogin_clone_db', con_val[0],
                                    con_val[2])

        # Build connection string <login-path>[:<port>][:<socket>]
        self.server1_con_str = 'test_mylogin_clone_db'
        if con_val[3]:
            self.server1_con_str = "%s:%s" % (self.server1_con_str, con_val[3])
        if con_val[4]:
            self.server1_con_str = "%s:%s" % (self.server1_con_str, con_val[4])

        # Load database data
        data_file = os.path.normpath("./std_data/basic_data.sql")
        self.drop_all()
        try:
            self.server1.read_and_exec_SQL(data_file, self.debug)
        except UtilError as err:
            raise MUTLibError("Failed to read commands from file %s: %s"
                              % (data_file, err.errmsg))
        return True

    def run(self):
        self.res_fname = "result.txt"

        from_conn = "--source=%s" % self.server1_con_str
        to_conn = "--destination=%s" % self.server1_con_str

        # Test case 1 - clone a sample database using login-path authentication
        cmd = ("mysqldbcopy.py --skip-gtid %s %s  util_test:util_db_clone "
               % (from_conn, to_conn))
        try:
            res = self.exec_util(cmd, self.res_fname)
            self.results.append(res)
            return res == 0
        except Exception as err:
            raise MUTLibError(str(err))

    def get_result(self):
        if self.server1 and self.results[0] == 0:
            query = "SHOW DATABASES LIKE 'util_%'"
            try:
                res = self.server1.exec_query(query)
                if res and res[0][0] == 'util_db_clone':
                    return (True, None)
            except UtilError as err:
                raise MUTLibError(err.errmsg)
        return (False, ("Result failure.\n", "Database clone not found.\n"))

    def record(self):
        # Not a comparative test, returning True
        return True

    def drop_db(self, server, db):
        # Check before you drop to avoid warning
        try:
            server.exec_query("SHOW DATABASES LIKE 'util_%'")
        except Exception:
            return True  # Ok to exit here as there weren't any dbs to drop
        try:
            server.exec_query("DROP DATABASE %s" % db)
        except Exception:
            return False
        return True

    def drop_all(self):
        res1, res2 = True, True
        try:
            self.drop_db(self.server1, "util_test")
        except Exception:
            res1 = False
        try:
            self.drop_db(self.server1, "util_db_clone")
        except Exception:
            res2 = False
        try:
            self.server1.exec_query("DROP USER 'joe'@'user'")
        except Exception:
            pass
        return res1 and res2

    def cleanup(self):
        self.remove_login_path_data('test_mylogin_clone_db')
        if self.res_fname:
            os.unlink(self.res_fname)
        return self.drop_all()
