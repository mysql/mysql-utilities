#!/usr/bin/env python

import os
import clone_db

from mysql.utilities.exception import MUTLibError

class test(clone_db.test):
    """check exclude parameter for clone db
    This test executes a series of clone database operations on a single
    server using a variety of --exclude options. It uses the clone_db test
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

        cmd_str = "mysqldbcopy.py %s %s --skip=grants " % (from_conn, to_conn)
        cmd_str += "util_test:util_db_clone "

        comment = "Test case 1 - exclude by name"
        cmd_opts = "--exclude=util_test.v1 --exclude=util_test.t4"
        res = self.run_test_case(0, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        clone_db.test.drop_db(self, self.server1, 'util_db_clone')

        comment = "Test case 2 - exclude by regex"
        cmd_opts = "--exclude=^e --exclude=4$ --regex "
        res = self.run_test_case(0, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        clone_db.test.drop_db(self, self.server1, 'util_db_clone')

        comment = "Test case 3 - exclude by name and regex"
        cmd_opts = "--exclude=^e --exclude=4$ --regex " + \
                   "--exclude=v1 --exclude=util_test.trg"
        res = self.run_test_case(0, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        return clone_db.test.cleanup(self)
