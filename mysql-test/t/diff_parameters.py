#!/usr/bin/env python

import os
import diff
from mysql.utilities.exception import MUTLibError

_FORMATS = ['unified','context','differ']
_DIRECTIONS = ['server1', 'server2']

class test(diff.test):
    """check parameters for diff
    This test executes a series of diff database operations on two
    servers using a variety of parameters. It uses the diff test
    as a parent for setup and teardown methods.
    """

    def check_prerequisites(self):
        return diff.test.check_prerequisites(self)

    def setup(self):
        return diff.test.setup(self)

    def run(self):
        self.server1 = self.servers.get_server(0)
        self.res_fname = "result.txt"

        s1_conn = "--server1=" + self.build_connection_string(self.server1)
        s2_conn = "--server2=" + self.build_connection_string(self.server2)
       
        cmd_str = "mysqldiff.py %s %s util_test:util_test " % \
                  (s1_conn, s2_conn)

        test_num = 1
        cmd_opts = " --help"
        comment = "Test case %d - Use%s " % (test_num, cmd_opts)
        res = self.run_test_case(0, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        for format in _FORMATS:
            test_num += 1
            cmd_opts = " --difftype=%s" % format
            comment = "Test case %d - Use diff %s" % (test_num, cmd_opts)
            res = self.run_test_case(1, cmd_str + cmd_opts, comment)
            if not res:
                raise MUTLibError("%s: failed" % comment)

        test_num += 1
        cmd_opts = " --force"
        comment = "Test case %d - Use%s " % (test_num, cmd_opts)
        res = self.run_test_case(1, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        test_num += 1
        cmd_opts = " --quiet"
        comment = "Test case %d - Use%s " % (test_num, cmd_opts)
        res = self.run_test_case(1, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        test_num += 1
        cmd_opts = " --width=65" 
        comment = "Test case %d - Use%s " % (test_num, cmd_opts)
        res = self.run_test_case(1, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        test_num += 1
        cmd_opts = " --width=55" 
        comment = "Test case %d - Use%s " % (test_num, cmd_opts)
        res = self.run_test_case(1, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        test_num += 1
        cmd_opts = " -vvv" 
        comment = "Test case %d - Use%s " % (test_num, cmd_opts)
        res = self.run_test_case(1, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        # Test --changes-for and reverse
        for dir in _DIRECTIONS:
            test_num += 1
            cmd_opts = " --changes-for=%s " % dir 
            comment = "Test case %d - Use%s " % (test_num, cmd_opts)
            res = self.run_test_case(1, cmd_str + cmd_opts, comment)
            if not res:
                raise MUTLibError("%s: failed" % comment)
            # now with reverse
            test_num += 1
            cmd_opts = " --changes-for=%s --show-reverse" % dir 
            comment = "Test case %d - Use%s " % (test_num, cmd_opts)
            res = self.run_test_case(1, cmd_str + cmd_opts, comment)
            if not res:
                raise MUTLibError("%s: failed" % comment)

        # The following are necessary due to changes in character spaces
        # introduced with Python 2.7.X in the difflib.
        
        self.replace_result("+++ util_test.t1", "+++ util_test.t1\n")
        self.replace_result("+++ util_test.t2", "+++ util_test.t2\n")
        self.replace_result("--- util_test.t1", "--- util_test.t1\n")
        self.replace_result("--- util_test.t2", "--- util_test.t2\n")
        self.replace_result("*** util_test.t1", "*** util_test.t1\n")
        self.replace_result("*** util_test.t2", "*** util_test.t2\n")

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        return diff.test.cleanup(self)
