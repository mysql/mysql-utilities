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
compare_db test.
"""

import os

import mutlib

from mysql.utilities.exception import MUTLibError
from mysql.utilities.exception import UtilError


class test(mutlib.System_test):
    """simple db diff
    This test executes a consistency check of two databases on
    separate servers.
    """

    server1 = None
    server2 = None
    need_server = False

    def check_prerequisites(self):
        self.check_gtid_unsafe()
        # Need at least one server.
        self.server1 = None
        self.server2 = None
        self.need_server = False
        if not self.check_num_servers(2):
            self.need_server = True
        return self.check_num_servers(1)

    def setup(self):
        self.server1 = self.servers.get_server(0)
        if self.need_server:
            try:
                self.servers.spawn_new_servers(2)
            except MUTLibError as err:
                raise MUTLibError("Cannot spawn needed servers: "
                                  "{0}".format(err.errmsg))
        self.server2 = self.servers.get_server(1)
        self.drop_all()

        # load SQL source files
        data_files = [
            os.path.normpath("./std_data/db_compare_test.sql"),
            os.path.normpath("./std_data/db_compare_backtick.sql"),
            os.path.normpath("./std_data/db_compare_use_indexes.sql")
        ]
        for data_file in data_files:
            try:
                self.server1.read_and_exec_SQL(data_file, self.debug)
                self.server2.read_and_exec_SQL(data_file, self.debug)
            except UtilError as err:
                raise MUTLibError("Failed to read commands from file"
                                  " {0}: {1}".format(data_file, err.errmsg))

        # Add some data to server1 to change AUTO_INCREMENT value.
        try:
            for _ in range(5):
                self.server1.exec_query("INSERT INTO "
                                        "`db_diff_test`.`table-dash` "
                                        "VALUES (NULL)")
        except UtilError as err:
            raise MUTLibError("Failed to insert data on server1: "
                              "{0}".format(err.errmsg))

        # insert values to no_primary_keys
        db = 'no_primary_keys'
        for server in [self.server1, self.server2]:
            for tb in ['nonix_1_simple',
                       'nonix_1_nix_2',
                       'nonix_2_nix_2',
                       'nonix_2_nix_2_pk']:
                for n in range(1, 5):
                    server.exec_query(
                        "INSERT INTO {db}.{tb} (c1, c2, c3, c4, c5, c6)"
                        " VALUES ({v}, {v}{v}, {v}0{v}, {v}00{v},"
                        " {v}000{v}, {v}0000{v});".format(db=db, tb=tb, v=n))
                server.exec_query(
                    "select * from {db}.{tb}".format(db=db, tb=tb,))

        return True

    def create_extra_table(self):
        """Creates an extra table.
        """
        try:
            self.server2.exec_query("USE inventory;")
            create_table = ("CREATE TABLE `inventory`.`extra_table` ("
                            "`id` int(10) unsigned NOT NULL AUTO_INCREMENT,"
                            "`name` varchar(255) NOT NULL,"
                            "PRIMARY KEY (`id`)"
                            ") ENGINE=InnoDB DEFAULT CHARSET=latin1;")
            self.server2.exec_query(create_table)
        except UtilError as err:
            raise MUTLibError("Failed to execute query: "
                              "{0}".format(err.errmsg))

    def drop_extra_table(self):
        """Drops the extra table created.
        """
        try:
            self.server2.exec_query("DROP TABLE `inventory`.`extra_table`")
        except UtilError as err:
            raise MUTLibError("Failed to execute query: "
                              "{0}".format(err.errmsg))

    def alter_data(self):
        """Alters data.
        """
        try:
            # Now do some alterations...
            self.server1.exec_query("USE inventory;")
            self.server1.exec_query("DROP VIEW inventory.tools")
            self.server1.exec_query("CREATE VIEW inventory.tools AS "
                                    "SELECT * FROM inventory.supplies "
                                    "WHERE type = 'tool'")
            self.server1.exec_query("DELETE FROM inventory.supplies "
                                    "WHERE qty > 2")
            self.server1.exec_query("INSERT INTO inventory.supplier "
                                    "VALUES (2, 'Never Enough Inc.')")
            self.server1.exec_query("INSERT INTO inventory.supplier "
                                    "VALUES (4, NULL)")

            self.server2.exec_query("USE inventory;")
            self.server2.exec_query("DROP VIEW inventory.cleaning")
            self.server2.exec_query("DROP VIEW inventory.finishing_up")
            self.server2.exec_query("UPDATE inventory.supplies SET "
                                    "cost = 10.00 WHERE cost = 9.99")
            self.server2.exec_query("INSERT INTO inventory.supplier "
                                    "VALUES (2, 'Wesayso Corporation')")
            self.server2.exec_query("INSERT INTO inventory.supplier "
                                    "VALUES (3, 'Never Enough Inc.')")
            self.server2.exec_query("DELETE FROM inventory.supplies "
                                    "WHERE cost = 10.00 AND "
                                    "type = 'cleaning'")
            self.server2.exec_query("INSERT INTO inventory.supplier "
                                    "VALUES (4, 'Acme Corporation')")
            self.server2.exec_query("INSERT INTO inventory.supplier "
                                    "VALUES (5, NULL)")
            self.server2.exec_query("INSERT INTO inventory.supplier "
                                    "VALUES (6, '')")
        except UtilError as err:
            raise MUTLibError("Failed to execute query: "
                              "{0}".format(err.errmsg))

    def alter_data_2(self):
        """Alters data.
        """
        try:
            # Now do some alterations...
            self.server1.exec_query("USE no_primary_keys")
            self.server1.exec_query(
                "UPDATE nonix_1_simple "
                "SET c1 = c1 + 10, c2 = c2 + 10, c3 = c3 + 10, c5 = c5 + 10"
            )
            self.server1.exec_query(
                "UPDATE nonix_1_nix_2 "
                "SET c1 = c1 + 10, c2 = c2 + 10, c5 = c5 + 10, c6 = c6 + 10"
            )
            self.server1.exec_query(
                "UPDATE `nonix_``2_nix_``2` "
                "SET `c``1` = `c``1` + 10, c3 = c3 + 10, c4 = c4 + 10, "
                "c5 = c5 + 10"
            )
            self.server1.exec_query(
                "UPDATE nonix_2_nix_2_pk "
                "SET c1 = c1 + 10, c2 = c2 + 10, c5 = c5 + 10, c6 = c6 + 10"
            )
        except UtilError as err:
            print("Failed to execute query: {0}".format(err.errmsg))
            raise MUTLibError("Failed to execute query: "
                              "{0}".format(err.errmsg))

    def run(self):
        self.mask_global = False  # Turn off global masks
        self.server1 = self.servers.get_server(0)
        self.res_fname = "result.txt"

        s1_conn = "--server1={0}".format(
            self.build_connection_string(self.server1))
        s2_conn = "--server2={0}".format(
            self.build_connection_string(self.server2))
        s2_conn_dupe = "--server2={0}".format(
            self.build_connection_string(self.server1))

        cmd_base = "mysqldbcompare.py {0} {1} ".format(s1_conn, s2_conn)

        test_num = 1
        comment = "Test case {0} - check a sample database".format(test_num)
        cmd = "{0} inventory:inventory -a".format(cmd_base)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        self.create_extra_table()

        test_num += 1
        comment = ("Test case {0} - check database with known differences "
                   "(extra table)".format(test_num))
        cmd = "{0} inventory:inventory -a".format(cmd_base)
        res = self.run_test_case(1, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        self.drop_extra_table()
        self.alter_data()

        test_num += 1
        comment = ("Test case {0} - check database with known differences "
                   "direction = server1 (default)".format(test_num))
        cmd = "{0} inventory:inventory -a --format=CSV".format(cmd_base)
        res = self.run_test_case(1, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - check database with known differences "
                   "direction = server2".format(test_num))
        cmd = ("{0} inventory:inventory -a --format=CSV "
               "--changes-for=server2".format(cmd_base))
        res = self.run_test_case(1, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - check database with known differences "
                   "direction = server1 and reverse".format(test_num))
        cmd = ("{0} inventory:inventory -a --format=CSV --changes-for=server1 "
               "--show-reverse".format(cmd_base))
        res = self.run_test_case(1, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - check database with known differences "
                   "direction = server2 and reverse".format(test_num))
        cmd = ("{0} inventory:inventory -a --format=CSV --changes-for=server2 "
               "--show-reverse".format(cmd_base))
        res = self.run_test_case(1, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # execute a compare on the same server to test messages

        self.server1.exec_query("CREATE DATABASE inventory2")

        test_num += 1
        comment = ("Test case {0} - compare two databases on same server "
                   "w/server2".format(test_num))
        cmd = ("mysqldbcompare.py {0} {1} inventory:inventory2 "
               "-a".format(s1_conn, s2_conn_dupe))
        res = self.run_test_case(1, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - compare two databases on same "
                   "server".format(test_num))
        cmd = "mysqldbcompare.py {0} inventory:inventory2 -a".format(s1_conn)
        res = self.run_test_case(1, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Set input parameter with appropriate quotes for the OS
        if os.name == 'posix':
            cmd_arg = "'`db.``:db`:`db.``:db`' -a"
        else:
            cmd_arg = '"`db.``:db`:`db.``:db`" -a'
        cmd = "mysqldbcompare.py {0} {1} {2}".format(s1_conn, s2_conn, cmd_arg)
        test_num += 1
        comment = ("Test case {0} - compare a database with weird names "
                   "(backticks)".format(test_num))
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = "Test case {0} - compare two empty databases".format(
            test_num)
        cmd = "mysqldbcompare.py {0} {1} {2}".format(s1_conn, s2_conn,
                                                     "empty_db:empty_db -a")
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - compare a sample database containing "
                   "tables with weird names (no backticks) and different "
                   "table options.".format(test_num))
        cmd_arg = ("db_diff_test:db_diff_test -a "
                   "--skip-row-count --skip-data-check")
        cmd = "mysqldbcompare.py {0} {1} {2}".format(s1_conn, s2_conn, cmd_arg)
        res = self.run_test_case(1, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - compare a sample database containing "
                   "tables with weird names (no backticks) and skipping "
                   "table options.".format(test_num))
        cmd_arg = ("db_diff_test:db_diff_test -a --skip-table-options "
                   "--skip-row-count --skip-data-check")
        cmd = "mysqldbcompare.py {0} {1} {2}".format(s1_conn, s2_conn, cmd_arg)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Compare databases with objects of different type with the same name

        # Create the same PROCEDURE on each server with the same name of an
        # already existing TABLE (i.e., ```t``export_1`).
        self.server1.exec_query(
            "CREATE PROCEDURE `db.``:db`.```t``export_1`() "
            "SELECT 1")
        self.server2.exec_query(
            "CREATE PROCEDURE `db.``:db`.```t``export_1`() "
            "SELECT 1")
        if os.name == 'posix':
            cmd_arg = "'`db.``:db`:`db.``:db`' -a"
        else:
            cmd_arg = '"`db.``:db`:`db.``:db`" -a'
            # Execute test (no differences expected)
        test_num += 1
        comment = ("Test case {0} - compare a database with objects of "
                   "different types with the same name "
                   "(no differences)".format(test_num))
        cmd = "mysqldbcompare.py {0} {1} {2}".format(s1_conn, s2_conn, cmd_arg)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Replace the PROCEDURE previously created on one of the servers by a
        # different one.
        self.server2.exec_query("DROP PROCEDURE `db.``:db`.```t``export_1`")
        self.server2.exec_query(
            "CREATE PROCEDURE `db.``:db`.```t``export_1`() "
            "SELECT 2")
        # Execute test (differences expected)
        test_num += 1
        comment = ("Test case {0} - compare a database with objects of "
                   "different types with the same name "
                   "(with differences)".format(test_num))
        cmd = "mysqldbcompare.py {0} {1} {2}".format(s1_conn, s2_conn, cmd_arg)
        res = self.run_test_case(1, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Tests for tables with no primary keys but with unique indexes
        # nullable and not nullable columns

        # Test automatically pick up the not nullable unique indexes.
        # Note: All previews test had primary keys. Skip checksum table
        # otherwise no indexes are used if there are no differences.
        cmd_arg = "no_primary_keys -a --skip-checksum-table"
        test_num += 1
        comment = ("Test case {0} - Test automatically picks up the not "
                   "nullable unique index (No differences)".format(test_num))
        cmd = "mysqldbcompare.py {0} {1} {2}".format(s1_conn, s2_conn, cmd_arg)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Test given a real not nullable unique index for a specific table
        # using --use-indexes, unique key with one column.
        # Note: skip checksum table otherwise no indexes are used if there are
        # no differences.
        cmd_arg = ("no_primary_keys "
                   "--use-indexes=nonix_1_simple.uk_nonullclmns -a "
                   "--skip-checksum-table")
        test_num += 1
        comment = ("Test case {0} - real not nullable unique index for a "
                   "specific table using --use-indexes "
                   "(No differences)".format(test_num))
        cmd = "mysqldbcompare.py {0} {1} {2}".format(s1_conn, s2_conn, cmd_arg)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Test given a real not nullable index for a specific table
        # using --use-indexes for two tables, unique keys with 2 columns
        # Note: skip checksum table otherwise no indexes are used if there are
        # no differences.
        cmd_arg = ('no_primary_keys '
                   '--use-indexes="nonix_1_nix_2.uk_nonulls;'
                   'nonix_2_nix_2.uk2_nonulls" -a --skip-checksum-table')
        test_num += 1
        comment = ("Test case {0} - compare using--use-indexes for two tables "
                   "(No differences)".format(test_num))
        cmd = "mysqldbcompare.py {0} {1} {2}".format(s1_conn, s2_conn, cmd_arg)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Test given a real not nullable index for a specific table
        # using --use-indexes for same table and other for dif table.
        # Note: skip checksum table otherwise no indexes are used if there are
        # no differences.
        cmd_arg = ('no_primary_keys '
                   '--use-indexes="nonix_2_nix_2.uk2_nonulls;'
                   'nonix_2_nix_2.uk_nonulls;'
                   'nonix_1_nix_2.uk_nonulls;nonix_1_simple.ix_nonull" -a '
                   '--skip-checksum-table')
        test_num += 1
        comment = ("Test case {0} - using --use-indexes for same table "
                   "(No differences)".format(test_num))
        cmd = "mysqldbcompare.py {0} {1} {2}".format(s1_conn, s2_conn, cmd_arg)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Test given a real not nullable index for a specific table
        # using --use-indexes for same table and other for dif table vvv.
        # Note: skip checksum table to show index info.
        cmd_arg = (
            'no_primary_keys --use-indexes="nonix_2_nix_2.uk2_nonulls;'
            'nonix_2_nix_2.uk_nonulls;nonix_1_nix_2.uk_nonulls;'
            'nonix_2_nix_2_pk.uk2_nonulls;nonix_1_simple.ix_nonull" -a -vvv '
            '--skip-checksum-table'
        )
        test_num += 1
        comment = ("Test case {0} - using --use-indexes for same table "
                   "verbose unique index over primary key (No differences)"
                   "").format(test_num)
        cmd = ("mysqldbcompare.py {0} {1} {2}"
               "").format(s1_conn, s2_conn, cmd_arg)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Test given a real not nullable index for a specific table
        # using --use-indexes with backticks verbose debug
        # Note: skip checksum table to show index info.
        if os.name == 'posix':
            cmd_arg = ("no_primary_keys --use-indexes='`nonix_``2_nix_``2`."
                       "`uk_no``nulls`' -a -vvv --skip-checksum-table")
        else:
            cmd_arg = ('no_primary_keys --use-indexes="`nonix_``2_nix_``2`.'
                       '`uk_no``nulls`" -a -vvv --skip-checksum-table')
        test_num += 1
        comment = ("Test case {0} - using --use-indexes with backticks "
                   "verbose (No differences)".format(test_num))
        cmd = "mysqldbcompare.py {0} {1} {2}".format(s1_conn, s2_conn, cmd_arg)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        self.alter_data_2()

        # Test given a nullable index for a specific table
        # using --use-indexes with backticks and Differences
        if os.name == 'posix':
            cmd_arg = ("no_primary_keys --use-indexes='`nonix_``2_nix_``2`."
                       "`uk_no``nulls`' -a")
        else:
            cmd_arg = ('no_primary_keys --use-indexes="`nonix_``2_nix_``2`.'
                       '`uk_no``nulls`" -a')
        test_num += 1
        comment = ("Test case {0} - using --use-indexes with backticks "
                   "verbose (Differences) ".format(test_num))
        cmd = "mysqldbcompare.py {0} {1} {2}".format(s1_conn, s2_conn, cmd_arg)
        res = self.run_test_case(1, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Clone inventory database with a different name
        cmd = ("mysqldbcopy.py --skip-gtid --source={0} --destination={1} {2}"
               "".format(self.build_connection_string(self.server1),
                         self.build_connection_string(self.server2),
                         "inventory:inventory_clone"))
        res = self.exec_util(cmd, self.res_fname)
        if res:
            raise MUTLibError("'{0}' failed. Return code: {1}"
                              "".format(cmd, res))
        test_num += 1
        comment = ("Test case {0} - compare two equal databases with "
                   "different names (including VIEWS)").format(test_num)
        cmd = "{0} inventory:inventory_clone -a".format(cmd_base)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Test with data that yields the same span key (size 8).
        test_num += 1
        comment = ("Test case {0} - data with multiple lines per span "
                   "(no differences).".format(test_num))
        cmd_arg = 'multi_span_row:multi_span_row --run-all-tests'
        cmd = 'mysqldbcompare.py {0} {1} {2}'.format(s1_conn, s2_conn, cmd_arg)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Change data to detect all changed rows within the same span.
        self.server2.exec_query(
            'UPDATE multi_span_row.t SET data = 2 WHERE id != 1651723'
        )

        test_num += 1
        comment = ("Test case {0} - data with multiple lines per span "
                   "(with changed rows).".format(test_num))
        cmd_arg = 'multi_span_row:multi_span_row --run-all-tests'
        cmd = 'mysqldbcompare.py {0} {1} {2}'.format(s1_conn, s2_conn, cmd_arg)
        res = self.run_test_case(1, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Change data to detect missing rows within the same span.
        self.server2.exec_query(
            'DELETE FROM multi_span_row.t WHERE id = 1908449'
        )

        test_num += 1
        comment = ("Test case {0} - data with multiple lines per span "
                   "(with missing row and CSV format).".format(test_num))
        cmd_arg = 'multi_span_row:multi_span_row --run-all-tests --format=csv'
        cmd = 'mysqldbcompare.py {0} {1} {2}'.format(s1_conn, s2_conn, cmd_arg)
        res = self.run_test_case(1, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        self.do_replacements()

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def do_replacements(self):
        """Do replacements in the result.

        The following are necessary due to changes in character spaces
        introduced with Python 2.7.X in the difflib.
        """
        prefixes = ['***', '---', '+++']
        names = ['supplies', 'supplier', 'tools']
        for prefix in prefixes:
            for name in names:
                self.replace_result("{0} inventory.{1}".format(prefix, name),
                                    "{0} inventory.{1}\n".format(prefix, name))

        # Mask inconsistent Python 2.7 behavior
        self.replace_result("@@ -1 +1 @@", "@@ -1,1 +1,1 @@\n")
        self.replace_result("# @@ -1 +1 @@", "# @@ -1,1 +1,1 @@\n")

        self.replace_substring("on [::1]", "on localhost")

    def record(self):
        return self.save_result_file(__name__, self.results)

    def drop_all(self):
        """Drops all databases created.
        """
        self.drop_db(self.server1, "inventory")
        self.drop_db(self.server1, "inventory1")
        self.drop_db(self.server1, "inventory2")
        self.drop_db(self.server2, "inventory")
        self.drop_db(self.server2, "inventory_clone")
        self.drop_db(self.server1, 'db.`:db')
        self.drop_db(self.server2, 'db.`:db')
        self.drop_db(self.server1, 'db_diff_test')
        self.drop_db(self.server2, 'db_diff_test')
        self.drop_db(self.server1, "empty_db")
        self.drop_db(self.server2, "empty_db")
        self.drop_db(self.server1, "no_primary_keys")
        self.drop_db(self.server2, "no_primary_keys")
        self.drop_db(self.server1, "multi_span_row")
        self.drop_db(self.server2, "multi_span_row")
        return True

    def cleanup(self):
        if self.res_fname:
            os.unlink(self.res_fname)
        return self.drop_all()
