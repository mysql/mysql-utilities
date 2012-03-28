#!/usr/bin/env python

import os
import test_sql_template
from mysql.utilities.exception import MUTLibError, UtilDBError

_TABLE1_DEF = """
    CREATE TABLE `comp_db`.`table1` (
        `stock_number` int(11) NOT NULL DEFAULT '0',
        `description` char(40) DEFAULT NULL,
        `qty` int(11) DEFAULT NULL,
        `cost` float(10,2) DEFAULT NULL,
        `type` enum('cleaning','washing','waxing','polishing','repair',
                    'drying','tools','other') DEFAULT NULL,
        `notes` char(4) DEFAULT NULL,
        `supplier` int(11) DEFAULT NULL,
        PRIMARY KEY (`stock_number`)
    ) ENGINE=MyISAM DEFAULT CHARSET=latin1;
"""

_SERVER1_TEST1 = [
"INSERT INTO comp_db.table1 VALUES (11036, 'Dried on wax remover', 1, 7.99, 'waxing', '', 1);",
"INSERT INTO comp_db.table1 VALUES (11173, 'Vinyl and rubber dressing', 1, 9.99, 'cleaning', '', 1);",
"INSERT INTO comp_db.table1 VALUES (11149, 'Interior scent +AC0- new car', 1, 6.99, 'cleaning', '', 1);",
"INSERT INTO comp_db.table1 VALUES (11153, 'Paint cleaning clay', 1, 19.99, 'cleaning', '', 1);",
"INSERT INTO comp_db.table1 VALUES (11035, 'Wheel cleaning clay', 1, 14.99, 'cleaning', '', 1);",
"INSERT INTO comp_db.table1 VALUES (11263, 'Red wax pad', 1, 4.99, 'waxing', '', 1);",
"INSERT INTO comp_db.table1 VALUES (11241, 'Orange polish pad', 1, 4.99, 'polishing', '', 1);",
"INSERT INTO comp_db.table1 VALUES (90211, 'Window wand set', 1, 8.99, 'cleaning', '', 1);",
"INSERT INTO comp_db.table1 VALUES (10628, 'Red wax pad', 1, 5.99, 'waxing', '', 1);",
"INSERT INTO comp_db.table1 VALUES (10626, 'Orange polish pad', 1, 5.99, 'polishing', '', 1);",
"INSERT INTO comp_db.table1 VALUES (10665, 'Glass polish pad', 3, 9.99, 'polishing', '', 1);",
"INSERT INTO comp_db.table1 VALUES (15736, 'Long wheel cleaning wand set', 1, 12.99, 'cleaning', '', 1);",
"INSERT INTO comp_db.table1 VALUES (15516, 'Dust brush set', 1, 12.99, 'cleaning', '', 1);",
"INSERT INTO comp_db.table1 VALUES (11034, 'Spray nozzles (extra)', 2, 2.99, 'other', '', 1);",
"INSERT INTO comp_db.table1 VALUES (10268, 'Wash mits', 2, 11.99, 'washing', '', 1);",
"INSERT INTO comp_db.table1 VALUES (11104, 'Interior cleaner', 1, 9.99, 'cleaning', '', 1);",
"INSERT INTO comp_db.table1 VALUES (11040, 'Leather care', 1, 9.99, 'other', '', 1);",
"INSERT INTO comp_db.table1 VALUES (67260, 'Wash bucket', 1, 39.99, 'tools', '', 1);",
"INSERT INTO comp_db.table1 VALUES (11205, 'Tire dressing applicator', 1, 5.99, 'other', '', 1);",
"INSERT INTO comp_db.table1 VALUES (11049, 'Glass cleaning clay', 1, 12.99, 'cleaning', '', 1);",
"INSERT INTO comp_db.table1 VALUES (11106, 'Wheel cleaner', 1, 9.99, 'cleaning', '', 1);",
"INSERT INTO comp_db.table1 VALUES (11141, 'Leather rejuvenator', 1, 12.99, 'other', '', 1);",
"INSERT INTO comp_db.table1 VALUES (10739, '3 inch orbital - 25 foot cord', 1, 109.99, 'tools', '', 1);",
"INSERT INTO comp_db.table1 VALUES (10765, '6 inch orbital - 10 foot cord', 1, 129.99, 'tools', '', 1);",
]

