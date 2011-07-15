#!/usr/bin/env python

import os
import clone_db

from mysql.utilities.exception import MUTLibError

# List of database objects for enumeration
DATABASE, TABLE, VIEW, TRIGGER, PROC, FUNC, EVENT, GRANT = "DATABASE", \
    "TABLE", "VIEW", "TRIGGER", "PROCEDURE", "FUNCTION", "EVENT", "GRANT"

class test(clone_db.test):
    """check parameters for clone db
    This test executes a series of clone database operations on a single
    server using a variety of parameters. It uses the clone_db test
    as a parent for setup and teardown methods.
    """

    def check_prerequisites(self):
        return clone_db.test.check_prerequisites(self)

    def setup(self):
        return clone_db.test.setup(self)

    def run(self):
        self.server1 = self.servers.get_server(0)
        self.res_fname = "result.txt"

        from_conn = "--source=" + self.build_connection_string(self.server1)
        to_conn = "--destination=" + self.build_connection_string(self.server1)

        cmd_str = "mysqldbcopy.py %s %s " % (from_conn, to_conn)

        # In this test, we execute a series of commands saving the results
        # from each run to perform a comparative check.

        cmd_opts = "util_test:util_db_clone"
        comment = "Test case 1 - normal run"
        res = self.run_test_case(0, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        comment = "Test case 2 - operation fails - need force"
        res = self.run_test_case(1, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        cmd_opts = "--help"
        comment = "Test case 3 - help"
        res = self.run_test_case(0, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        # We exercise --force here to ensure skips don't interfere
        cmd_opts = "--force --skip=data util_test:util_db_clone"
        comment = "Test case 4 - no data"
        res = self.run_test_case(0, cmd_str + cmd_opts, comment)
        self.results.append(self.check_objects(self.server1, "util_db_clone"))
        if not res:
            raise MUTLibError("%s: failed" % comment)

        cmd_opts = "--force --skip=data --quiet util_test:util_db_clone"
        comment = "Test case 5 - quiet clone"
        res = self.run_test_case(0, cmd_str + cmd_opts, comment)

        # Mask known platform-dependent lines
        self.replace_result("# Reading the file", "# Reading data file.\n")
        if not res:
            raise MUTLibError("%s: failed" % comment)

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        return clone_db.test.cleanup(self)
