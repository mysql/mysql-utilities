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
Test the main features of the mysqlbinlogmove utility.
"""

import os
import shutil

import rpl_admin
from mysql.connector import OperationalError

from mysql.utilities.common.tools import delete_directory
from mysql.utilities.exception import MUTLibError


MYSQL_OPTS_DEFAULT = ('"--log-bin={log_bin} '
                      '--relay-log={relay_log} '
                      '--skip-slave-start"')

_TEMP_BINLOG_DIR = './temp_binlog/'


class test(rpl_admin.test):
    """Test binlog relocate utility.

    This test runs the mysqlbinlogmove utility to test its base features.
    """

    # Define values here to avoid pylint warning (W0201: Attribute defined
    # outside __init__). Note: Better using super().__init__()
    master_dir = None
    slave1_dir = None
    slave2_dir = None

    def check_prerequisites(self):
        # Check required server version.
        # Reason: FLUSH BINARY LOGS not available prior to 5.5.3.
        if not self.servers.get_server(0).check_version_compat(5, 5, 3):
            raise MUTLibError("Test requires server version >= 5.5.3")
        return self.check_num_servers(1)

    def setup(self):
        self.res_fname = "result.txt"

        # Spawn servers
        self.server0 = self.servers.get_server(0)
        mysqld = MYSQL_OPTS_DEFAULT.format(log_bin='master-bin',
                                           relay_log='master-relay-bin')
        self.server1 = self.servers.spawn_server("rep_master", mysqld,
                                                 True)
        mysqld = MYSQL_OPTS_DEFAULT.format(log_bin='slave1-bin',
                                           relay_log='slave1-relay-bin')
        self.server2 = self.servers.spawn_server("rep_slave1", mysqld,
                                                 True)
        mysqld = MYSQL_OPTS_DEFAULT.format(log_bin='slave2-bin',
                                           relay_log='slave2-relay-bin')
        self.server3 = self.servers.spawn_server("rep_slave2", mysqld,
                                                 True)

        # Reset spawned servers (clear binary log and GTID_EXECUTED set)
        self.reset_master([self.server1, self.server2, self.server3])

        # Set replication topology.
        self.reset_topology([self.server2, self.server3])

        # Create temp directories to hold moved binary logs.
        if self.debug:
            print("\nCreating temporary directories...")
        self.master_dir = os.path.normpath(os.path.join(_TEMP_BINLOG_DIR,
                                                        'master'))
        os.makedirs(self.master_dir)
        if self.debug:
            print(" - {0}".format(os.path.abspath(self.master_dir)))
        self.slave1_dir = os.path.normpath(os.path.join(_TEMP_BINLOG_DIR,
                                                        'salve1'))
        os.makedirs(self.slave1_dir)
        if self.debug:
            print(" - {0}".format(os.path.abspath(self.slave1_dir)))
        self.slave2_dir = os.path.normpath(os.path.join(_TEMP_BINLOG_DIR,
                                                        'slave2'))
        os.makedirs(self.slave2_dir)
        if self.debug:
            print(" - {0}".format(os.path.abspath(self.slave2_dir)))

        return True

    def check_moved_binlogs(self, dest_dir, src_dir, index_filename,
                            other_basename=None, other_index=None):
        """Check moved binary log files and changes in the index file.

        This method list the files in the destination directory (printing
        them to the result file) and verify if respective entries are found
        (updated) in the index file.

        dest_dir[in]        Destination directory (where the binary log files
                            were moved).
        src_dir[in]         Source directory (where the binary log index file
                            is located)
        index_filename[in]  Filename of the binary log index file.
        other_basename[in]  Basename for the additional type of binary logs to
                            check. Use when files from multiple types are
                            found in the destination directory (i.e., bin and
                            relay).
        other_index[in]     Filename of the binary log index file for the
                            additional type to check (bin or relay log).
        """
        # List all files in the destination directory.
        for f_name in sorted(os.listdir(dest_dir)):
            # Get index entry for file including destination directory.
            index_entry = os.path.join(dest_dir, f_name)
            # Search for matching file entry in the index file.
            found = False
            # Get full path to the index file.
            if other_basename and f_name.startswith(other_basename):
                log_index = os.path.join(src_dir, other_index)
            else:
                log_index = os.path.join(src_dir, index_filename)
            with open(log_index, 'r') as index_file:
                data = index_file.readlines()
                for line in data:
                    # Note: path start can be ignored (working directory).
                    if line.strip().endswith(index_entry):
                        found = True
                        break
            self.results.append("File moved: '{0}' (index updated: {1})"
                                "\n".format(f_name, found))
        self.results.append("\n")

    def run(self):

        cmd_base = "mysqlbinlogmove.py"
        master_con = self.build_connection_string(self.server1).strip(' ')
        slave1_con = self.build_connection_string(self.server2).strip(' ')

        if self.debug:
            print("\nCreate multiple binary logs on all servers "
                  "(FLUSH LOGS)...")
        for srv in [self.server1, self.server2, self.server3]:
            for _ in range(5):
                srv.exec_query('FLUSH LOCAL LOGS')

        # Stop slaves to avoid the creation of more relay logs.
        for srv in [self.server2, self.server3]:
            srv.exec_query('STOP SLAVE')

        test_num = 1
        comment = ("Test case {0}a - move binary logs from running server "
                   "(master).").format(test_num)
        cmd = "{0} --server={1} {2}".format(cmd_base, master_con,
                                            self.master_dir)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        master_src = self.server1.select_variable('datadir')
        if self.debug:
            print("\nServer {0}:{1} source directory (datadir): "
                  "{2}".format(self.server1.host, self.server1.port,
                               master_src))

        self.results.append("Test case {0}b - check moved files and changes "
                            "in index file:\n".format(test_num))
        self.check_moved_binlogs(self.master_dir, master_src,
                                 'master-bin.index')

        test_num += 1
        comment = ("Test case {0}a - move binary logs from running server "
                   "(slave 1).").format(test_num)
        cmd = "{0} --server={1} {2}".format(cmd_base, slave1_con,
                                            self.slave1_dir)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        slave1_src = self.server2.select_variable('datadir')
        if self.debug:
            print("\nServer {0}:{1} source directory (datadir): "
                  "{2}".format(self.server2.host, self.server2.port,
                               slave1_src))

        self.results.append("Test case {0}b - check moved files and changes "
                            "in index file:\n".format(test_num))
        self.check_moved_binlogs(self.slave1_dir, slave1_src,
                                 'slave1-bin.index')

        # Get binary log source directory (datadir) for slave 2.
        slave2_src = self.server3.select_variable('datadir')
        if self.debug:
            print("\nServer {0}:{1} source directory (datadir): "
                  "{2}".format(self.server3.host, self.server3.port,
                               slave2_src))
            print("\nStopping server {0}:{1}...".format(self.server3.host,
                                                        self.server3.port))
        # Stop slave 2 (to move binlogs with --source).
        self.servers.stop_server(self.server3, drop=False)

        test_num += 1
        comment = ("Test case {0}a - move binary logs for stopped server "
                   "(slave 2).").format(test_num)
        cmd = "{0} --binlog-dir={1} {2}".format(cmd_base, slave2_src,
                                                self.slave2_dir)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        self.results.append("Test case {0}b - check moved files and changes "
                            "in index file:\n".format(test_num))
        self.check_moved_binlogs(self.slave2_dir, slave2_src,
                                 'slave2-bin.index')

        # Clean state data and filesystem for stopped server (slave 2).
        if self.debug:
            print("\nCleaning data for server {0}:{1} (already stopped)..."
                  "".format(self.server3.host, self.server3.port))
        self.servers.remove_server(self.server3.role)
        delete_directory(slave2_src)

        # Mask non-deterministic data.
        # Warning messages for older MySQL versions (variables not available).
        self.remove_result("# WARNING: Variable 'log_bin_basename' is not "
                           "available for server ")

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        if self.res_fname:
            try:
                os.unlink(self.res_fname)
            except OSError:
                pass
        # Remove temp directory.
        shutil.rmtree(os.path.normpath(_TEMP_BINLOG_DIR))
        # Kill all spawned servers.
        self.kill_server_list(
            ['rep_master', 'rep_slave1']
        )
        # Attempt to kill slave 2, in case test ended before stopping it.
        try:
            self.kill_server('rep_slave2')
        except OperationalError:
            # Ignore error if server is not available (already stopped).
            pass
        return True
