#
# Copyright (c) 2010, 2013, Oracle and/or its affiliates. All rights reserved.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301 USA
#
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
_LOG_PREFIX = ["a","b","c","d"]

class test(failover.test):
    """test replication failover console
    This test exercises the mysqlfailover utility for multiple instances.
    It uses the failover and rpl_adming_gtid tests for setup and
    teardown methods.
    """

    def check_prerequisites(self):
        if self.servers.get_server(0).supports_gtid() != "ON" or \
           not self.servers.get_server(0).check_version_compat(5,6,9):
            raise MUTLibError("Test requires server version 5.6.9 with "
                              "GTID_MODE=ON.")
        if self.debug:
            print
        for log in _LOG_PREFIX:
            try:
                os.unlink(log+_FAILOVER_LOG)
            except:
                pass
        return rpl_admin_gtid.test.check_prerequisites(self)

    def setup(self):
        return rpl_admin_gtid.test.setup(self)
        
    def _poll_console(self, start, name, proc, comment):
        msg = "Timeout waiting for console %s to " % name
        msg += "start." if start else "end."
        if self.debug:
            print "# Waiting for console %s to" % name,
            print "start." if start else "end."
        elapsed = 0
        delay = 1
        done = False
        while not done:
            if start:
                done = proc.poll() is None
            else:
                done = proc.poll() is not None
            time.sleep(delay)
            elapsed += delay
            if elapsed >= _TIMEOUT:
                if self.debug:
                    print "#", msg
                raise MUTLibError("%s: " % comment + msg)
                
    def _check_result(self, prefix, target):
        found_row = False
        log_file = open(prefix + _FAILOVER_LOG)
        if self.debug:
            print "# Looking for mode change in log."
        for row in log_file.readlines():
            if self.debug:
                print row,
            if target in row:
                found_row = True
                break
                if self.debug:
                    print "# Found in row = '%s'." % row,
        log_file.close()
        return found_row

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
                       "mode=%s --log=%s %s "
        failover_cmd1 = failover_cmd % ("auto", "a" + _FAILOVER_LOG, master_str)
        failover_cmd2 = failover_cmd % ("auto", "b" + _FAILOVER_LOG, master_str)
        failover_cmd3 = failover_cmd % ("elect", "c" + _FAILOVER_LOG, master_str)
        failover_cmd3 += " --candidate=%s" % slave1_conn
        failover_cmd4 = failover_cmd % ("auto", "d" + _FAILOVER_LOG,
                                        "--master="+slave2_conn)
        
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
            
        proc1, f_out1 = failover.test.start_process(self, failover_cmd1)
        self._poll_console(True, "first", proc1, comment)

        # Now wait for interval to occur.
        if self.debug:
            print "# Waiting for interval to end."
        time.sleep(interval)

        proc2, f_out2 = failover.test.start_process(self, failover_cmd2)
        self._poll_console(True, "second", proc2, comment)

        ret_val = failover.test.stop_process(self, proc1, f_out1, True)
        self._poll_console(False, "first", proc1, comment)

        ret_val = failover.test.stop_process(self, proc2, f_out2, True)
        self._poll_console(False, "second", proc1, comment)

        # Check to see if second console changed modes.
        found_row = self._check_result("b", "Multiple instances of failover")
        self.results.append((comment, found_row))
                    
        comment = "Test case 2 : test failed instance restart"
        if self.debug:
            print comment
            print "# Third instance:", failover_cmd3
            print "# Fourth instance:", failover_cmd4
            
        # Launch the console in stealth mode
        proc3, f_out3 = failover.test.start_process(self, failover_cmd3)
        self._poll_console(True, "third", proc3, comment)

        # Now, kill the master - wha-ha-ha!
        res = self.server1.show_server_variable('pid_file')
        pid_file = open(res[0][1])
        pid = int(pid_file.readline().strip('\n'))
        if self.debug:
            print "# Terminating server", self.server1.port, "via pid =", pid
        pid_file.close()

        # Stop the server 
        self.server1.disconnect()
        failover.test.kill(self, pid, True)

        self.servers.remove_server(self.server1.role)
        
        # Now wait for interval to occur.
        if self.debug:
            print "# Waiting for interval to end."
        time.sleep(interval)

        ret_val = failover.test.stop_process(self, proc3, f_out3, True)
        self._poll_console(False, "third", proc3, comment)
                
        # Restart the console - should not demote the failover mode.
        proc4, f_out4 = failover.test.start_process(self, failover_cmd4)
        self._poll_console(True, "fourth", proc4, comment)
        
        ret_val = failover.test.stop_process(self, proc4, f_out4, True)
        self._poll_console(False, "fourth", proc4, comment)

        found_row = self._check_result("d", "Multiple instances of failover")
        self.results.append((comment, found_row == False))

        rpl_admin_gtid.test.reset_topology(self)

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
        for log in _LOG_PREFIX:
            try:
                os.unlink(log+_FAILOVER_LOG)
            except:
                pass
        return rpl_admin_gtid.test.cleanup(self)


