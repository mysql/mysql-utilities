#!/usr/bin/env python

import os
import test_sql_template
from mysql.utilities.exception import MUTLibError, UtilDBError

_TRIG_TABLE = "CREATE TABLE `diff_trig`.`t1` (a int)"
_DIFF_TABLE = "CREATE TABLE `diff_trig`.`t2` (a int, b char(30))"

# (comment, def1, def2, expected result)
_TRIGGER_TESTS = [ 
    ("Trigger definition",
     "CREATE TRIGGER diff_trig.trg BEFORE UPDATE ON diff_trig.t1 " + \
     "FOR EACH ROW INSERT INTO diff_trig.t2 VALUES(1, 'Wax on, wax off');",
     "CREATE TRIGGER diff_trig.trg AFTER INSERT ON diff_trig.t1 " + \
     "FOR EACH ROW INSERT INTO diff_trig.t2 VALUES(3, 'Wasabi?');",
     0),
]

class test(test_sql_template.test):
    """test mysqldiff --difftype=sql generation for triggers
    
    This test uses the test_sql_template for testing triggers.
    """

    def check_prerequisites(self):
        return test_sql_template.test.check_prerequisites(self)

    def setup(self):
        test_object = {
            'db1'             : 'diff_trig',
            'db2'             : 'diff_trig',
            'object_name'     : 'trg',
            'startup_cmds'    : [_TRIG_TABLE, _DIFF_TABLE],
            'shutdown_cmds'   : [],
        }
        for trigger in _TRIGGER_TESTS:
            new_test_obj = test_object.copy()
            new_test_obj['comment'] = trigger[0]
            new_test_obj['server1_object'] = trigger[1]
            new_test_obj['server2_object'] = trigger[2]
            new_test_obj['expected_result'] = trigger[3]
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
        return test_sql_template.test.cleanup(self)


