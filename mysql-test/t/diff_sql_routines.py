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

_PROC_TABLE = "CREATE TABLE `diff_routine`.`t1` (b char(30))"

# Need tests for access, security, comment, body (drop+create)

# (comment, def1, def2, expected result, object_name, startup_cmds)
_ROUTINE_TESTS = [
    # Procedure tests
    ("Procedure access",
     "CREATE definer=root@localhost PROCEDURE diff_routine.p1(p1 CHAR(20)) " + \
     "CONTAINS SQL " + \
     "INSERT INTO diff_routine.t1 VALUES ('50');",
     "CREATE definer=root@localhost PROCEDURE diff_routine.p1(p1 CHAR(20)) " + \
     "NO SQL " + \
     "INSERT INTO diff_routine.t1 VALUES ('50');",
     0, "p1", [_PROC_TABLE]),
    ("Procedure security",
     "CREATE definer=root@localhost PROCEDURE diff_routine.p1(p1 CHAR(20)) " + \
     "SQL SECURITY INVOKER " + \
     "INSERT INTO diff_routine.t1 VALUES ('50');",
     "CREATE definer=root@localhost PROCEDURE diff_routine.p1(p1 CHAR(20)) " + \
     "SQL SECURITY DEFINER " + \
     "INSERT INTO diff_routine.t1 VALUES ('50');",
     0, "p1", [_PROC_TABLE]),
    ("Procedure comment",
     "CREATE PROCEDURE diff_routine.p1(p1 CHAR(20)) " + \
     "COMMENT 'Test 123' " + \
     "INSERT INTO diff_routine.t1 VALUES ('50');",
     "CREATE PROCEDURE diff_routine.p1(p1 CHAR(20)) " + \
     "COMMENT 'Test 456' " + \
     "INSERT INTO diff_routine.t1 VALUES ('50');",
     0, "p1", [_PROC_TABLE]),
    ("Procedure body - generates DROP+CREATE",
     "CREATE PROCEDURE diff_routine.p1(p1 CHAR(20)) " + \
     "INSERT INTO diff_routine.t1 VALUES ('50');",
     "CREATE PROCEDURE diff_routine.p1(p1 CHAR(20)) " + \
     "INSERT INTO diff_routine.t1 VALUES ('100');",
     0, "p1", [_PROC_TABLE]),
    
    # Function tests
    ("Function access",
     "CREATE definer=root@localhost FUNCTION diff_routine.f1() " + \
     "RETURNS INT CONTAINS SQL DETERMINISTIC RETURN (SELECT 1);",
     "CREATE definer=root@localhost FUNCTION diff_routine.f1() " + \
     "RETURNS INT NO SQL DETERMINISTIC RETURN (SELECT 1);",
     0, "f1", []),
    ("Function security",
     "CREATE definer=root@localhost FUNCTION diff_routine.f1() " + \
     "RETURNS INT SQL SECURITY INVOKER DETERMINISTIC RETURN (SELECT 1);",
     "CREATE definer=root@localhost FUNCTION diff_routine.f1() " + \
     "RETURNS INT SQL SECURITY DEFINER DETERMINISTIC RETURN (SELECT 1);",
     0, "f1", []),
    ("Function comment",
     "CREATE FUNCTION diff_routine.f1() " + \
     "RETURNS INT COMMENT 'Test 123' DETERMINISTIC RETURN (SELECT 1);",
     "CREATE FUNCTION diff_routine.f1() " + \
     "RETURNS INT COMMENT 'Test 456' DETERMINISTIC RETURN (SELECT 1);",
     0, "f1", []),
    ("Function body - generates DROP+CREATE",
     "CREATE FUNCTION diff_routine.f1() " + \
     "RETURNS INT DETERMINISTIC RETURN (SELECT 1);",
     "CREATE FUNCTION diff_routine.f1() " + \
     "RETURNS INT DETERMINISTIC RETURN (SELECT 2);",
     0, "f1", []),
]

class test(test_sql_template.test):
    """test mysqldiff --difftype=sql generation for routines
    
    This test uses the test_sql_template for testing routines.
    """

    def check_prerequisites(self):
        return test_sql_template.test.check_prerequisites(self)

    def setup(self):
        test_object = {
            'db1'             : 'diff_routine',
            'db2'             : 'diff_routine',
            'shutdown_cmds'   : [],
        }
        for routine in _ROUTINE_TESTS:
            new_test_obj = test_object.copy()
            new_test_obj['comment'] = routine[0]
            new_test_obj['server1_object'] = routine[1]
            new_test_obj['server2_object'] = routine[2]
            new_test_obj['expected_result'] = routine[3]
            new_test_obj['object_name'] = routine[4]
            new_test_obj['startup_cmds'] = routine[5]
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


