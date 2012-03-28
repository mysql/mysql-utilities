#!/usr/bin/env python

import os
import mutlib
import rpl_admin_gtid
import subprocess
import signal
import time
from mysql.utilities.exception import MUTLibError

_FAILOVER_LOG = "fail_log.txt"
_EXPECTED_RESULTS = [
    # (console_retval, log_entry present)
    (0, True),
    (0, True),
    (-1, True),
]

_TIMEOUT = 30

class test(rpl_admin_gtid.test):
    """test replication failover console
    This test exercises the mysqlfailover utility failover event and modes.
    It uses the rpl_admin_gtid test for setup and teardown methods.
    """

    # TODO: Perform analysis as to whether any of these methods need to be
    #       generalized and placed in the mutlib for all tests to access.
    
    def is_long(self):
        # This test is a long running test
        return True

    def check_prerequisites(self):
        # Need non-Windows platform
        if os.name == "nt":
            raise MUTLibError("Test requires a non-Windows platform.")
        if self.debug:
            print
        for log in ["1","2","3"]:
            try:
                os.unlink(log+_FAILOVERLOG)
            except:
                pass
        return rpl_admin_gtid.test.check_prerequisites(self)

    def setup(self):
        try:
            # Only valid for *nix systems.
            import termios, sys
            if self.debug:
                print "# Getting old terminal settings."
            self.old_terminal_settings = termios.tcgetattr(sys.stdin)
            if self.debug:
                print "# Got old terminal settings."
        except Exception, e:
            # Ok to fail for Windows
            self.old_terminal_settings = None
        return rpl_admin_gtid.test.setup(self)
        
    def start_process(self, cmd):
        file = os.devnull
        f_out = open(file, 'w')
        if os.name == "posix":
             proc = subprocess.Popen(cmd, shell=True, stdout=f_out, stderr=f_out)
        else:
             proc = subprocess.Popen(cmd, stdout=f_out, stderr=f_out)
        return (proc, f_out)
     
    def stop_process(self, proc, f_out, kill=True):
        res = -1
        if kill:
            if os.name == "posix":
                retval = os.kill(proc.pid, subprocess.signal.SIGTERM)
            else:
                retval = subprocess.Popen("taskkill /F /T /PID %i" % proc.pid,
                                          shell=True) 
            res = 0 if retval is None else -1
        else:
            if proc.poll() is None:
                res = proc.wait()
        f_out.close()
        return res
    
    def is_process_alive(self, pid, start, end):
        
        from mysql.utilities.common.server import get_local_servers
        
        mysqld_procs = get_local_servers(False, start, end)
        for proc in mysqld_procs:
            if int(pid) == int(proc[0]):
                return True
        return False
    
    def test_failover_console(self, test_case, interval):
        server = test_case[0]
        cmd = test_case[1]
        kill_console = test_case[2]
        log_filename = test_case[3]
        comment = test_case[4]
        key_phrase = test_case[5]

        # Since this test case expects the console to stop, we can launch it
        # via a subprocess and wait for it to finish.
        if self.debug:
            print comment
            print "# COMMAND:", cmd
            
        # Launch the console in stealth mode
        proc, f_out = self.start_process(cmd)

        # Wait for console to load
        if self.debug:
            print "# Waiting for console to start."
        i = 1
        time.sleep(1)
        while proc.poll() is not None:
            time.sleep(1)
            i += 1
            if i > _TIMEOUT:
                if self.debug:
                    print "# Timeout console to start."
                raise MUTLibError("%s: failed - timeout waiting for "
                                  "console to start." % comment)  
                
        # Now, kill the master - wha-ha-ha!
        res = server.show_server_variable('pid_file')
        pid_file = open(res[0][1])
        pid = int(pid_file.readline().strip('\n'))
        if self.debug:
            print "# Terminating server", server.port, "via pid =", pid
        pid_file.close()

        # Stop the server 
        server.disconnect()
        if os.name == "posix":
            os.kill(pid, subprocess.signal.SIGABRT)
        else:
            subprocess.Popen("taskkill /F /T /PID %i" % pid, shell=True) 
        
        # Need to wait until the process is really dead.
        if self.debug:
            print "# Waiting for master to stop."
        i = 0
        # TODO: may need to add datadir for Windows machines...
        while self.is_process_alive(pid, int(server.port)-1,
                                    int(server.port)+1):
            time.sleep(1)
            i += 1
            if i > _TIMEOUT:
                if self.debug:
                    print "# Timeout master to fail."
                raise MUTLibError("%s: failed - timeout waiting for "
                                  "master to end." % comment)
         
        # Now wait for interval to occur.
        if self.debug:
            print "# Waiting for interval to end."
        time.sleep(interval)

        if kill_console:            
            # Need to poll here and wait for exec_after to fire.
            if self.debug:
                print "# Waiting for failover to complete."
            i = 0
            while os.path.exists("./before_ok"):
                time.sleep(1)
                i += 1
                if i > _TIMEOUT:
                    if self.debug:
                        print "# Timeout console failover."
                    raise MUTLibError("%s: failed - timeout waiting for "
                                      "exec_after." % comment)
    
        # Now wait for failover to complete and logs to be written.
        if self.debug:
            print "# Waiting for failover to complete."
        time.sleep(interval)

        # Need to poll here and wait for console to really end.
        ret_val = self.stop_process(proc, f_out, kill_console)
        if not kill_console:
            # Wait for console to end
            if self.debug:
                print "# Waiting for console to end."
            i = 0
            while proc.poll() is None:
                time.sleep(1)
                i += 1
                if i > _TIMEOUT:
                    if self.debug:
                        print "# Timeout console to end."
                    raise MUTLibError("%s: failed - timeout waiting for "
                                      "console to end." % comment)
        # We elected to kill the console so let's wait until it has written
        # the failover complete string.
        else:
            if self.debug:
                print "# Waiting for log to be updated."
            i = 0
            done = False
            while not done:
                log_file = open(log_filename)
                rows = log_file.readlines()
                for row in rows:
                    if 'Failover console stopped' in row:
                        if self.debug:
                            print "# Found:", row[:len(row)-1]
                        done = True
                log_file.close()
                if not done:
                    time.sleep(1)
                    i += 1
                    if i > _TIMEOUT:
                        if self.debug:
                            print "# Timeout failover to complete."
                        raise MUTLibError("%s: failed - timeout waiting for "
                                          "failover to complete." % comment)
                    
        if self.debug:
            print "# Return code from console termination =", ret_val
        
        # Check result code from stop_process then read the log to find the
        # key phrase.
        found_row = False
        log_file = open(log_filename)
        rows = log_file.readlines()
        if self.debug:
            print "# Looking in log for:", key_phrase
        for row in rows:
            if key_phrase in row:
                found_row = True
                if self.debug:
                    print "# Found in row = '%s'." % row[:len(row)-1]
        log_file.close()
        
        if not found_row:
            print "# ERROR: Cannot find entry in log:"
            for row in rows:
                print row,
        
        try:
            os.unlink(log_filename)
        except:
            pass
        
        # Remove server from the list.
        if self.debug:
            print "# Removing server name '%s'." % server.role
        self.servers.remove_server(server.role)

        if self.debug:
            print "# Test case results = (%s,%s)." % (ret_val, found_row)
        return (ret_val, found_row)

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
        
        self.test_results = []
        self.test_cases = []

        failover_cmd = "python ../scripts/mysqlfailover.py --interval=15 " + \
                       " --discover-slaves-login=root:root %s --failover-" + \
                       "mode=%s --log=%s --exec-before='mkdir ./before_ok'" + \
                       " --exec-after='rmdir ./before_ok' "
        
        conn_str = " ".join([master_str, slaves_str])
        str = failover_cmd % (conn_str, 'auto', "1"+_FAILOVER_LOG)
        str += " --candidates=%s " % slave1_conn
        self.test_cases.append((self.server1, str, True, "1"+_FAILOVER_LOG,
                    "Test case 1 - Simple failover with --failover=auto.",
                    "Failover complete"))
        str = failover_cmd % ("--master=%s" % slave1_conn, 'elect',
                              "2"+_FAILOVER_LOG)
        str += " --candidates=%s " % slave2_conn
        self.test_cases.append((self.server2, str, True, "2"+_FAILOVER_LOG,
                    "Test case 2 - Simple failover with --failover=elect.",
                    "Failover complete"))
        str = failover_cmd % ("--master=%s" % slave2_conn, 'fail',
                              "3"+_FAILOVER_LOG)
        self.test_cases.append((self.server3, str, False, "3"+_FAILOVER_LOG,
                    "Test case 3 - Simple failover with --failover=fail.",
                    "Master has failed and automatic"))

        for test_case in self.test_cases:
            res = self.test_failover_console(test_case, 20)
            if res is not None:
                self.test_results.append((res[0], res[1], test_case[4]))
            else:
                raise MUTLibError("%s: failed" % comment)
                
        return True

    def get_result(self):
        # Here we check the result from execution of each test object.
        # We check all and show a list of those that failed.
        msg = ""
        for i in range(0,len(self.test_results)):
            exp_res = _EXPECTED_RESULTS[i]
            act_res = self.test_results[i]
            if int(exp_res[0]) != int(act_res[0]) or \
               exp_res[1] != act_res[1]:
                msg += "\n%s\nExpected results = " % act_res[2] + \
                        "%s, actual results = %s.\n" % (exp_res, act_res[0:2])
                return (False, msg)
            
        return (True, '')
    
    def record(self):
        return True # Not a comparative test
    
    def cleanup(self):
        if self.old_terminal_settings is not None:
            import termios, sys
            if self.debug:
                print "# Resetting old terminal settings."
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN,
                              self.old_terminal_settings)
            if self.debug:
                print "# Set old terminal settings."
            
        for log in ["1","2","3"]:
            try:
                os.unlink(log+_FAILOVERLOG)
            except:
                pass
        return rpl_admin_gtid.test.cleanup(self)



