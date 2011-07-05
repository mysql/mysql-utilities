#!/usr/bin/env python

import os
import mutlib

class test(mutlib.System_test):
    """Experimental test #1
    This is a demonstration of running a simple execution and supplying a
    test result file for comparison. This example compares return code only
    supplying a custom result to be displayed to the user on failure.
    """

    def check_prerequisites(self):
        return self.check_num_servers(1)

    def setup(self):
        return True
    
    def run(self):
        #
        # Note: comment out the following line and uncomment the next line
        #       to see an unsuccessful test run
        #
        cmd = "mysqlserverclone.py --help"
        #cmd = "NOTREALLYTHEREATALL!"
        self.result = self.exec_util(cmd, "./result.txt")
        return True
  
    def get_result(self):
        str = None
        if self.result != 0:
            str = "Unexpected return code: %d\n" % (self.result)
        return (self.result == 0, str)
        
    def record(self):
        # Not a comparative test, returning True
        return True
    
    def cleanup(self):
        os.unlink("./result.txt")
        return True

