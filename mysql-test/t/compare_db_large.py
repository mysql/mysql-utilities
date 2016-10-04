#
# Copyright (c) 2010, 2016, Oracle and/or its affiliates. All rights reserved.
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
compare_db_large test.
"""

import os

import mutlib

from mysql.utilities.exception import MUTLibError
from mysql.utilities.exception import UtilError
from mysql.utilities.common.database import UtilDBError


class test(mutlib.System_test):
    """Large db diff
    This test executes a consistency check of two databases on
    separate servers.

    Tests BUG#16204629: Where the length of the key for the span index
    has been increased.

    Note: Test requires the world_innodb sample database loaded in server1.
    """

    server1 = None
    server2 = None
    db_test_name = None
    setup_temp_file = None

    def check_prerequisites(self):
        self.check_gtid_unsafe()
        self.server1 = self.servers.get_server(0)
        self.db_test_name = "world"
        rows = []
        engine = ""
        try:
            rows = self.server1.exec_query("SHOW DATABASES LIKE '{0}'"
                                           "".format(self.db_test_name))
            if len(rows) > 0:
                self.server1.exec_query("USE {0}".format(self.db_test_name))
                res = self.server1.exec_query("SHOW TABLE STATUS  LIKE '{0}'"
                                              "".format("City"))
                if res:
                    engine = res[0][1]
        except MUTLibError as err:
            print("Error checking prerequisites: {0}".format(err))
        if engine.upper() != "INNODB" or len(rows) == 0:
            raise MUTLibError("Need {0} ({1}) database loaded on {2}"
                              "".format(self.db_test_name, "world_innodb.sql",
                                        self.server1.role))

        return self.check_num_servers(1)

    def setup(self):
        if not self.check_num_servers(2):
            try:
                self.servers.spawn_new_servers(2)
            except MUTLibError as err:
                raise MUTLibError("Cannot spawn needed servers: {0}"
                                  "".format(err.errmsg))
        self.server2 = self.servers.get_server(1)

        self.setup_temp_file = "setup.tmp"

        s1_conn = self.build_connection_string(self.server1)
        source_conn = "--source={0}".format(s1_conn)
        s2_conn = self.build_connection_string(self.server2)
        dest_conn = "--destination={0}".format(s2_conn)
        copy_cmd = ("mysqldbcopy.py {0} {1} {2}:{3} --drop-first --skip-gtid"
                    "".format(source_conn, dest_conn, self.db_test_name,
                              self.db_test_name))

        res = self.exec_util(copy_cmd, self.setup_temp_file)
        if res != 0:
            raise MUTLibError("Failed to clone the database {0}:{1}"
                              "".format(self.db_test_name, self.db_test_name))

        table1 = "CountryLanguage"
        count_rows_qry = ("SELECT COUNT(*) FROM {0}.{1}"
                          "".format(self.db_test_name, table1))
        try:
            if self.debug:
                print("\n")
                print("Querying server1: {0}".format(self.server1.port))
            count_one = self.server1.exec_query(count_rows_qry)
            if self.debug:
                print("Querying server2: {0}".format(self.server2.port))
            count_two = self.server2.exec_query(count_rows_qry)
            if self.debug:
                print("{0}.{1} row count in server1 is {2} "
                      "and in server2 is {3}"
                      "".format(self.db_test_name, table1, count_one[0][0],
                                count_two[0][0]))
        except UtilDBError as err:
            raise MUTLibError("While setting up test, An error was found: {0}"
                              "".format(err.errmsg))
        return True

    def run(self):
        self.res_fname = "result.txt"
        s_conn = self.build_connection_string(self.server1)
        s1_conn = "--server1={0}".format(s_conn)
        s_conn = self.build_connection_string(self.server2)
        s2_conn = "--server2={0}".format(s_conn)

        cmd_str = ("mysqldbcompare.py {s1} {s2} {params}"
                   "".format(s1=s1_conn, s2=s2_conn, params="{params}"))

        test_case = 1
        comment = ("Test case {0} - check database with No differences "
                   "".format(test_case))

        parameters = ("{0}:{1} -t --changes-for=server2 --difftype=sql -vv"
                      "".format(self.db_test_name, self.db_test_name))
        res = self.run_test_case(0, cmd_str.format(params=parameters), comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_case += 1
        # Do some alterations...
        try:
            table = "City"
            count_rows_qry = ("SELECT COUNT(*) FROM {0}.{1}"
                              "".format(self.db_test_name, table))
            count_before = self.server2.exec_query(count_rows_qry)

            self.server2.exec_query("DELETE FROM {0}.{1} WHERE Id > 4050;"
                                    "".format(self.db_test_name, table))

            count_after = self.server2.exec_query(count_rows_qry)

            if self.debug:
                print("{0}.{1} rows had been decreased from {2} to {3}"
                      "".format(self.db_test_name, table, count_before[0][0],
                                count_after[0][0]))

        except UtilError as err:
            raise MUTLibError("Failed to execute query: {0}"
                              "".format(err.errmsg))

        comment = ("Test case {0} - check database with known differences "
                   "".format(test_case))
        res = self.run_test_case(1, cmd_str.format(params=parameters), comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        self.do_replacements()

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def do_replacements(self):
        """Mask inconsistent Python 2.7 behavior.
        """
        self.replace_result("@@ -1 +1 @@", "@@ -1,1 +1,1 @@\n")
        self.replace_result("# @@ -1 +1 @@", "# @@ -1,1 +1,1 @@\n")

        synoms = [("on [::1]", "on localhost"), ("city`", "City`"),
                  ("country`", "Country`"),
                  ("countrylanguage`", "CountryLanguage`"),
                  ("world.city", "world.City"),
                  ("world.country", "world.Country"),
                  ("world.Countrylanguage", "world.CountryLanguage"),
                  ("TABLE     city", "TABLE     City"),
                  ("TABLE     country", "TABLE     Country"),
                  ("TABLE     Countrylanguage", "TABLE     CountryLanguage")]
        for word, synom in synoms:
            self.replace_substring(word, synom)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        try:
            if self.setup_temp_file:
                os.unlink(self.setup_temp_file)
            if self.res_fname:
                os.unlink(self.res_fname)
        except OSError:
            pass
        return self.kill_server(self.server2.role)
