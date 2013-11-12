#
# Copyright (c) 2013 Oracle and/or its affiliates. All rights reserved.
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
import re
import time

import failover

from mysql.utilities.common.tools import delete_directory
from mysql.utilities.exception import MUTLibError, UtilError

_FAILOVER_LOG = "{0}fail_log.txt"
_FAILOVER_PID = "{0}fail_pid.txt"
_FAILOVER_COMPLETE = "Failover complete"
_TIMEOUT = 30


class test(failover.test):
    """Test replication failover daemon
    This test exercises the mysqlfailover utility failover event and modes.
    It uses the rpl_admin_gtid test for setup and teardown methods.
    """
    log_range = range(1, 6)

    def check_prerequisites(self):
        if os.name != "posix":
            raise MUTLibError("Test requires a POSIX system.")
        return super(test, self).check_prerequisites()

    def test_failover_daemon_nodetach(self, test_case):
        server = test_case[0]
        cmd = test_case[1]
        kill_daemon = test_case[2]
        logfile = test_case[3]
        comment = test_case[4]
        key_phrase = test_case[5]
        unregister = test_case[6]

        if unregister:
            # Unregister any failover instance from server
            try:
                server.exec_query("DROP TABLE IF EXISTS "
                                  "mysql.failover_console")
            except UtilError:
                pass

        # Since this test case expects the daemon to stop, we can launch it
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

        # Wait for the failover daemon to register on master and start
        # its monitoring process
        phrase = "Failover daemon started"
        if self.debug:
            print("Waiting for failover daemon to register master and start "
                  "its monitoring process")
        i = 0
        with open(logfile, "r") as f:
            while i < _TIMEOUT:
                line = f.readline()
                if not line:
                    i += 1
                    time.sleep(1)
                elif phrase in line:
                    break
            else:
                if self.debug:
                    print("# Timeout waiting for failover daemon to register "
                          "master and start its monitoring process")
                raise MUTLibError("{0}: failed - timeout waiting for daemon "
                                  "to register master and start its "
                                  "monitoring process".format(comment))

        # Now, kill the master
        res = server.show_server_variable("pid_file")
        pid_file = open(res[0][1])
        pid = int(pid_file.readline().strip("\n"))
        if self.debug:
            print("# Terminating server {0} via pid = {1}".format(server.port,
                                                                  pid))
        pid_file.close()

        # Get server datadir to clean directory after kill.
        res = server.show_server_variable("datadir")
        datadir = res[0][1]

        # Stop the server
        server.disconnect()
        self.kill(pid)

        # Need to wait until the process is really dead.
        if self.debug:
            print("# Waiting for master to stop.")
        i = 0
        while self.is_process_alive(pid, int(server.port) - 1,
                                    int(server.port) + 1):
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
        while not os.path.isdir(self.failover_dir):
            time.sleep(5)
            i += 1
            if i > _TIMEOUT:
                if self.debug:
                    print("# Timeout daemon failover.")
                raise MUTLibError("{0}: failed - timeout waiting for "
                                  "exec_post_fail.".format(comment))

        # Need to poll here and wait for daemon to really end.
        ret_val = self.stop_process(proc, f_out, kill_daemon)
        # Wait for daemon to end
        if self.debug:
            print("# Waiting for daemon to end.")
        i = 0
        while proc.poll() is None:
            time.sleep(1)
            i += 1
            if i > _TIMEOUT:
                if self.debug:
                    print("# Timeout daemon to end.")
                raise MUTLibError("{0}: failed - timeout waiting for "
                                  "daemon to end.".format(comment))

        if self.debug:
            print("# Return code from daemon termination = "
                  "{0}".format(ret_val))

        # Check result code from stop_process then read the log to find the
        # key phrase.
        found_row = True
        if key_phrase is not None:
            found_row = False
            with open(logfile, "r") as f:
                rows = f.readlines()
                if self.debug:
                    print("# Looking in log for: {0}".format(key_phrase))
                for row in rows:
                    if key_phrase in row:
                        found_row = True
                        if self.debug:
                            print("# Found in row = '{0}'."
                                  "".format(row[:len(row) - 1]))
            if not found_row:
                print("# ERROR: Cannot find entry in log:")
                for row in rows:
                    print(row)

        # Cleanup after test case
        try:
            os.unlink(logfile)
        except OSError:
            pass

        if os.path.exists(self.failover_dir):
            try:
                os.system("rmdir {0}".format(self.failover_dir))
            except OSError:
                pass

        return (comment, found_row)

    def test_failover_daemon(self, comment, cmd, logfile, pidfile,
                             stop_daemon, key_phrase=None):
        found_row = key_phrase is None
        if self.debug:
            print(comment)
            print("# COMMAND: {0}".format(cmd))

        # Cleanup in case previous test case failed
        if os.path.exists(self.failover_dir):
            try:
                os.system("rmdir {0}".format(self.failover_dir))
            except OSError:
                pass

        # Run command
        self.start_process(cmd)

        # Wait for console to load
        if self.debug:
            print("# Waiting for console to start.")
        i = 0
        while True:
            time.sleep(1)
            i += 1
            if i > _TIMEOUT:
                if self.debug:
                    print("# Timeout daemon to start.")
                raise MUTLibError("{0}: failed - timeout waiting for "
                                  "daemon to start.".format(comment))

            # Since we don't have any control over the process, try to
            # read the PID to ensure that process started.
            try:
                with open(pidfile, "r") as f:
                    int(f.read().strip())
                break  # The daemon is running
            except IOError:
                continue
            except SystemExit:
                continue
            except ValueError:
                continue

        # Wait for the failover daemon to register on master and start
        # its monitoring process
        phrase = "Failover daemon started"
        if self.debug:
            print("Waiting for failover daemon to register master and start "
                  "its monitoring process")
        time.sleep(5)
        i = 0
        with open(logfile, "r") as f:
            while i < _TIMEOUT:
                line = f.readline()
                if not line:
                    i += 1
                    time.sleep(1)
                elif phrase in line:
                    break
            else:
                if self.debug:
                    msg = ()
                    print("# Timeout waiting for failover daemon to register "
                          "master and start its monitoring process")
                    raise MUTLibError("{0}: failed - timeout waiting for "
                                      "failover daemon to register master and "
                                      "start its monitoring process"
                                      "".format(comment, msg))

        if stop_daemon:
            # Stop daemon
            if self.debug:
                print("# Waiting for daemon to end.")

            # Build stop command by replacing (re)start for stop
            cmd_stop = re.sub("--daemon=(re)?start", "--daemon=stop", cmd)
            self.start_process(cmd_stop)
            i = 0
            while True:
                time.sleep(1)
                i += 1
                if i > _TIMEOUT:
                    if self.debug:
                        print("# Timeout daemon to stop.")
                    raise MUTLibError("{0}: failed - timeout waiting for "
                                      "daemon to stop.".format(comment))
                if not os.path.exists(pidfile):
                    break

            phrase = "Failover daemon stopped"
            if self.debug:
                print("Waiting for failover daemon to unregister master and "
                      "stop its monitoring process")
            i = 0
            with open(logfile, "r") as f:
                while i < _TIMEOUT:
                    line = f.readline()
                    if not line:
                        i += 1
                        time.sleep(1)
                    elif phrase in line:
                        break
                else:
                    if self.debug:
                        print("# Timeout waiting for failover daemon to "
                              "unregister master and start its monitoring "
                              "process")
                        raise MUTLibError("{0}: failed - timeout waiting for "
                                          "failover daemon to unregister "
                                          "master and start its monitoring "
                                          "process".format(comment))

        return (comment, found_row)

    def run(self):
        self.res_fname = "result.txt"

        master_conn = self.build_connection_string(self.server1).strip(" ")
        slave1_conn = self.build_connection_string(self.server2).strip(" ")
        slave2_conn = self.build_connection_string(self.server3).strip(" ")
        slave3_conn = self.build_connection_string(self.server4).strip(" ")
        slave4_conn = self.build_connection_string(self.server5).strip(" ")

        master_str = "--master={0}".format(master_conn)
        slaves_str = "--slaves={0}".format(
            ",".join([slave1_conn, slave2_conn, slave3_conn])
        )
        self.test_results = []
        self.test_cases = []

        failover_cmd = ("python ../scripts/mysqlfailover.py --interval=10 "
                        "--daemon={0} --discover-slaves-login=root:root {1} "
                        "--failover-mode={2} --log={3} "
                        "--exec-post-fail=\"{4}\" --timeout=5{5}")

        i = 1
        cmd = failover_cmd.format("nodetach",
                                  " ".join([master_str, slaves_str]), "auto",
                                  _FAILOVER_LOG.format("1"),
                                  self.fail_event_script,
                                  " --candidates={0}".format(slave1_conn))
        self.test_cases.append(
            (self.server1, cmd, True, _FAILOVER_LOG.format("1"),
             "Test case {0} - Simple failover with --daemon=nodetach "
             "--failover=auto.".format(i),
             _FAILOVER_COMPLETE, False)
        )

        i += 1
        cmd = failover_cmd.format("nodetach",
                                  "--master={0}".format(slave1_conn), "elect",
                                  _FAILOVER_LOG.format("2"),
                                  self.fail_event_script,
                                  " --candidates={0} ".format(slave2_conn))
        self.test_cases.append(
            (self.server2, cmd, True, _FAILOVER_LOG.format("2"),
             "Test case {0} - Simple failover with --failover=elect."
             "".format(i), _FAILOVER_COMPLETE, True)
        )

        i += 1
        cmd = failover_cmd.format("nodetach",
                                  "--master={0}".format(slave2_conn), "fail",
                                  _FAILOVER_LOG.format("3"),
                                  self.fail_event_script, "")
        self.test_cases.append(
            (self.server3, cmd, False, _FAILOVER_LOG.format("3"),
             "Test case {0} - Simple failover with --failover=fail.",
             "Master has failed and automatic".format(i), True)
        )

        i += 1
        cmd = failover_cmd.format("nodetach",
                                  "--master={0}".format(slave3_conn), "fail",
                                  _FAILOVER_LOG.format("4"),
                                  self.fail_event_script, " --force")
        self.test_cases.append(
            (self.server4, cmd, False, _FAILOVER_LOG.format("4"),
             "Test case {0} - Test with --daemon=nodetach and --force on "
             "first run.".format(i), None, True)
        )

        # Run --daemon=nodetach tests
        for test_case in self.test_cases:
            res = self.test_failover_daemon_nodetach(test_case)
            if res:
                self.test_results.append(res)
            else:
                raise MUTLibError("{0}: failed".format(test_case[4]))

        i += 1
        comment = ("Test case {0} - Start failover with --daemon=start."
                   "".format(i))
        cmd_extra = " --pidfile={0}".format(_FAILOVER_PID.format("5"))
        cmd = failover_cmd.format("start",
                                  "--master={0}".format(slave4_conn), "auto",
                                  _FAILOVER_LOG.format("5"),
                                  self.fail_event_script, cmd_extra)

        res = self.test_failover_daemon(comment, cmd,
                                        _FAILOVER_LOG.format("5"),
                                        _FAILOVER_PID.format("5"), False)
        if res:
            self.test_results.append(res)
        else:
            raise MUTLibError("{0}: failed".format(comment))

        i += 1
        comment = ("Test case {0} - Restart failover by using --daemon="
                   "restart and then stop the daemon.".format(i))
        cmd = failover_cmd.format("restart",
                                  "--master={0}".format(slave4_conn), "auto",
                                  _FAILOVER_LOG.format("5"),
                                  self.fail_event_script, cmd_extra)

        res = self.test_failover_daemon(comment, cmd,
                                        _FAILOVER_LOG.format("5"),
                                        _FAILOVER_PID.format("5"), True)
        if res:
            self.test_results.append(res)
        else:
            raise MUTLibError("{0}: failed".format(comment))

        return True
