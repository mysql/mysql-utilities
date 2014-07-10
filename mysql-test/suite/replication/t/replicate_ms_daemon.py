#
# Copyright (c) 2014, Oracle and/or its affiliates. All rights reserved.
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

"""
replicate_ms_daemon test.
"""

import os
import re
import time

import replicate_ms

from mysql.utilities.exception import MUTLibError


_RPLMS_LOG = "{0}rplms_log.txt"
_RPLMS_PID = "{0}rplms_pid.txt"
_TIMEOUT = 30
_SWITCHOVER_TIMEOUT = 60
_DEFAULT_MYSQL_OPTS = ('"--log-bin=mysql-bin --skip-slave-start '
                       '--log-slave-updates --gtid-mode=on '
                       '--enforce-gtid-consistency --report-host=127.0.0.1 '
                       '--report-port={port} '
                       '--sync-master-info=1 --master-info-repository=table"')


class test(replicate_ms.test):
    """Test multi-source replication daemon.

    This test exercises the mysqlrpms utility using a POSIX daemon.

    Note: this test requires GTID enabled servers.
    """

    log_range = range(1, 3)
    total_masters = 2

    def check_prerequisites(self):
        if os.name != "posix":
            raise MUTLibError("Test requires a POSIX system.")
        return super(test, self).check_prerequisites()

    def test_rplms_daemon(self, cmd, logfile, comment, pidfile, stop_daemon):
        """Test multi-source replication daemon.

        cmd[in]           Command to be executed.
        logfile[in]       Log filename.
        comment[in]       Test comment.
        pidfile[in]       PID file.
        stop_daemon[in]   True to execute --daemon=stop

        This method create a process by executing the command and waits for
        the round-robin scheduling to switch all the masters. At the end
        compares the databases.
        """
        # Since this test case expects the process to stop, we can launch it
        # via a subprocess and wait for it to finish.
        if self.debug:
            print(comment)
            print("# COMMAND: {0}".format(cmd))

        # Run command
        proc, _ = self.start_process(cmd)

        # Wait for process to load
        if self.debug:
            print("# Waiting for daemon to start.")
        i = 1
        time.sleep(1)
        while proc.poll() is not None:
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

        # Wait for logfile file to be created
        if self.debug:
            print("# Waiting for logfile to be created.")
        for i in range(_TIMEOUT):
            if os.path.exists(logfile):
                break
            else:
                time.sleep(1)
        else:
            raise MUTLibError("{0}: failed - timeout waiting for "
                              "logfile '{1}' to be "
                              "created.".format(comment, logfile))

        # Wait for switching all the masters
        self.wait_for_switching_all_masters(logfile, comment)

        # Compare databases
        self.compare_databases(comment)

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

            phrase = "Multi-source replication daemon stopped"
            if self.debug:
                print("# Waiting for multi-source replication daemon to stop.")
            i = 0
            with open(logfile, "r") as file_:
                while i < _TIMEOUT:
                    line = file_.readline()
                    if not line:
                        i += 1
                        time.sleep(1)
                    elif phrase in line:
                        break
                else:
                    if self.debug:
                        print("# Timeout waiting for multi-source replication "
                              "daemon to stop.")
                        raise MUTLibError("{0}: failed - timeout waiting for "
                                          "multi-source daemon to stop."
                                          "".format(comment))

        # Cleanup after test case
        try:
            os.unlink(logfile)
        except OSError:
            pass

    def run(self):
        slave_conn = self.build_connection_string(self.server1).strip(' ')
        master1_conn = self.build_connection_string(self.server2).strip(' ')
        master2_conn = self.build_connection_string(self.server3).strip(' ')

        slave_str = "--slave={0}".format(slave_conn)
        masters_str = "--masters={0}".format(
            ",".join([master1_conn, master2_conn])
        )

        base_cmd = ("python ../scripts/mysqlrplms.py --daemon={0} --log={1} "
                    "--interval=5 --switchover-interval=30 --rpl-user=rpl:rpl "
                    "{2} {3}{4}")
        test_num = 1
        nodetach_cmd = base_cmd.format("nodetach", _RPLMS_LOG.format(1),
                                       slave_str, masters_str, "")
        comment = ("Test case {0} - Multi-source replication daemon with "
                   "--daemon=nodetach.".format(test_num))
        self.test_rplms(nodetach_cmd, _RPLMS_LOG.format(1), comment,
                        True)

        # Drop all
        self.drop_all()

        # Reset topology
        self.reset_ms_topology()

        # Create data
        self.create_all()

        test_num += 1
        extra_cmd = " --pidfile={0}".format(_RPLMS_PID.format(2))
        start_cmd = base_cmd.format("start", _RPLMS_LOG.format(2), slave_str,
                                    masters_str, extra_cmd)
        comment = ("Test case {0} - Multi-source replication daemon with "
                   "--daemon=start.".format(test_num))
        self.test_rplms_daemon(start_cmd, _RPLMS_LOG.format(2), comment,
                               _RPLMS_PID.format(2), False)

        test_num += 1
        extra_cmd = " --pidfile={0}".format(_RPLMS_PID.format(2))
        start_cmd = base_cmd.format("restart", _RPLMS_LOG.format(2), slave_str,
                                    masters_str, extra_cmd)
        comment = ("Test case {0} - Multi-source replication daemon with "
                   "--daemon=restart and then stop the daemon."
                   "".format(test_num))
        self.test_rplms_daemon(start_cmd, _RPLMS_LOG.format(2), comment,
                               _RPLMS_PID.format(2), True)

        return True
