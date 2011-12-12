#!/usr/bin/env python

import os
import export_parameters_def
from mysql.utilities.exception import MUTLibError

class test(export_parameters_def.test):
    """check exclude parameter for export utility
    This test executes a series of export database operations on a single
    server using a variety of exclude options. It uses the
    export_parameters_def test as a parent for setup and teardown methods.
    """

    def check_prerequisites(self):
        return export_parameters_def.test.check_prerequisites(self)

    def setup(self):
        return export_parameters_def.test.setup(self)

    def run(self):
        self.res_fname = "result.txt"

        from_conn = "--server=" + self.build_connection_string(self.server1)

        cmd_str = "mysqldbexport.py --skip=events,grants --no-headers " + \
                  " %s --format=CSV util_test " % from_conn

        comment = "Test case 1 - exclude by name"
        cmd_opts = "--exclude=util_test.v1 --exclude=util_test.t4"
        res = self.run_test_case(0, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        comment = "Test case 2 - exclude by regex"
        cmd_opts = "-x ^f -x 4$ --regexp"
        res = self.run_test_case(0, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        comment = "Test case 3 - exclude by name and regex"
        cmd_opts = "--exclude=^f --exclude=4$ -x ^p " + \
                   "--exclude=v1 --exclude=util_test.trg --regexp"
        res = self.run_test_case(0, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        comment = "Test case 4 - exclude everything by regex"
        cmd_opts = "-x 1 -x t --exclude=util_test.trg --regexp"
        res = self.run_test_case(0, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        export_parameters_def.test._mask_csv(self)

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        return export_parameters_def.test.cleanup(self)