_SERVER2_TEST1 = [
"INSERT INTO comp_db.table1 VALUES (11036, 'Dried on wax remover', 1, 7.99, 'waxing', '', 1);",
"INSERT INTO comp_db.table1 VALUES (11173, 'Vinyl and rubber dressing', 1, 9.99, 'cleaning', '', 1);",
"INSERT INTO comp_db.table1 VALUES (11149, 'Interior scent +AC0- new car', 1, 6.99, 'cleaning', '', 1);",
"INSERT INTO comp_db.table1 VALUES (11153, 'Paint cleaning clay', 1, 19.99, 'cleaning', '', 1);",
"INSERT INTO comp_db.table1 VALUES (11263, 'Red wax pad', 1, 4.99, 'waxing', '', 1);",
"INSERT INTO comp_db.table1 VALUES (11241, 'Orange polish pad', 1, 4.99, 'polishing', '', 1);",
"INSERT INTO comp_db.table1 VALUES (10628, 'Red wax pad', 1, 5.99, 'waxing', '', 1);",
"INSERT INTO comp_db.table1 VALUES (10626, 'Orange polish pad', 1, 5.99, 'polishing', '', 1);",
"INSERT INTO comp_db.table1 VALUES (10665, 'Glass polish pad', 3, 9.99, 'polishing', '', 1);",
"INSERT INTO comp_db.table1 VALUES (15736, 'Long wheel cleaning wand set', 1, 12.99, 'cleaning', '', 1);",
"INSERT INTO comp_db.table1 VALUES (15516, 'Dust brush set', 1, 12.99, 'cleaning', '', 1);",
"INSERT INTO comp_db.table1 VALUES (11034, 'Spray nozzles (extra)', 2, 2.99, 'other', '', 1);",
"INSERT INTO comp_db.table1 VALUES (11117, 'Microfiber drying towel', 1, 26.99, 'drying', '', 1);",
"INSERT INTO comp_db.table1 VALUES (11115, 'Microfiber polish towel', 2, 16.99, 'polishing', '', 1);",
"INSERT INTO comp_db.table1 VALUES (11116, 'Microfiber wax removal towel', 3, 16.99, 'waxing', '', 1);",
"INSERT INTO comp_db.table1 VALUES (11269, 'Microfiber spray on car wash towel', 3, 16.99, 'cleaning', '', 1);",
"INSERT INTO comp_db.table1 VALUES (11104, 'Interior cleaner', 1, 9.99, 'cleaning', '', 1);",
"INSERT INTO comp_db.table1 VALUES (11040, 'Leather care', 1, 9.99, 'other', '', 1);",
"INSERT INTO comp_db.table1 VALUES (11080, 'Microfiber interior cleaning towel', 3, 9.99, 'cleaning', '', 1);",
"INSERT INTO comp_db.table1 VALUES (11205, 'Tire dressing applicator', 1, 5.99, 'other', '', 1);",
"INSERT INTO comp_db.table1 VALUES (11049, 'Glass cleaning clay', 1, 12.99, 'cleaning', '', 1);",
"INSERT INTO comp_db.table1 VALUES (11106, 'Wheel cleaner', 1, 9.99, 'cleaning', '', 1);",
"INSERT INTO comp_db.table1 VALUES (11141, 'Leather rejuvenator', 1, 12.99, 'other', '', 1);",
"INSERT INTO comp_db.table1 VALUES (10739, '3 inch orbital - 25 foot cord', 1, 109.99, 'tools', '', 1);",
"INSERT INTO comp_db.table1 VALUES (10765, '6 inch orbital - 10 foot cord', 1, 129.99, 'tools', '', 1);",
]

_SERVER1_TEST2 = [
"INSERT INTO comp_db.table1 VALUES (11136, 'Rubber cleaner', 1, 9.99, 'cleaning', '', 1);",
"INSERT INTO comp_db.table1 VALUES (11065, 'Spray on car crash', 1, 14.99, 'washing', '', 1);",
"INSERT INTO comp_db.table1 VALUES (11138, 'Over carriage spray', 1, 13.99, 'cleaning', '', 1);",
"INSERT INTO comp_db.table1 VALUES (11270, 'Carpet cleaner', 1, 9.99, 'cleaning', '', 1);",
"INSERT INTO comp_db.table1 VALUES (11108, 'Window cleaner', 1, 6.99, 'cleaning', '', 1);",
"INSERT INTO comp_db.table1 VALUES (11146, 'Speed shine', 1, 9.99, 'repair', '', 1);",
"INSERT INTO comp_db.table1 VALUES (11135, 'Paint prep', 1, 12.99, 'repair', '', 1);",
"INSERT INTO comp_db.table1 VALUES (12980, 'Bug off', 1, 14.99, 'other', '', 1);",
"INSERT INTO comp_db.table1 VALUES (11098, 'Spray on wax', 2, 12.99, 'waxing', '', 1);",
"INSERT INTO comp_db.table1 VALUES (11171, 'Best of show wax', 1, 19.99, 'waxing', '', 1);",
"INSERT INTO comp_db.table1 VALUES (11017, 'Fine glass polish', 1, 15.99, 'polishing', '', 1);",
"INSERT INTO comp_db.table1 VALUES (11102, 'Car wash', 1, 7.99, 'washing', '', 1);",
"INSERT INTO comp_db.table1 VALUES (11186, 'Plastic polish', 1, 9.99, 'polishing', '', 1);",
"INSERT INTO comp_db.table1 VALUES (11185, 'Face cleaner', 1, 0.00, 'polishing', '', 33);",
]

