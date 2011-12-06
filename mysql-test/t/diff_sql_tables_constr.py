#!/usr/bin/env python

import os
import test_sql_template
from mysql.utilities.exception import MUTLibError, UtilDBError

_PARENT_TABLE = "CREATE TABLE diff_table.t2 (a_i int not null " + \
                "primary key) engine=Innodb;"

# Note: removing auto_increment does not work correctly.

# do tests for :
#  - primary key, no primary key
#  - foreign key, no foreign key
#  - unique index, no unique index
#  - various

# (comment, def1, def2, expected result, error_codes)
_TABLE_TESTS = [
    ("Table constraints primary key",
     "CREATE TABLE diff_table.t1(a int not null primary key);",
     "CREATE TABLE diff_table.t1(a int not null);",
     0, None),
    ("Table constraints foreign key",
     "CREATE TABLE diff_table.t1(a int not null, d int) " + \
     "ENGINE=INNODB;",
     "CREATE TABLE diff_table.t1(a int not null, d int, " + \
     "CONSTRAINT ref_t2 FOREIGN KEY(d) REFERENCES diff_table.t2(a_i)) " + \
     "ENGINE=INNODB;",
     0, None),
    ("Table constraints unique index",
     "CREATE TABLE diff_table.t1(a int not null, INDEX A1 (a));",
     "CREATE TABLE diff_table.t1(a int not null);",
     0, None),
    ("Table constraints various",
     "CREATE TABLE diff_table.t1(a int not null primary key, b char(30), " + \
     "d int, CONSTRAINT ref_t2 FOREIGN KEY(d) REFERENCES " + \
     "diff_table.t2(a_i), INDEX A1 (b)) ENGINE=INNODB;",
     "CREATE TABLE diff_table.t1(a int not null) ENGINE=INNODB;",
     0, None),
]

class test(test_sql_template.test):
    """test mysqldiff --difftype=sql generation for table constraint changes
    
    This test uses the test_sql_template for testing tables.
    """

    def check_prerequisites(self):
        return test_sql_template.test.check_prerequisites(self)

    def setup(self):
        test_object = {
            'db1'             : 'diff_table',
            'db2'             : 'diff_table',
            'object_name'     : 't1',
            'startup_cmds'    : [_PARENT_TABLE],
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


