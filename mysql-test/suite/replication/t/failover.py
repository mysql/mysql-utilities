#!/usr/bin/env python

import os
import mutlib
import rpl_admin_gtid
import subprocess
import signal
import time
from mysql.utilities.exception import MUTLibError

_FAILOVER_LOG = "fail_log.txt"
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
        if self.servers.get_server(0).supports_gtid() != "ON":
            raise MUTLibError("Test requires server version 5.6.5 with "
                              "GTID_MODE=ON.")
        if os.name == "posix":
            self.failover_dir = "./fail_event"
        else:
            self.failover_dir = ".\\fail_event"
        if self.debug:
            print
        for log in ["1","2","3"]:
            try:
                os.unlink(log+_FAILOVERLOG)
            except:
                pass
        return rpl_admin_gtid.test.check_prerequisites(self)

    def setup(self):
        return rpl_admin_gtid.test.setup(self)
        
    def start_process(self, cmd):
        file = os.devnull
        f_out = open(file, 'w')
        if os.name == "posix":
             proc = subprocess.Popen(cmd, shell=True, stdout=f_out, stderr=f_out)
        else:
             proc = subprocess.Popen(cmd, stdout=f_out, stderr=f_out)
        return (proc, f_out)
     
    def kill(self, pid, force=False):
        if os.name == "posix":
            if force:
                res = os.kill(pid, subprocess.signal.SIGABRT)
            else:
                res = os.kill(pid, subprocess.signal.SIGTERM)
        else:
            f_out = open(os.devnull, 'w')
            proc = subprocess.Popen("taskkill /F /T /PID %i" % pid, shell=True,
                                    stdout=f_out, stdin=f_out)
            res = 0  # Ignore spurious Windows results
            f_out.close()
        return res

    def stop_process(self, proc, f_out, kill=True):
        res = -1
        if kill:
            retval = self.kill(proc.pid)
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

        # Cleanup in case previous test case failed
        if os.path.exists(self.failover_dir):
            try:
                os.system("rmdir %s" % self.failover_dir)
            except:
                pass
        
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
        self.kill(pid, True)
        
        # Need to wait until the process is really dead.
        if self.debug:
            print "# Waiting for master to stop."
        i = 0
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
            print "# Waiting for failover to complete."
        i = 0
        while not os.path.exists(self.failover_dir):
            time.sleep(1)
            i += 1
            if i > _TIMEOUT:
                if self.debug:
                    print "# Timeout console failover."
                raise MUTLibError("%s: failed - timeout waiting for "
                                  "exec_post_fail." % comment)
    
        # Need to poll here and wait for console to really end.
        ret_val = self.stop_process(proc, f_out, kill_console)
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
        
        # Cleanup after test case
        try:
            os.unlink(log_filename)
        except:
            pass
        
        if os.path.exists(self.failover_dir):
            try:
                os.system("rmdir %s" % self.failover_dir)
            except:
                pass

        # Remove server from the list.
        if self.debug:
            print "# Removing server name '%s'." % server.role
        self.servers.remove_server(server.role)

        return (comment, found_row)

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

        failover_cmd = "python ../scripts/mysqlfailover.py --interval=10 " + \
                       " --discover-slaves-login=root:root %s --failover-" + \
                       'mode=%s --log=%s --exec-post-fail="mkdir ' + \
                       self.failover_dir + '" '
        
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
                self.test_results.append(res)
            else:
                raise MUTLibError("%s: failed" % comment)
                
        return True

    def get_result(self):
        # Here we check the result from execution of each test object.
        # We check all and show a list of those that failed.
        msg = ""
        for i in range(0,len(self.test_results)):
            act_res = self.test_results[i]
            if not act_res[1]:
                msg += "\n%s\nEvent missing from log. " % act_res[0]
                return (False, msg)
            
        return (True, '')
    
    def record(self):
        return True # Not a comparative test
    
    def cleanup(self):
        for log in ["1","2","3"]:
            try:
                os.unlink(log+_FAILOVERLOG)
            except:
                pass
        return rpl_admin_gtid.test.cleanup(self)