_SERVER2_TEST2 = [
"INSERT INTO comp_db.table1 VALUES (11136, 'Rubber cleaner', 1, 9.99, 'cleaning', '', 1);",
"INSERT INTO comp_db.table1 VALUES (11065, 'Spray on car wash', 1, 14.99, 'washing', '', 1);",
"INSERT INTO comp_db.table1 VALUES (11138, 'Under carriage spray', 1, 13.99, 'cleaning', '', 1);",
"INSERT INTO comp_db.table1 VALUES (11270, 'Carpet cleaner', 1, 9.99, 'cleaning', '', 1);",
"INSERT INTO comp_db.table1 VALUES (11108, 'Window cleaner', 1, 6.99, 'cleaning', '', 1);",
"INSERT INTO comp_db.table1 VALUES (11146, 'Speed shine', 1, 9.99, 'repair', '', 1);",
"INSERT INTO comp_db.table1 VALUES (11135, 'Paint prep', 1, 12.99, 'repair', '', 1);",
"INSERT INTO comp_db.table1 VALUES (12980, 'Bug off', 1, 14.99, 'other', '', 1);",
"INSERT INTO comp_db.table1 VALUES (11098, 'Paint on wax', 2, 12.99, 'waxing', '', 1);",
"INSERT INTO comp_db.table1 VALUES (11171, 'Worst of show wax', 1, 19.99, 'waxing', '', 1);",
"INSERT INTO comp_db.table1 VALUES (11017, 'Fine glass polish', 1, 15.99, 'polishing', '', 1);",
"INSERT INTO comp_db.table1 VALUES (11102, 'Car wash', 1, 7.99, 'washing', '', 1);",
"INSERT INTO comp_db.table1 VALUES (11186, 'Plastic polish', 1, 9.99, 'polishing', '', 1);",
"INSERT INTO comp_db.table1 VALUES (11185, 'Foot cleaner', 1, 13.01, 'repair', '', 1);",
]

# (comment, def1, def2, expected result)
_TABLE_CONSISTENCY_TESTS = [ 
    ("Table consistency and transform drops and inserts only",
     _SERVER1_TEST1,
     _SERVER2_TEST1,
     None),
    ("Table consistency and transform updates only",
     _SERVER1_TEST2,
     _SERVER2_TEST2,
     None),
    ("Table consistency all changes",
     _SERVER1_TEST1 + _SERVER1_TEST2,
     _SERVER2_TEST1 + _SERVER2_TEST2,
     None),
    ("Table consistency no changes",
     _SERVER1_TEST1 + _SERVER1_TEST2,
     _SERVER1_TEST1 + _SERVER1_TEST2,
     [0,0,0,0,0,0,0,0]),   # All tests should return 0
]

class test(test_sql_template.test):
    """test mysqldbcompare --difftype=sql generation for table consistency checks
    
    This test uses the test_sql_template for testing.
    """

    def check_prerequisites(self):
        self.check_gtid_unsafe()
        return test_sql_template.test.check_prerequisites(self)

    def setup(self):
        test_object = {
            'db1'             : 'comp_db',
            'db2'             : 'comp_db',
            'object_name'     : '',
            'startup_cmds'    : [],
            'shutdown_cmds'   : [],
        }
        for tbl_check in _TABLE_CONSISTENCY_TESTS:
            new_test_obj = test_object.copy()
            new_test_obj['comment'] = tbl_check[0]
            new_test_obj['server1_object'] = _TABLE1_DEF
            new_test_obj['server2_object'] = _TABLE1_DEF
            new_test_obj['server1_data'] = tbl_check[1]
            new_test_obj['server2_data'] = tbl_check[2]
            new_test_obj['expected_result'] = 0
            new_test_obj['error_codes'] = tbl_check[3]
            self.test_objects.append(new_test_obj)

        self.utility = 'mysqldbcompare.py -a'
        
        return test_sql_template.test.setup(self)
    
    def run(self):
        return test_sql_template.test.run(self)
          
    def get_result(self):
        return test_sql_template.test.get_result(self)

    def record(self):
        return True # Not a comparative test
    
    def cleanup(self):
        return test_sql_template.test.cleanup(self)




