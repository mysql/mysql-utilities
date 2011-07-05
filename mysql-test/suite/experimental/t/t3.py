#!/usr/bin/env python

import mutlib

class test(mutlib.System_test):
    """Experimental test #3
    This example tests the return codes for the methods. Uncomment out the
    False returns and comment out the True returns to see failed execution.
    """

    def check_prerequisites(self):
        return True
        #return False

    def setup(self):
        return True
        #return False
    
    def run(self):
        return True
        #return False
  
    def get_result(self):
        return (True, None)
        #return (False, "Test message\nAnother test message\n")
    
    def record(self):
        # Not a comparative test, returning True
        return True
        #return False
    
    def cleanup(self):
        return True
        #return False


