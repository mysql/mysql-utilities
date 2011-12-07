#!/usr/bin/env python

import os
import test_sql_template
from mysql.utilities.exception import MUTLibError, UtilDBError

# Note: removing auto_increment does not work correctly.

# (comment, def1, def2, expected result, error_codes)
_TABLE_TESTS = [
    ("Table single column change",
     "CREATE TABLE diff_table.t1(a int);",
     "CREATE TABLE diff_table.t1(b int);",
     0, None),
    ("Table columns reversed",
     "CREATE TABLE diff_table.t1(a int, b char(20));",
     "CREATE TABLE diff_table.t1(b char(20), a int);",
     0, None),
    ("Table columns null vs not null",
     "CREATE TABLE diff_table.t1(a INT NOT NULL);",
     "CREATE TABLE diff_table.t1(a INT NULL);",
     0, None),
    ("Table columns default",
     "CREATE TABLE diff_table.t1(a int default -1);",
     "CREATE TABLE diff_table.t1(a int);",
     0, None),
    ("Table columns different defaults",
     "CREATE TABLE diff_table.t1(a int default 2);",
     "CREATE TABLE diff_table.t1(a int default 1);",
     0, None),
    ("Table columns extra",
     "CREATE TABLE diff_table.t1(a int, t timestamp on update CURRENT_TIMESTAMP);",
     "CREATE TABLE diff_table.t1(a int, t timestamp);",
     0, None),
    ("Table columns comment",
     "CREATE TABLE diff_table.t1(a INT COMMENT 'boys');",
     "CREATE TABLE diff_table.t1(a int comment 'girls');",
     0, None),
    ("Table columns minor order change",
     "CREATE TABLE diff_table.t1(a int, b char(20), c datetime);",
     "CREATE TABLE diff_table.t1(c datetime, b char(20), a int);",
     0, None),
    ("Table columns drop column",
     "CREATE TABLE diff_table.t1(a int, b char(30));",
     "CREATE TABLE diff_table.t1(a int);",
     0, None),
    ("Table columns various",
     "CREATE TABLE diff_table.t1(a int, b char(30), c float, d char(33));",
     "CREATE TABLE diff_table.t1(a int, c float, d char(50));",
     0, None),
]

class test(test_sql_template.test):
    """test mysqldiff --difftype=sql generation for table column changes
    
    This test uses the test_sql_template for testing tables.
    """

    def check_prerequisites(self):
        return test_sql_template.test.check_prerequisites(self)

    def setup(self):
        test_object = {
            'db1'             : 'diff_table',
            'db2'             : 'diff_table',
            'object_name'     : 't1',
            'startup_cmds'    : [],
            'shutdown_cmds'   : [],
        }
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
        return True # Not a comparative test
    
    def cleanup(self):
        try:
            self.server1.exec_query(_DROP_TABLE_DB)
        except:
            pass
        try:
            self.server2.exec_query(_DROP_TABLE_DB)
        except:
            pass
        return test_sql_template.test.cleanup(self)


