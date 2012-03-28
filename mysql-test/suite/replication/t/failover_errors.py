#!/usr/bin/env python

import os
import mutlib
import mutlib
from mysql.utilities.exception import MUTLibError

class test(mutlib.System_test):
    """test replication failover utility
    This test exercises the mysqlfailover utility known error conditions.
    """

    def check_prerequisites(self):
        return True

    def setup(self):
        return True
    
    def run(self):
        self.res_fname = "result.txt"
        
        comment = "Test case 1 - No master"
        cmd_str = "mysqlfailover.py " 
        cmd_opts = " --discover-slaves-login=root:root"
        res = mutlib.System_test.run_test_case(self, 2, cmd_str+cmd_opts,
                                               comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        comment = "Test case 2 - No slaves or discover-slaves-login"
        cmd_str = "mysqlfailover.py " 
        cmd_opts = " --master=root:root@localhost"
        res = mutlib.System_test.run_test_case(self, 2, cmd_str+cmd_opts,
                                               comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        comment = "Test case 3 - Low value for interval."
        cmd_str = "mysqlfailover.py --interval=1" 
        cmd_opts = " --master=root:root@localhost"
        res = mutlib.System_test.run_test_case(self, 2, cmd_str+cmd_opts,
                                               comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        comment = "Test case 4 - elect mode but no candidates"
        cmd_str = "mysqlfailover.py " 
        cmd_opts = " --master=root:root@localhost --failover-mode=elect "
        cmd_opts += "--slaves=root:root@localhost "
        res = mutlib.System_test.run_test_case(self, 2, cmd_str+cmd_opts,
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

