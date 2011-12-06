#!/usr/bin/env python

import os
import test_sql_template
from mysql.utilities.exception import MUTLibError, UtilDBError

_TEST_VIEW_TABLE = "CREATE TABLE `diff_view`.`t1` (a int)"

# (comment, def1, def2, expected result)
_VIEW_TESTS = [ 
    ("View definition",
     "CREATE VIEW diff_view.v1 as SELECT 1;",
     "CREATE VIEW diff_view.v1 as SELECT 2;",
     0),
    ("View definer",
     "CREATE definer='root'@'localhost' VIEW diff_view.v1 as SELECT 3;",
     "CREATE definer='joe'@'otherhost' VIEW diff_view.v1 as SELECT 3;",
     0),
    ("View security",
     "CREATE SQL SECURITY DEFINER VIEW diff_view.v1 as SELECT 4;",
     "CREATE SQL SECURITY INVOKER VIEW diff_view.v1 as SELECT 4;",
     0),
    ("View check option",
     "CREATE VIEW diff_view.v1 as SELECT * FROM `diff_view`.`t1` " + \
     "WHERE a < 11 WITH CASCADED CHECK OPTION;",
     "CREATE VIEW diff_view.v1 as SELECT * FROM `diff_view`.`t1` " + \
     "WHERE a < 11;",
     0),
]

class test(test_sql_template.test):
    """test mysqldiff --difftype=sql generation for views
    
    This test uses the test_sql_template for testing views.
    """

    def check_prerequisites(self):
        return test_sql_template.test.check_prerequisites(self)

    def setup(self):
        test_object = {
            'db1'             : 'diff_view',
            'db2'             : 'diff_view',
            'object_name'     : 'v1',
            'startup_cmds'    : [_TEST_VIEW_TABLE],
            'shutdown_cmds'   : [],
        }
        for view in _VIEW_TESTS:
            new_test_obj = test_object.copy()
            new_test_obj['comment'] = view[0]
            new_test_obj['server1_object'] = view[1]
            new_test_obj['server2_object'] = view[2]
            new_test_obj['expected_result'] = view[3]
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
            self.server1.exec_query(_DROP_VIEW_DB)
        except:
            pass
        try:
            self.server2.exec_query(_DROP_VIEW_DB)
        except:
            pass
        return test_sql_template.test.cleanup(self)


