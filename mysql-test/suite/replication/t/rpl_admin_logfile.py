#!/usr/bin/env python

import os
import stat
import mutlib
import rpl_admin
from mysql.utilities.exception import MUTLibError

_LOGNAME = "temp_log.txt"

class test(rpl_admin.test):
    """test replication administration commands
    This tests checks handling of accessibility of the log file (BUG#14208415)
    """

    def check_prerequisites(self):
        if self.servers.get_server(0).check_version_compat(5, 6, 5):
            raise MUTLibError("Test requires server version prior to 5.6.5")
        return self.check_num_servers(1)

    def setup(self):
        self.res_fname = "result.txt"
        return rpl_admin.test.setup(self)
        
    def run(self):
        master_conn = self.build_connection_string(self.server1).strip(' ')
        slave_conn = self.build_connection_string(self.server2).strip(' ')
        
        # For this test, it's OK when master and slave are the same
        master_str = "--master=" + master_conn
        slave_str = "--slave=" + slave_conn
        
        # command used in test cases: replace 3 element with location of
        # log file.
        cmd = [
            "mysqlrpladmin.py",
            master_str,
            slave_str,
            "--log=" + _LOGNAME,
            "health",
            ]
        
        # Test Case 1
        comment = "Test Case 1 - Log file is newly created"
        res = mutlib.System_test.run_test_case(
            self, 0, ' '.join(cmd), comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        
        # Test Case 2
        comment = "Test Case 2 - Log file is reopened"
        res = mutlib.System_test.run_test_case(
            self, 0, ' '.join(cmd), comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        
        # Test Case 3
        comment = "Test Case 3 - Log file can not be written to"
        os.chmod(_LOGNAME, stat.S_IREAD) # Make log read-only
        res = mutlib.System_test.run_test_case(
            self, 2, ' '.join(cmd), comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
            
        rpl_admin.test.do_masks(self)
        
        return True

    def get_result(self):
        return self.compare(__name__, self.results)
    
    def record(self):
        return self.save_result_file(__name__, self.results)
    
    def cleanup(self):
        try:
            os.chmod(_LOGNAME, stat.S_IWRITE)
            os.unlink(_LOGNAME)
        except:
            if self.debug:
                print "# failed removing temporary log file " + _LOGNAME
        return rpl_admin.test.cleanup(self)

