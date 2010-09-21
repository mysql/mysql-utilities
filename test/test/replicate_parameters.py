#!/usr/bin/env python

import os
import replicate

class test(replicate.test):
    """check parameters for the replicate utility
    This test executes the replicate utility parameters. It uses the
    replicate test as a parent for setup and teardown methods.
    """

    def check_prerequisites(self):
        return replicate.test.check_prerequisites(self)

    def setup(self):
        return replicate.test.setup(self)

    def run(self):
        self.res_fname = self.testdir + "result.txt"
                      
        comment = "Test case 1 - use the test feature"
        res = self.run_test_case(self.server2, self.server1, self.s2_serverid,
                                 comment, "--test-db=db_not_there_yet", True)
        if not res:
            return False

        res = self.server2.exec_query("STOP SLAVE")

        comment = "Test case 2 - show the help"
        res = self.run_test_case(self.server1, self.server2, self.s1_serverid,
                                 comment, "--help", True)
        if not res:
            return False

        return True

    def get_result(self):
        return self.compare(__name__, self.results)
    
    def record(self):
        return self.save_result_file(__name__, self.results)
    
    def cleanup(self):
        return replicate.test.cleanup(self)


