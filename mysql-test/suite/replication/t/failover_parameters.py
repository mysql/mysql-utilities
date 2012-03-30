#!/usr/bin/env python

import os
import mutlib
from mysql.utilities.exception import MUTLibError

class test(mutlib.System_test):
    """test replication failover utility
    This test runs the mysqlfailover utility parameters on a known topology.
    """

    def check_prerequisites(self):
        return self.check_num_servers(1)

    def setup(self):
        return True
    
    def run(self):
        self.res_fname = "result.txt"
        
        cmd_str = "mysqlfailover.py "
        
        comment = "Test case 1 - show help"
        cmd_opts = " --help" 
        res = mutlib.System_test.run_test_case(self, 0, cmd_str+cmd_opts,
                                               comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        return True

    def get_result(self):
        return self.compare(__name__, self.results)
    
    def record(self):
        return self.save_result_file(__name__, self.results)
    
    def cleanup(self):
        if self.res_fname:
            try:
                os.unlink(self.res_fname)
            except:
                pass
        return True

