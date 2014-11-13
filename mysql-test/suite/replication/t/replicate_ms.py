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
replicate_ms test.
"""

import os
import shlex
import subprocess
import time

import rpl_admin

from mysql.utilities.exception import MUTLibError, UtilError
from mutlib.mutlib import stop_process
from mysql.utilities.common.server import get_connection_dictionary
from mysql.utilities.common.messages import (MSG_UTILITIES_VERSION,
                                             MSG_MYSQL_VERSION)
from mysql.utilities import VERSION_STRING


_RPLMS_LOG = "{0}rplms_log.txt"
_TIMEOUT = 30
_SWITCHOVER_TIMEOUT = 120
_DEFAULT_MYSQL_OPTS = ('"--log-bin=mysql-bin --skip-slave-start '
                       '--log-slave-updates --gtid-mode=on '
                       '--enforce-gtid-consistency --report-host=127.0.0.1 '
                       '--report-port={port} '
                       '--sync-master-info=1 --master-info-repository=table"')


class test(rpl_admin.test):
    """Test multi-source replication.

    This test exercises the mysqlrplms utility.
    """

    log_range = range(1, 2)
    total_masters = 2
    server0 = None
    server1 = None
    server2 = None
    server3 = None

    def check_prerequisites(self):
        if not self.servers.get_server(0).check_version_compat(5, 6, 9):
            raise MUTLibError("Test requires server version 5.6.9")
        return self.check_num_servers(1)

    def setup(self):
        self.res_fname = "result.txt"

        # Spawn servers
        self.server0 = self.servers.get_server(0)
        mysqld = _DEFAULT_MYSQL_OPTS.format(port=self.servers.view_next_port())
        self.server1 = self.servers.spawn_server("rep_slave", mysqld, True)
        mysqld = _DEFAULT_MYSQL_OPTS.format(port=self.servers.view_next_port())
        self.server2 = self.servers.spawn_server("rep_master1", mysqld, True)
        mysqld = _DEFAULT_MYSQL_OPTS.format(port=self.servers.view_next_port())
        self.server3 = self.servers.spawn_server("rep_master2", mysqld, True)
        self.total_masters = 2

        # Drop all
        self.drop_all()

        # Reset topology
        self.reset_ms_topology()

        # Create data
        self.create_all()

        # Remove log files (leftover from previous test).
        self.cleanup_logs()

        return True

    def start_process(self, cmd):
        """Starts a process by executing the command using the subprocess
        module.
        """
        # Check if cmd is a list of commands
        if isinstance(cmd, list):
            pass
        else:
            is_posix = True if os.name == 'posix' else False
            cmd = shlex.split(cmd, is_posix)

        if self.debug:
            f_out = None
            stdout = subprocess.PIPE
            stderr = subprocess.PIPE
        else:
            file_ = os.devnull
            f_out = open(file_, 'w')
            stdout = f_out
            stderr = f_out

        proc = subprocess.Popen(cmd, stdout=stdout,
                                stderr=stderr)
        return proc, f_out

    def wait_for_switching_all_masters(self, logfile, comment):
        """Wait for switching all the masters.

        This method waits for switching all masters in the round-robin
        scheduling by searching the "Switching to master" phrase in the log
        file.

        logfile[in]       Log filename.
        comment[in]       Test comment.
        """
        phrase = "Switching to master"
        if self.debug:
            print("# Waiting for switching all the masters.")

        i = 0
        master_idx = 1

        with open(logfile, "r") as file_:
            while i < _SWITCHOVER_TIMEOUT:
                line = file_.readline()
                if not line:
                    i += 1
                    time.sleep(1)
                elif phrase in line:
                    if master_idx > self.total_masters:
                        break
                    master_idx += 1
                    i = 0
            else:
                if self.debug:
                    print("# Timeout waiting for round-robin of all masters.")
                raise MUTLibError("{0}: failed - Timeout waiting for "
                                  "round-robin of all masters".format(comment))

    def compare_databases(self, comment):
        """Compare databases.

        This method compares the databases replicated.

        comment[in]       Test comment.
        """
        # Compare command
        compare_cmd = "mysqldbcompare.py {0} {1} {2}:{2}"
        from_conn = "--server1={0}".format(
            self.build_connection_string(self.server1))

        # Compare `inventory` database from master1
        to_conn = "--server2={0}".format(
            self.build_connection_string(self.server2)
        )
        res = self.run_test_case(
            0,
            compare_cmd.format(from_conn, to_conn, "inventory"),
            "Comparing `inventory` database."
        )
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Compare `import_test` database from master2
        to_conn = "--server2={0}".format(
            self.build_connection_string(self.server3)
        )
        res = self.run_test_case(
            0,
            compare_cmd.format(from_conn, to_conn, "import_test"),
            "Comparing `import_test` database."
        )
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

    def find_stop_phrase(self, logfile, comment, stop_phrase):
        """Find stop phrase in the log file.

        logfile[in]       Log filename.
        comment[in]       Test comment.
        stop_phrase[in]   Phrase to be found.

        Raises a MUTLibError if the phrase is not found.
        """
        # Check result code from stop_process then read the log to find the
        # key phrase.
        found_row = False
        with open(logfile, "r") as file_:
            rows = file_.readlines()
            if self.debug:
                print("# Looking in log for: {0}".format(stop_phrase))
            for row in rows:
                if stop_phrase in row:
                    found_row = True
                    if self.debug:
                        print("# Found in row = '{0}'."
                              "".format(row[:len(row) - 1]))
        if not found_row:
            if self.debug:
                print("# ERROR: Cannot find entry in log:")
                for row in rows:
                    print(row)
            raise MUTLibError("{0}: failed - cannot find entry in log."
                              "".format(comment))

    def kill_process(self, proc, f_out, comment):
        """Kill process spwaned by subprocess.

        proc[in]          Subprocess process.
        f_out[in]         Output file.
        stop_phrase[in]   Phrase to be found.
        """
        # Need to poll here and wait for process to really end
        ret_val = stop_process(proc, True)
        if f_out and not f_out.closed:
            f_out.close()
        # Wait for process to end
        if self.debug:
            print("# Waiting for process to end.")
        i = 0
        while proc.poll() is None:
            time.sleep(1)
            i += 1
            if i > _TIMEOUT:
                if self.debug:
                    print("# Timeout process to end.")
                raise MUTLibError("{0}: failed - timeout waiting for "
                                  "process to end.".format(comment))

        if self.debug:
            print("# Return code from process termination = {0}"
                  "".format(ret_val))

    def test_rplms(self, cmd, logfile, comment, kill_process=True,
                   stop_phrase=None):
        """Test multi-source replication.

        cmd[in]           Command to be executed.
        logfile[in]       Log filename.
        comment[in]       Test comment.
        kill_process[in]  True if the process is to be killed.
        stop_phrase[in]   Stop phrase to be searched in the log.

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
        proc, f_out = self.start_process(cmd)

        # Wait for process to load
        if self.debug:
            print("# Waiting for process to start.")
        i = 1
        time.sleep(1)
        while proc.poll() is not None:
            time.sleep(1)
            i += 1
            if i > _TIMEOUT:
                if self.debug:
                    print("# Timeout process to start.")
                raise MUTLibError("{0}: failed - timeout waiting for "
                                  "process to start.".format(comment))

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

        # Kill process
        if kill_process:
            self.kill_process(proc, f_out, comment)

        # Find stop phrase
        if stop_phrase:
            self.find_stop_phrase(logfile, comment, stop_phrase)

        # Find MySQL Utilities version in the log
        utils_phrase = MSG_UTILITIES_VERSION.format(utility="mysqlrplms",
                                                    version=VERSION_STRING)
        self.find_stop_phrase(logfile, comment, utils_phrase)

        # Find MySQL servers versions in the log
        for server in (self.server1, self.server2, self.server3,):
            host_port = "{host}:{port}".format(
                **get_connection_dictionary(server))
            server_version = server.get_version()
            mysql_phrase = MSG_MYSQL_VERSION.format(server=host_port,
                                                    version=server_version)
            self.find_stop_phrase(logfile, comment, mysql_phrase)

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

        test_num = 1
        rplms_cmd = ("python ../scripts/mysqlrplms.py --log={0} --interval=5 "
                     "--switchover-interval=30 --rpl-user=rpl:rpl {1} {2}"
                     "".format(_RPLMS_LOG.format(test_num), slave_str,
                               masters_str))
        comment = ("Test case {0} - Simple multi-source replication."
                   "".format(test_num))
        self.test_rplms(rplms_cmd, _RPLMS_LOG.format(test_num), comment, True)
        return True

    def reset_ms_topology(self):
        """Resets multi-source topology.

        Resets all servers and stop the slave.
        """
        # Stop slave
        try:
            self.server1.exec_query("STOP SLAVE")
        except UtilError:
            pass
        self.reset_master([self.server1, self.server2, self.server3])
        # Reset slave
        try:
            self.server1.exec_query("RESET SLAVE")
        except UtilError:
            pass

    def get_result(self):
        # If run method executes successfully without throwing any exceptions,
        # then test was successful
        return True, None

    def record(self):
        # Not a comparative test
        return True

    def create_all(self):
        """Create all databases needed for this test.
        """
        # Create data for master1
        try:
            data_file = os.path.normpath("./std_data/db_compare_test.sql")
            self.server2.read_and_exec_SQL(data_file, self.debug)
        except UtilError as err:
            raise MUTLibError("Failed to read commands from file {0}: "
                              "{1}".format(data_file, err.errmsg))

        # Create data for master2
        try:
            data_file = os.path.normpath("./std_data/import_data.sql")
            self.server3.read_and_exec_SQL(data_file, self.debug)
        except UtilError as err:
            raise MUTLibError("Failed to read commands from file {0}: "
                              "{1}".format(data_file, err.errmsg))

    def drop_all(self):
        """Drop all databases used in this test.
        """
        self.drop_db(self.server1, "empty_db")
        self.drop_db(self.server1, "inventory")
        self.drop_db(self.server1, "multi_span_row")
        self.drop_db(self.server1, "import_test")
        self.drop_db(self.server2, "empty_db")
        self.drop_db(self.server2, "inventory")
        self.drop_db(self.server2, "multi_span_row")
        self.drop_db(self.server3, "import_test")

    def cleanup_logs(self):
        """Remove all log files.
        """
        for log in self.log_range:
            try:
                if os.path.exists(_RPLMS_LOG.format(log)):
                    os.unlink(_RPLMS_LOG.format(log))
            except OSError:
                pass

    def cleanup(self):
        self.cleanup_logs()
        self.drop_all()

        if self.res_fname:
            try:
                os.unlink(self.res_fname)
            except OSError:
                pass

        # Kill all spawned servers.
        self.kill_server_list(
            ['rep_slave', 'rep_master1', 'rep_master2']
        )
        return True
