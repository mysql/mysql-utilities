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
diff_sql_tables_defn test.
"""

import test_sql_template


# (comment, def1, def2, expected result, error_codes)
_TABLE_TESTS = [
    ("Table engine",
     "CREATE TABLE diff_table.t1(a int) ENGINE=MYISAM;",
     "CREATE TABLE diff_table.t1(a int) ENGINE=INNODB;", 0, None),
    # This test is failing using MySQL Server 5.6.12 due to a bug:
    # http://clustra.no.oracle.com/orabugs/bug.php?id=16629820
    #
    # ("Table auto_increment",
    #  "CREATE TABLE diff_table.t1(a INT AUTO_INCREMENT NOT NULL
    # PRIMARY KEY, "
    #  "b CHAR(10)) AUTO_INCREMENT=5;",
    #  "CREATE TABLE diff_table.t1(a INT AUTO_INCREMENT NOT NULL
    # PRIMARY KEY, "
    #  "b CHAR(10)) AUTO_INCREMENT=10;",
    #  0, None),
    ("Table multiple options",
     "CREATE TABLE diff_table.t1(a INT AUTO_INCREMENT NOT NULL "
     "PRIMARY KEY, "
     "b CHAR(10)) AUTO_INCREMENT=5 ENGINE=INNODB;",
     "CREATE TABLE diff_table.t1(a INT AUTO_INCREMENT NOT NULL "
     "PRIMARY KEY, "
     "b CHAR(10)) AUTO_INCREMENT=10 ENGINE=MYISAM;", 0, None),
    ("Table average row length",
     "CREATE TABLE diff_table.t1(a int) AVG_ROW_LENGTH=32 "
     "ENGINE=INNODB;",
     "CREATE TABLE diff_table.t1(a int) AVG_ROW_LENGTH=128 "
     "ENGINE=INNODB;", 0, None),
    ("Table checksum",
     "CREATE TABLE diff_table.t1(a int) CHECKSUM=1 ENGINE=INNODB;",
     "CREATE TABLE diff_table.t1(a int) CHECKSUM=0 ENGINE=INNODB;",
     0, [1, 0, 1, 1, 0, 0, 1, 1]),
    # Throws warning on direction=server1
    ("Table collation",
     "CREATE TABLE diff_table.t1(a int) "
     "COLLATE=latin1_swedish_ci;",
     "CREATE TABLE diff_table.t1(a int) COLLATE=latin1_bin;", 0,
     None),
    ("Table comment",
     "CREATE TABLE diff_table.t1(a int) COMMENT='WHAT?' "
     "ENGINE=INNODB;",
     "CREATE TABLE diff_table.t1(a int) COMMENT='WHO?' "
     "ENGINE=INNODB;", 0, None),
    ("Table comment only one table.",
     "CREATE TABLE diff_table.t1(a int) COMMENT='Doctor Who' "
     "ENGINE=INNODB;",
     "CREATE TABLE diff_table.t1(a int) ENGINE=INNODB;", 0, None),
    ("Table other options",
     "CREATE TABLE diff_table.t1(a int) INSERT_METHOD=FIRST, "
     "PACK_KEYS=1 ENGINE=INNODB;",
     "CREATE TABLE diff_table.t1(a int) INSERT_METHOD=LAST, "
     "PACK_KEYS=0 ENGINE=INNODB;", 0, None),
    ("Table column order",
     "CREATE TABLE diff_table.t1(a int, b int, c int) "
     "ENGINE=INNODB;",
     "CREATE TABLE diff_table.t1(b int, a int, c int) "
     "ENGINE=INNODB;", 0, None),
    ("Table index order",
     "CREATE TABLE diff_table.t1(a int, b int, KEY a (a), "
     "KEY b (b)) ENGINE=INNODB;",
     "CREATE TABLE diff_table.t1(b int, a int, KEY b (b), "
     "KEY a (a)) ENGINE=INNODB;", 0, None),
]


class test(test_sql_template.test):
    """test mysqldiff --difftype=sql generation for table definition changes

    This test uses the test_sql_template for testing tables.
    """

    utility = None

    def check_prerequisites(self):
        self.check_gtid_unsafe()
        return test_sql_template.test.check_prerequisites(self)

    def setup(self, spawn_servers=True):
        test_object = {'db1': 'diff_table', 'db2': 'diff_table',
                       'object_name': 't1', 'startup_cmds': [],
                       'shutdown_cmds': [], }
        for table in _TABLE_TESTS:
            new_test_obj = test_object.copy()
            new_test_obj['comment'] = table[0]
            new_test_obj['server1_object'] = table[1]
            new_test_obj['server2_object'] = table[2]
            new_test_obj['expected_result'] = table[3]
            new_test_obj['error_codes'] = table[4]
            self.test_objects.append(new_test_obj)

        self.utility = 'mysqldiff.py'

        return test_sql_template.test.setup(self)

    def run(self):
        return test_sql_template.test.run(self)

    def get_result(self):
        return test_sql_template.test.get_result(self)

    def record(self):
        return True  # Not a comparative test

    def cleanup(self):
        return test_sql_template.test.cleanup(self)
