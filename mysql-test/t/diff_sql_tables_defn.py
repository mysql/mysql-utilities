#!/usr/bin/env python

import os
import test_sql_template
from mysql.utilities.exception import MUTLibError, UtilDBError

# (comment, def1, def2, expected result, error_codes)
_TABLE_TESTS = [
    ("Table engine",
     "CREATE TABLE diff_table.t1(a int) ENGINE=MYISAM;",
     "CREATE TABLE diff_table.t1(a int) ENGINE=INNODB;",
     0, None),
    ("Table auto_increment",
     "CREATE TABLE diff_table.t1(a INT AUTO_INCREMENT NOT NULL PRIMARY KEY, " + \
     "b CHAR(10)) AUTO_INCREMENT=5;",
     "CREATE TABLE diff_table.t1(a INT AUTO_INCREMENT NOT NULL PRIMARY KEY, " + \
     "b CHAR(10)) AUTO_INCREMENT=10;",
     0, None),
    ("Table multiple options",
     "CREATE TABLE diff_table.t1(a INT AUTO_INCREMENT NOT NULL PRIMARY KEY, " + \
     "b CHAR(10)) AUTO_INCREMENT=5 ENGINE=INNODB;",
     "CREATE TABLE diff_table.t1(a INT AUTO_INCREMENT NOT NULL PRIMARY KEY, " + \
     "b CHAR(10)) AUTO_INCREMENT=10 ENGINE=MYISAM;",
     0, None),
    ("Table average row length",
     "CREATE TABLE diff_table.t1(a int) AVG_ROW_LENGTH=32;",
     "CREATE TABLE diff_table.t1(a int) AVG_ROW_LENGTH=128;",
     0, None),
    ("Table checksum",
     "CREATE TABLE diff_table.t1(a int) CHECKSUM=1;",
     "CREATE TABLE diff_table.t1(a int) CHECKSUM=0;",
     0, [1,0,1,1,0,0,1,1]), # Throws warning on direction=server1
    ("Table collation",
     "CREATE TABLE diff_table.t1(a int) COLLATE=latin1_swedish_ci;",
     "CREATE TABLE diff_table.t1(a int) COLLATE=latin1_bin;",
     0, None),
    ("Table comment",
     "CREATE TABLE diff_table.t1(a int) COMMENT='WHAT?';",
     "CREATE TABLE diff_table.t1(a int) COMMENT='WHO?';",
     0, None),
    ("Table comment only one table.",
     "CREATE TABLE diff_table.t1(a int) COMMENT='Doctor Who';",
     "CREATE TABLE diff_table.t1(a int);",
     0, None),
    ("Table other options",
     "CREATE TABLE diff_table.t1(a int) INSERT_METHOD=FIRST, PACK_KEYS=1;",
     "CREATE TABLE diff_table.t1(a int) INSERT_METHOD=LAST, PACK_KEYS=0;",
     0, None),
]

class test(test_sql_template.test):
    """test mysqldiff --difftype=sql generation for table definition changes
    
    This test uses the test_sql_template for testing tables.
    """

    def check_prerequisites(self):
        self.check_gtid_unsafe()
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


