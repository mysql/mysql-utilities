#
# Copyright (c) 2010, 2013, Oracle and/or its affiliates. All rights reserved.
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
import os
import test_sql_template
from mysql.utilities.exception import MUTLibError, UtilDBError

_DIFF_TABLE = "CREATE TABLE `diff_event`.`t1` (a char(30))"

# interval, on completion, status, body
# (comment, def1, def2, expected result)
_EVENT_TESTS = [ 
    ("Event schedule interval",
     "CREATE definer=root@localhost EVENT diff_event.e1 " + \
     "ON SCHEDULE EVERY 2 YEAR STARTS '2011-11-11 20:00:00' DISABLE " + \
     "DO DELETE FROM diff_event.t1 WHERE a = 'not there';",
     "CREATE definer=root@localhost EVENT diff_event.e1 " + \
     "ON SCHEDULE EVERY 1 YEAR STARTS '2011-11-11 20:00:00' DISABLE " + \
     "DO DELETE FROM diff_event.t1 WHERE a = 'not there';",
     0),
    ("Event on completion",
     "CREATE definer=root@localhost EVENT diff_event.e1 " + \
     "ON SCHEDULE EVERY 1 YEAR STARTS '2011-11-11 20:00:00' " + \
     "ON COMPLETION PRESERVE DISABLE " + \
     "DO DELETE FROM diff_event.t1 WHERE a = 'not there';",
     "CREATE definer=root@localhost EVENT diff_event.e1 " + \
     "ON SCHEDULE EVERY 1 YEAR STARTS '2011-11-11 20:00:00' " + \
     "ON COMPLETION NOT PRESERVE DISABLE " + \
     "DO DELETE FROM diff_event.t1 WHERE a = 'not there';",
     0),
    ("Event schedule interval",
     "CREATE definer=root@localhost EVENT diff_event.e1 " + \
     "ON SCHEDULE EVERY 1 YEAR STARTS '2011-11-11 20:00:00' DISABLE " + \
     "DO DELETE FROM diff_event.t1 WHERE a = 'not there';",
     "CREATE definer=root@localhost EVENT diff_event.e1 " + \
     "ON SCHEDULE EVERY 1 YEAR STARTS '2011-11-11 20:00:00' DISABLE ON SLAVE " + \
     "DO DELETE FROM diff_event.t1 WHERE a = 'not there';",
     0),
    ("Event body",
     "CREATE definer=root@localhost EVENT diff_event.e1 " + \
     "ON SCHEDULE EVERY 1 YEAR STARTS '2011-11-11 20:00:00' DISABLE " + \
     "DO DELETE FROM diff_event.t1 WHERE a = 'not there';",
     "CREATE definer=root@localhost EVENT diff_event.e1 " + \
     "ON SCHEDULE EVERY 1 YEAR STARTS '2011-11-11 20:00:00' DISABLE " + \
     "DO DELETE FROM diff_event.t1 WHERE a = 'it is there';",
     0),
]

class test(test_sql_template.test):
    """test mysqldiff --difftype=sql generation for events
    
    This test uses the test_sql_template for testing events.
    """

    def check_prerequisites(self):
        return test_sql_template.test.check_prerequisites(self)

    def setup(self):
        test_object = {
            'db1'             : 'diff_event',
            'db2'             : 'diff_event',
            'object_name'     : '',
            'startup_cmds'    : [_DIFF_TABLE],
            'shutdown_cmds'   : [],
        }
        for event in _EVENT_TESTS:
            new_test_obj = test_object.copy()
            new_test_obj['comment'] = event[0]
            new_test_obj['server1_object'] = event[1]
            new_test_obj['server2_object'] = event[2]
            new_test_obj['expected_result'] = event[3]
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


