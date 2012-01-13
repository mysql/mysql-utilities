#!/usr/bin/env python

import os
import mutlib
import copy_db_parameters
from mysql.utilities.exception import MUTLibError

class test(copy_db_parameters.test):
    """Export Data
    This test executes the export utility on a single server. It uses the
    copy_db_parameters test to setup.
    """

    def check_prerequisites(self):
        return copy_db_parameters.test.check_prerequisites(self)

    def setup(self):
        return copy_db_parameters.test.setup(self)

    def run(self):
        self.res_fname = "result.txt"

        from_conn = "--server=%s" % self.build_connection_string(self.server1)

        cmd = "mysqldbexport.py %s util_test  " % from_conn

        comment = "Test case 1 - export metadata only"
        cmd_str = cmd + " --export=definitions --format=SQL --skip=events "
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        comment = "Test case 2 - export data only - single rows"
        cmd_str = cmd + " --export=data --format=SQL "
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        comment = "Test case 3 - export data only - bulk insert"
        cmd_str = cmd + " --export=DATA --format=SQL --bulk-insert"
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        comment = "Test case 4 - export data and metadata"
        cmd_str = cmd + " --export=both --format=SQL --skip=events"
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        comment = "Test case 5 - export data and metadata with quiet"
        cmd_str = cmd + " --export=both --format=SQL --skip=events --quiet"
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        comment = "Test case 6 - export data and metadata with debug"
        cmd_str = cmd + " --export=both --format=SQL --skip=events -vvv"
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        self.replace_result("Time:", "Time:       XXXXXX\n")

        _REPLACEMENTS = ("PROCEDURE", "FUNCTION", "TRIGGER", "SQL")

        for replace in _REPLACEMENTS:
            self.mask_result_portion("CREATE", "DEFINER=", replace,
                                     "DEFINER=`XXXX`@`XXXXXXXXX` ")

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def drop_db(self, server, db):
        # Check before you drop to avoid warning
        try:
            res = server.exec_query("SHOW DATABASES LIKE 'util_%%'")
        except:
            return True # Ok to exit here as there weren't any dbs to drop
        try:
            res = server.exec_query("DROP DATABASE %s" % db)
        except:
            return False
        return True

    def drop_all(self):
        try:
            self.drop_db(self.server1, "util_test")
        except:
            return False
        return True

    def cleanup(self):
        return copy_db_parameters.test.cleanup(self)
