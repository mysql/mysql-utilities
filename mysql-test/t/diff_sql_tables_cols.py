#
# Copyright (c) 2010, 2016 Oracle and/or its affiliates. All rights reserved.
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
diff_sql_tables_cols test.
"""

import test_sql_template


# Note: removing auto_increment does not work correctly.

# (comment, def1, def2, expected result, error_codes)
_TABLE_TESTS = [
    ("Table single column change",
     "CREATE TABLE diff_table.t1(a int) ENGINE=InnoDB;",
     "CREATE TABLE diff_table.t1(b int) ENGINE=InnoDB;", 0, None),
    ("Table columns reversed",
     "CREATE TABLE diff_table.t1(a int, b char(20)) ENGINE=InnoDB;",
     "CREATE TABLE diff_table.t1(b char(20), a int) ENGINE=InnoDB;", 0, None),
    ("Table columns null vs not null",
     "CREATE TABLE diff_table.t1(a INT NOT NULL) ENGINE=InnoDB;",
     "CREATE TABLE diff_table.t1(a INT NULL) ENGINE=InnoDB;", 0, None),
    ("Table columns default",
     "CREATE TABLE diff_table.t1(a int default -1) ENGINE=InnoDB;",
     "CREATE TABLE diff_table.t1(a int) ENGINE=InnoDB;", 0, None),
    ("Table columns different defaults",
     "CREATE TABLE diff_table.t1(a int default 2) ENGINE=InnoDB;",
     "CREATE TABLE diff_table.t1(a int default 1) ENGINE=InnoDB;", 0, None),
    ("Table columns extra",
     "CREATE TABLE diff_table.t1(a int, t timestamp "
     "DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP) ENGINE=InnoDB;",
     "CREATE TABLE diff_table.t1(a int, t timestamp "
     "DEFAULT CURRENT_TIMESTAMP) ENGINE=InnoDB;", 0, None),
    ("Table columns comment",
     "CREATE TABLE diff_table.t1(a INT COMMENT 'boys') ENGINE=InnoDB;",
     "CREATE TABLE diff_table.t1(a int comment 'girls') ENGINE=InnoDB;",
     0, None),
    ("Table columns minor order change",
     "CREATE TABLE diff_table.t1(a int, b char(20), c datetime) "
     "ENGINE=InnoDB;",
     "CREATE TABLE diff_table.t1(c datetime, b char(20), a int) "
     "ENGINE=InnoDB;", 0, None),
    ("Table columns drop column",
     "CREATE TABLE diff_table.t1(a int, b char(30)) ENGINE=InnoDB;",
     "CREATE TABLE diff_table.t1(a int) ENGINE=InnoDB;", 0, None),
    ("Table columns various",
     "CREATE TABLE diff_table.t1(a int, b char(30), c float, d char(33)) "
     "ENGINE=InnoDB;",
     "CREATE TABLE diff_table.t1(a int, c float, d char(50)) "
     "ENGINE=InnoDB;", 0, None),
]


class test(test_sql_template.test):
    """test mysqldiff --difftype=sql generation for table column changes

    This test uses the test_sql_template for testing tables.
    """

    utility = None

    def check_prerequisites(self):
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
