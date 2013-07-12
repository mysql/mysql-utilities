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
import subprocess
import tempfile
import time

import rpl_admin_gtid

from mysql.utilities.common.server import get_local_servers
from mysql.utilities.common.tools import delete_directory
from mysql.utilities.exception import MUTLibError, UtilError

_FAILOVER_LOG = "{0}fail_log.txt"
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
        if self.servers.get_server(0).supports_gtid() != "ON" or \
           not self.servers.get_server(0).check_version_compat(5, 6, 9):
            raise MUTLibError("Test requires server version 5.6.9 with "
                              "GTID_MODE=ON.")
        return rpl_admin_gtid.test.check_prerequisites(self)

    def setup(self):
        self.temp_files = []
        # Post failover script executed to detect failover events (by creating
        # a specific directory).
        # Note: .bat extension is used for the script to be executed on all
        # operating systems (including Windows).
        self.fail_event_script = os.path.normpath("./std_data/fail_event.bat")
        # Directory created by the post failover script.
        self.failover_dir = os.path.normpath("./fail_event")
        self.log_range = range(1, 5)

        # Remove log files (leftover from previous test).
        for log in self.log_range:
            try:
                os.unlink(_FAILOVER_LOG.format(log))
            except OSError:
                pass
        return rpl_admin_gtid.test.setup(self)

    def start_process(self, cmd):
        if self.debug:
            f_out = tempfile.TemporaryFile()
            self.temp_files.append(f_out)
        else:
            file = os.devnull
            f_out = open(file, 'w')
        if os.name == "posix":
             proc = subprocess.Popen(cmd, shell=True, stdout=f_out,
                                     stderr=f_out)
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
        if not self.debug:
            f_out.close()
        return res

    def is_process_alive(self, pid, start, end):
        mysqld_procs = get_local_servers(False, start, end)
        for proc in mysqld_procs:
            if int(pid) == int(proc[0]):
                return True
        return False

    def test_failover_console(self, test_case):
        server = test_case[0]
        cmd = test_case[1]
        kill_console = test_case[2]
        log_filename = test_case[3]
        comment = test_case[4]
        key_phrase = test_case[5]

        # Since this test case expects the console to stop, we can launch it
        # via a subprocess and wait for it to finish.
        if self.debug:
            print(comment)
            print("# COMMAND: {0}".format(cmd))

        # Cleanup in case previous test case failed
        if os.path.exists(self.failover_dir):
            try:
                os.system("rmdir {0}".format(self.failover_dir))
            except OSError:
                pass

        # Launch the console in stealth mode
        proc, f_out = self.start_process(cmd)

        # Wait for console to load
        if self.debug:
            print("# Waiting for console to start.")
        i = 1
        time.sleep(1)
        while proc.poll() is not None:
            time.sleep(1)
            i += 1
            if i > _TIMEOUT:
                if self.debug:
                    print("# Timeout console to start.")
                raise MUTLibError("{0}: failed - timeout waiting for "
                                  "console to start.".format(comment))

        # Wait for the failover console to register on master and start
        # its monitoring process

        phrase = "Failover console started"
        if self.debug:
            print("Waiting for failover console to register master and start "
                  "its monitoring process")
        i = 0
        with open(log_filename, 'r') as file_:
            while i < _TIMEOUT:
                line = file_.readline()
                if not line:
                    i += 1
                    time.sleep(1)
                elif phrase in line:
                    break
            else:
                if self.debug:
                    print("# Timeout waiting for failover console to register "
                          "master and start its monitoring process")
                raise MUTLibError("{0}: failed - timeout waiting for console "
                                  "to register master and start its "
                                  "monitoring process".format(comment))

        # Now, kill the master - wha-ha-ha!
        res = server.show_server_variable('pid_file')
        pid_file = open(res[0][1])
        pid = int(pid_file.readline().strip('\n'))
        if self.debug:
            print("# Terminating server {0} via pid = {1}".format(server.port,
                                                                  pid))
        pid_file.close()

        # Get server datadir to clean directory after kill.
        res = server.show_server_variable("datadir")
        datadir = res[0][1]

        # Stop the server 
        server.disconnect()
        self.kill(pid, True)

        # Need to wait until the process is really dead.
        if self.debug:
            print("# Waiting for master to stop.")
        i = 0
        while self.is_process_alive(pid, int(server.port)-1,
                                    int(server.port)+1):
            time.sleep(1)
            i += 1
            if i > _TIMEOUT:
                if self.debug:
                    print("# Timeout master to fail.")
                raise MUTLibError("{0}: failed - timeout waiting for "
                                  "master to end.".format(comment))

        # Remove server from the list (and clean data directory).
        if self.debug:
            print("# Removing server name '{0}'.".format(server.role))
        delete_directory(datadir)
        self.servers.remove_server(server.role)

        # Now wait for interval to occur.
        if self.debug:
            print("# Waiting for failover to complete.")
        i = 0
        while not os.path.exists(self.failover_dir):
            time.sleep(1)
            i += 1
            if i > _TIMEOUT:
                if self.debug:
                    print("# Timeout console failover.")
                raise MUTLibError("{0}: failed - timeout waiting for "
                                  "exec_post_fail.".format(comment))

        # Need to poll here and wait for console to really end.
        ret_val = self.stop_process(proc, f_out, kill_console)
        # Wait for console to end
        if self.debug:
            print("# Waiting for console to end.")
        i = 0
        while proc.poll() is None:
            time.sleep(1)
            i += 1
            if i > _TIMEOUT:
                if self.debug:
                    print("# Timeout console to end.")
                raise MUTLibError("{0}: failed - timeout waiting for "
                                  "console to end.".format(comment))

        if self.debug:
            print("# Return code from console termination = "
                  "{0}".format(ret_val))

        # Check result code from stop_process then read the log to find the
        # key phrase.
        found_row = False
        log_file = open(log_filename)
        rows = log_file.readlines()
        if self.debug:
            print("# Looking in log for: {0}".format(key_phrase))
        for row in rows:
            if key_phrase in row:
                found_row = True
                if self.debug:
                    print("# Found in row = '{0}'.".format(row[:len(row)-1]))
        log_file.close()

        if not found_row:
            print("# ERROR: Cannot find entry in log:")
            for row in rows:
                print row,

        # Cleanup after test case
        try:
            os.unlink(log_filename)
        except OSError:
            pass

        if os.path.exists(self.failover_dir):
            try:
                os.system("rmdir {0}".format(self.failover_dir))
            except OSError:
                pass

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

        self.test_results = []
        self.test_cases = []

        failover_cmd = "python ../scripts/mysqlfailover.py --interval=10 " + \
                       " --discover-slaves-login=root:root %s --failover-" + \
                       'mode=%s --log=%s --exec-post-fail="' + \
                       self.fail_event_script + '" --timeout=5 '
        
        conn_str = " ".join([master_str, slaves_str])
        str = failover_cmd % (conn_str, 'auto', _FAILOVER_LOG.format('1'))
        str += " --candidates=%s " % slave1_conn
        self.test_cases.append(
            (self.server1, str, True, _FAILOVER_LOG.format('1'),
             "Test case 1 - Simple failover with --failover=auto.",
             "Failover complete")
        )
        str = failover_cmd % ("--master=%s" % slave1_conn, 'elect',
                              _FAILOVER_LOG.format('2'))
        str += " --candidates=%s " % slave2_conn
        self.test_cases.append(
            (self.server2, str, True, _FAILOVER_LOG.format('2'),
             "Test case 2 - Simple failover with --failover=elect.",
             "Failover complete")
        )
        str = failover_cmd % ("--master=%s" % slave2_conn, 'fail',
                              _FAILOVER_LOG.format('3'))
        self.test_cases.append(
            (self.server3, str, False, _FAILOVER_LOG.format('3'),
             "Test case 3 - Simple failover with --failover=fail.",
             "Master has failed and automatic")
        )

        for test_case in self.test_cases:
            res = self.test_failover_console(test_case)
            if res is not None:
                self.test_results.append(res)
            else:
                raise MUTLibError("{0}: failed".format(test_case[4]))

        # Now we must test the --force option. But first, ensure the master
        # does not have the table.
        try:
            self.server4.exec_query("DROP TABLE IF EXISTS "
                                    "mysql.failover_console")
        except UtilError:
            pass

        comment = "Test case 4 - test --force on first run"
        # Note: test should pass without any errors. If the start or stop
        #       timeout, the test case has failed and the log will contain
        #       the error.
        if self.debug:
            print comment

        failover_cmd = "python ../scripts/mysqlfailover.py --interval=10 " + \
                       " --discover-slaves-login=root:root --force " + \
                       "--master=%s --log=%s" % (slave3_conn,
                                                 _FAILOVER_LOG.format('4'))

        if self.debug:
            print failover_cmd

        # Launch the console in stealth mode
        proc, f_out = self.start_process(failover_cmd)

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

        # Need to poll here and wait for console to really end.
        ret_val = self.stop_process(proc, f_out, True)
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

        return True

    def get_result(self):
        # Here we check the result from execution of each test object.
        # We check all and show a list of those that failed.
        msg = ""
        for i in range(0, len(self.test_results)):
            act_res = self.test_results[i]
            if not act_res[1]:
                msg = "{0}\n{1}\nEvent missing from log. ".format(msg,
                                                                  act_res[0])
                return (False, msg)

        return (True, '')

    def record(self):
        return True  # Not a comparative test

    def cleanup(self):
        if self.debug:
            for file in self.temp_files:
                file.seek(0)
                for row in file.readlines():
                    if len(row.strip()):
                        print row,

        # Kill all remaining servers (to avoid problems for other tests).
        self.kill_server('rep_slave3_gtid')
        self.kill_server('rep_slave4_gtid')

        # Remove all log files
        for log in self.log_range:
            try:
                os.unlink(_FAILOVER_LOG.format(log))
            except OSError:
                pass

        return rpl_admin_gtid.test.cleanup(self)



