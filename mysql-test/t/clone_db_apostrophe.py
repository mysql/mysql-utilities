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
clone_db_apostrophe test.
"""

import os
import sys

import mutlib

from mysql.utilities.exception import MUTLibError, UtilError
from mysql.utilities.common.format import format_tabular_list

_DATA_SQL = ["CREATE DATABASE apostrophe",
             "CREATE TABLE apostrophe.t1 (a char(30), b blob)",
             "INSERT INTO apostrophe.t1 VALUES ('1', 'test single "
             "apostrophe''')",
             "INSERT INTO apostrophe.t1 VALUES ('2', 'test 2 '' apostrophes "
             "''')",
             "INSERT INTO apostrophe.t1 VALUES ('3', 'test three'' "
             "apos''trophes''')",
             "INSERT INTO apostrophe.t1 VALUES ('4 '' ', 'test '' in 2 "
             "columns')", ]


class test(mutlib.System_test):
    """simple db clone
    This test executes a simple clone of a database on a single server that
    contains a table with apostrophes in the text.
    """

    server1 = None

    def check_prerequisites(self):
        return self.check_num_servers(1)

    def setup(self):
        self.server1 = self.servers.get_server(0)
        self.drop_all()
        try:
            for command in _DATA_SQL:
                self.server1.exec_query(command)
        except UtilError as err:
            raise MUTLibError("Failed to create test data: "
                              "{0}".format(err.errmsg))
        return True

    def run(self):
        self.server1 = self.servers.get_server(0)
        self.res_fname = "result.txt"

        from_conn = "--source={0}".format(
            self.build_connection_string(self.server1))
        to_conn = "--destination={0}".format(
            self.build_connection_string(self.server1))

        # dump if debug run
        if self.debug:
            print "\n# Dump of data to be cloned:"
            rows = self.server1.exec_query("SELECT * FROM apostrophe.t1")
            format_tabular_list(sys.stdout, ['char_field', 'blob_field'], rows)

        # Test case 1 - clone a sample database
        cmd = ("mysqldbcopy.py {0} {1} apostrophe:apostrophe_clone "
               " --skip-gtid ".format(from_conn, to_conn))
        try:
            res = self.exec_util(cmd, self.res_fname)
            self.results.append(res)
        except MUTLibError as err:
            raise MUTLibError(err.errmsg)

        # dump if debug run
        if self.debug:
            print "\n# Dump of data cloned:"
            rows = self.server1.exec_query("SELECT * FROM apostrophe_clone.t1")
            format_tabular_list(sys.stdout, ['char_field', 'blob_field'], rows)

        return True

    def get_result(self):
        if self.server1 and self.results[0] == 0:
            query = "SHOW DATABASES LIKE 'apostrophe_%'"
            try:
                res = self.server1.exec_query(query)
                if res and res[0][0] == 'apostrophe_clone':
                    return (True, None)
            except UtilError as err:
                raise MUTLibError(err.errmsg)
        return False, ("Result failure.\n", "Database clone not found.\n")

    def record(self):
        # Not a comparative test, returning True
        return True

    def drop_all(self):
        """Drops all databases.
        """
        res1 = self.drop_db(self.server1, "apostrophe")
        res2 = self.drop_db(self.server1, "apostrophe_clone")
        return res1 and res2

    def cleanup(self):
        if self.res_fname:
            try:
                os.unlink(self.res_fname)
            except OSError:
                pass
        return self.drop_all()
