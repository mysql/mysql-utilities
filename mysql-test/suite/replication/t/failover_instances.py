#!/usr/bin/env python

import os
import mutlib
import failover
import rpl_admin_gtid
import subprocess
import signal
import time
from mysql.utilities.exception import MUTLibError

_FAILOVER_LOG = "fail_log.txt"
_TIMEOUT = 30

class test(failover.test):
    """test replication failover console
    This test exercises the mysqlfailover utility for multiple instances.
    It uses the failover and rpl_adming_gtid tests for setup and
    teardown methods.
    """

    def check_prerequisites(self):
        if self.servers.get_server(0).supports_gtid() != "ON":
            raise MUTLibError("Test requires server version 5.6.5 with "
                              "GTID_MODE=ON.")
        if self.debug:
            print
        for log in ["a","b"]:
            try:
                os.unlink(log+_FAILOVERLOG)
            except:
                pass
        return rpl_admin_gtid.test.check_prerequisites(self)

    def setup(self):
        return rpl_admin_gtid.test.setup(self)
        
    def run(self):
        self.res_fname = "result.txt"
        
        master_conn = self.build_connection_string(self.server1).strip(' ')
        slave1_conn = self.build_connection_string(self.server2).strip(' ')
        slave2_conn = self.build_connection_string(self.server3).strip(' ')
        slave3_conn = self.build_connection_string(self.server4).strip(' ')
        
        master_str = "--master=" + master_conn
        slaves_str = "--slaves=" + \
                     ",".join([slave1_conn, slave2_conn, slave3_conn])
        candidates_str = "--candidates=" + \
                         ",".join([slave1_conn, slave2_conn, slave3_conn])
        
        failover_cmd = "python ../scripts/mysqlfailover.py --interval=15 " + \
                       " --discover-slaves-login=root:root --failover-" + \
                       "mode=auto --log=%s " + master_str
        failover_cmd1 = failover_cmd % ("a" + _FAILOVER_LOG)
        failover_cmd2 = failover_cmd % ("b" + _FAILOVER_LOG)
        
        # We launch one console, wait for interval, then start another,
        # wait for interval, then kill both, and finally check log of each
        # for whether each logged the correct messages for multiple instance
        # check.
        
        interval = 15
        comment = "Test case 1 : test multiple instances of failover console."
        if self.debug:
            print comment
            print "# First instance:", failover_cmd1
            print "# Second instance:", failover_cmd2
            
        # Launch the consoles in stealth mode
        proc1, f_out1 = failover.test.start_process(self, failover_cmd1)

        # Wait for console to load
        if self.debug:
            print "# Waiting for consoles to start."
        i = 1
        time.sleep(1)
        while proc1.poll() is not None:
            if self.debug:
                print "# Polling first console:", proc1.pid, proc1.poll()
            time.sleep(1)
            i += 1
            if i > _TIMEOUT:
                if self.debug:
                    print "# Timeout first console to start."
                raise MUTLibError("%s: failed - timeout waiting for "
                                  "first console to start." % comment)  

        # Now wait for interval to occur.
        if self.debug:
            print "# Waiting for interval to end."
        time.sleep(interval)

        proc2, f_out2 = failover.test.start_process(self, failover_cmd2)
        i = 1
        time.sleep(1)
        while proc2.poll() is not None:
            if self.debug:
                print "# Polling second console:", proc2.pid, proc2.poll()
            time.sleep(1)
            i += 1
            if i > _TIMEOUT:
                if self.debug:
                    print "# Timeout second console to start."
                raise MUTLibError("%s: failed - timeout waiting for "
                                  "second console to start." % comment)  
                
        # Need to poll here and wait for console to really end.
        ret_val = failover.test.stop_process(self, proc1, f_out1, True)
        # Wait for console to end
        if self.debug:
            print "# Waiting for first console to end."
        i = 0
        while proc1.poll() is None:
            time.sleep(1)
            i += 1
            if i > _TIMEOUT:
                if self.debug:
                    print "# Timeout first console to end."
                raise MUTLibError("%s: failed - timeout waiting for "
                                  "first console to end." % comment)

        ret_val = failover.test.stop_process(self, proc2, f_out2, True)
        # Wait for console to end
        if self.debug:
            print "# Waiting for second console to end."
        i = 0
        while proc2.poll() is None:
            time.sleep(1)
            i += 1
            if i > _TIMEOUT:
                if self.debug:
                    print "# Timeout second console to end."
                raise MUTLibError("%s: failed - timeout waiting for "
                                  "second console to end." % comment)

        # Check to see if second console changed modes.
        found_row = False
        log_file = open("b"+_FAILOVER_LOG)
        rows = log_file.readlines()
        if self.debug:
            print "# Looking for mode change in log."
        for row in rows:
            if "Multiple instances of failover console found" in row:
                found_row = True
                if self.debug:
                    print "# Found in row = '%s'." % row[:len(row)-1]
        log_file.close()
        self.results.append((comment, found_row))
        
        if not found_row:
            print "# ERROR: Cannot find entry in log:"
            for row in rows:
                print row,
        
        try:
            os.unlink(log_filename)
        except:
            pass
        
        return True

    def get_result(self):
        # Here we check the result from execution of each test object.
        # We check all and show a list of those that failed.
        msg = ""
        for result in self.results:
            if not result[1]:
                msg += "\n%s\nTest case failed." % result[0]
                return (False, msg)
        return (True, '')
    
    def record(self):
        return True # Not a comparative test
    
    def cleanup(self):
        for log in ["a","b"]:
            try:
                os.unlink(log+_FAILOVERLOG)
            except:
                pass
        return rpl_admin_gtid.test.cleanup(self)



