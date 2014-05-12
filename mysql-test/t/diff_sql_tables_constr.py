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
diff_sql_tables_constr test.
"""

import test_sql_template


_PARENT_TABLE = ("CREATE TABLE diff_table.t2 (a_i INT NOT NULL PRIMARY KEY) "
                 "ENGINE=INNODB;")

# Note: removing auto_increment does not work correctly.

# do tests for :
#  - primary key, no primary key
#  - foreign key, no foreign key
#  - unique index, no unique index
#  - various

# (comment, def1, def2, expected result, error_codes)
_TABLE_TESTS = [("Table constraints primary key",
                 "CREATE TABLE diff_table.t1(a INT NOT NULL PRIMARY KEY);",
                 "CREATE TABLE diff_table.t1(a INT NOT NULL);", 0, None),
                ("Table constraints foreign key",
                 "CREATE TABLE diff_table.t1(a INT NOT NULL, d INT) "
                 "ENGINE=INNODB;",
                 "CREATE TABLE diff_table.t1(a INT NOT NULL, d INT, "
                 "CONSTRAINT ref_t2 FOREIGN KEY(d) REFERENCES "
                 "diff_table.t2(a_i)) ENGINE=INNODB;", 0, None),
                ("Table constraints unique index",
                 "CREATE TABLE diff_table.t1(a INT NOT NULL, INDEX A1 (a));",
                 "CREATE TABLE diff_table.t1(a INT NOT NULL);", 0, None),
                ("Table constraints various",
                 "CREATE TABLE diff_table.t1(a INT NOT NULL PRIMARY KEY, "
                 "b char(30), d INT, CONSTRAINT ref_t2 "
                 "FOREIGN KEY(d) REFERENCES diff_table.t2(a_i), INDEX A1 (b)) "
                 "ENGINE=INNODB;",
                 "CREATE TABLE diff_table.t1(a INT NOT NULL) "
                 "ENGINE=INNODB;", 0, None),
                ]


class test(test_sql_template.test):
    """test mysqldiff --difftype=sql generation for table constraint changes

    This test uses the test_sql_template for testing tables.
    """

    utility = None

    def check_prerequisites(self):
        return test_sql_template.test.check_prerequisites(self)

    def setup(self):
        test_object = {'db1': 'diff_table', 'db2': 'diff_table',
                       'object_name': 't1', 'startup_cmds': [_PARENT_TABLE],
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
