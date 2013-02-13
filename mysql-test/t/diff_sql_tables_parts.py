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

# TODO: Partitions are not supported at this time, so the following
#       test is only a placeholder for the future work. Once completed,
#       the test can be changed to include tests for partition
#       transformations.

# (comment, def1, def2, expected result, error_codes)
_TABLE_TESTS = [
    ("Table partition test placeholder",
     "CREATE TABLE diff_table.t1(a int, b int, c char(33)) " + \
     "PARTITION BY KEY(a);",
     "CREATE TABLE diff_table.t1(a int, b int, c char(33)) " + \
     "PARTITION BY KEY(b);", 
     0, [1,0,1,1,0,1,1,1]),
]

class test(test_sql_template.test):
    """test mysqldiff --difftype=sql generation for table partition changes
    
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


