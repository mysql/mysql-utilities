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
Test options for the mysqlbinlogmove utility.
"""

import os
import time

import binlogmove

from mysql.utilities.exception import MUTLibError


class test(binlogmove.test):
    """Test binlog relocate utility parameters.

    This test checks the behaviour of the mysqlbinlogmove utility using
    different options.

    NOTE: Test extend the base binlogmove test, having the same prerequisites.
    """

    def run(self):
        cmd_base = "mysqlbinlogmove.py"
        master_con = self.build_connection_string(self.server1).strip(' ')
        slave1_con = self.build_connection_string(self.server2).strip(' ')
        slave2_con = self.build_connection_string(self.server3).strip(' ')

        test_num = 1
        comment = "Test case {0} - help option.".format(test_num)
        cmd = "{0} --help".format(cmd_base)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        master_src = self.server1.select_variable('datadir')
        if self.debug:
            print("\nServer {0}:{1} source directory (datadir): "
                  "{2}".format(self.server1.host, self.server1.port,
                               master_src))
        master_index = os.path.join(master_src, 'master-bin.index')
        if self.debug:
            print("\nServer {0}:{1} bin index file: "
                  "{2}".format(self.server1.host, self.server1.port,
                               master_index))
        master_basename = os.path.join(master_src, 'master-bin')
        if self.debug:
            print("\nServer {0}:{1} bin basename: "
                  "{2}".format(self.server1.host, self.server1.port,
                               master_basename))

        test_num += 1
        comment = ("Test case {0} - warning using --bin-log-index with relay "
                   "type.").format(test_num)
        cmd = ("{0} --server={1} --bin-log-index={2} --log-type=relay "
               "--skip-flush-binlogs .").format(cmd_base, master_con,
                                                master_index)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - warning using --bin-log-basename with "
                   "relay type.").format(test_num)
        cmd = ("{0} --server={1} --bin-log-basename={2} --log-type=relay "
               "--skip-flush-binlogs .").format(cmd_base, master_con,
                                                master_basename)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - warning using --relay-log-index with bin "
                   "type.").format(test_num)
        cmd = ("{0} --server={1} --relay-log-index={2} --log-type=bin "
               "--skip-flush-binlogs .").format(cmd_base, master_con,
                                                master_index)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - warning using --relay-log-basename with "
                   "bin type.").format(test_num)
        cmd = ("{0} --server={1} --relay-log-basename={2} --log-type=bin "
               "--skip-flush-binlogs .").format(cmd_base, master_con,
                                                master_basename)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - warning using --skip-flush-binlogs "
                   "without --server.").format(test_num)
        cmd = ("{0} --binlog-dir={1} --skip-flush-binlogs "
               ".").format(cmd_base, self.slave1_dir)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Disable automatic relay log purging on slaves.
        for srv in [self.server2, self.server3]:
            srv.exec_query('SET GLOBAL relay_log_purge = 0')

        # Generate multiple binary log files.
        if self.debug:
            print("\nCreate multiple binary logs on all servers "
                  "(FLUSH LOCAL LOGS)...")
        for srv in [self.server1, self.server2, self.server3]:
            for _ in range(5):
                srv.exec_query('FLUSH LOCAL LOGS')

        # Get parameters info for slave 1 (source, index files, and basenames).
        slave1_src = self.server2.select_variable('datadir')
        if self.debug:
            print("\nServer {0}:{1} source directory (datadir): "
                  "{2}".format(self.server2.host, self.server2.port,
                               slave1_src))
        slave1_bin_index = os.path.join(slave1_src, 'slave1-bin.index')
        if self.debug:
            print("\nServer {0}:{1} bin index file: "
                  "{2}".format(self.server2.host, self.server2.port,
                               slave1_bin_index))
        slave1_bin_basename = os.path.join(slave1_src, 'slave1-bin')
        if self.debug:
            print("\nServer {0}:{1} bin basename: "
                  "{2}".format(self.server2.host, self.server2.port,
                               slave1_bin_basename))
        slave1_relay_index = os.path.join(slave1_src, 'slave1-relay-bin.index')
        if self.debug:
            print("\nServer {0}:{1} relay index file: "
                  "{2}".format(self.server2.host, self.server2.port,
                               slave1_relay_index))
        slave1_relay_basename = os.path.join(slave1_src, 'slave1-relay-bin')
        if self.debug:
            print("\nServer {0}:{1} relay basename: "
                  "{2}".format(self.server2.host, self.server2.port,
                               slave1_relay_basename))

        # Move only binlog files.
        test_num += 1
        comment = ("Test case {0}a - move (only) binlogs from slave "
                   ".").format(test_num)
        cmd = ("{0} --server={1} --bin-log-index={2} --bin-log-basename={3} "
               "--log-type=bin {4}").format(cmd_base, slave1_con,
                                            slave1_bin_index,
                                            slave1_bin_basename,
                                            self.slave1_dir)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        self.results.append("Test case {0}b - check moved files and changes "
                            "in index file:\n".format(test_num))
        self.check_moved_binlogs(self.slave1_dir, slave1_src,
                                 'slave1-bin.index')

        self.results.append("Test case {0}c - SHOW BINARY LOGS (flush "
                            "performed):\n".format(test_num))
        result_set = self.server2.exec_query('SHOW BINARY LOGS')
        for row in result_set:
            self.results.append("file: {0}, size: {1};\n".format(row[0],
                                                                 row[1]))

        comment = "Test case {0}d - move files back.".format(test_num)
        cmd = ("{0} --binlog-dir={1} --bin-log-index={2} "
               "--bin-log-basename={3} --log-type=bin "
               "{4}").format(cmd_base, self.slave1_dir, slave1_bin_index,
                             slave1_bin_basename, slave1_src)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Move only relay log files.
        test_num += 1
        comment = ("Test case {0}a - move (only) relay logs from slave "
                   ".").format(test_num)
        cmd = ("{0} --server={1} --relay-log-index={2} "
               "--relay-log-basename={3} --log-type=relay "
               "{4}").format(cmd_base, slave1_con, slave1_relay_index,
                             slave1_relay_basename, self.slave1_dir)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        self.results.append("Test case {0}b - check moved files and changes "
                            "in index file:\n".format(test_num))
        self.check_moved_binlogs(self.slave1_dir, slave1_src,
                                 'slave1-relay-bin.index')

        comment = "Test case {0}c - move files back.".format(test_num)
        cmd = ("{0} --binlog-dir={1} --relay-log-index={2} "
               "--relay-log-basename={3} --log-type=relay "
               "{4}").format(cmd_base, self.slave1_dir, slave1_relay_index,
                             slave1_relay_basename, slave1_src)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Get parameters info for slave 2 (source, index files, and basenames).
        slave2_src = self.server3.select_variable('datadir')
        if self.debug:
            print("\nServer {0}:{1} source directory (datadir): "
                  "{2}".format(self.server3.host, self.server3.port,
                               slave2_src))
        slave2_bin_index = os.path.join(slave2_src, 'slave2-bin.index')
        if self.debug:
            print("\nServer {0}:{1} bin index file: "
                  "{2}".format(self.server3.host, self.server3.port,
                               slave2_bin_index))
        slave2_bin_basename = os.path.join(slave2_src, 'slave2-bin')
        if self.debug:
            print("\nServer {0}:{1} bin basename: "
                  "{2}".format(self.server3.host, self.server3.port,
                               slave2_bin_basename))
        slave2_relay_index = os.path.join(slave2_src, 'slave2-relay-bin.index')
        if self.debug:
            print("\nServer {0}:{1} relay index file: "
                  "{2}".format(self.server3.host, self.server3.port,
                               slave2_relay_index))
        slave2_relay_basename = os.path.join(slave2_src, 'slave2-relay-bin')
        if self.debug:
            print("\nServer {0}:{1} relay basename: "
                  "{2}".format(self.server3.host, self.server3.port,
                               slave2_relay_basename))

        # Move all binary log (bin and relay) files.
        test_num += 1
        comment = ("Test case {0}a - move (all) bin and relay logs from slave "
                   " (with --skip-flush-binlogs).").format(test_num)
        cmd = ("{0} --server={1} --bin-log-index={2} --bin-log-basename={3} "
               "--relay-log-index={4} --relay-log-basename={5} --log-type=all "
               "--skip-flush-binlogs {6}").format(cmd_base, slave2_con,
                                                  slave2_bin_index,
                                                  slave2_bin_basename,
                                                  slave2_relay_index,
                                                  slave2_relay_basename,
                                                  self.slave2_dir)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        self.results.append("Test case {0}b - check moved files and changes "
                            "in index file:\n".format(test_num))
        self.check_moved_binlogs(self.slave2_dir, slave2_src,
                                 'slave2-bin.index', 'slave2-relay-bin',
                                 'slave2-relay-bin.index')

        self.results.append("Test case {0}c - SHOW BINARY LOGS (flush "
                            "skipped):\n".format(test_num))
        result_set = self.server3.exec_query('SHOW BINARY LOGS')
        for row in result_set:
            self.results.append("file: {0}, size: {1};\n".format(row[0],
                                                                 row[1]))

        comment = "Test case {0}d - move files back.".format(test_num)
        cmd = ("{0} --binlog-dir={1} --bin-log-index={2} "
               "--bin-log-basename={3} --relay-log-index={4} "
               "--relay-log-basename={5} --log-type=all "
               "{6}").format(cmd_base, self.slave2_dir, slave2_bin_index,
                             slave2_bin_basename, slave2_relay_index,
                             slave2_relay_basename, slave2_src)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Move binary log files matching specified sequence numbers.
        test_num += 1
        comment = ("Test case {0}a - move binary logs from slave matching "
                   "specific sequence numbers.").format(test_num)
        cmd = ("{0} --server={1} --bin-log-index={2} --bin-log-basename={3} "
               "--relay-log-index={4} --relay-log-basename={5} --log-type=all "
               "--sequence=2,4-7,11,13 {6}").format(cmd_base, slave1_con,
                                                    slave1_bin_index,
                                                    slave1_bin_basename,
                                                    slave1_relay_index,
                                                    slave1_relay_basename,
                                                    self.slave1_dir)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        self.results.append("Test case {0}b - check moved files and changes "
                            "in index file:\n".format(test_num))
        self.check_moved_binlogs(self.slave1_dir, slave1_src,
                                 'slave1-bin.index', 'slave1-relay-bin',
                                 'slave1-relay-bin.index')

        comment = "Test case {0}c - move files back.".format(test_num)
        cmd = ("{0} --binlog-dir={1} --bin-log-index={2} "
               "--bin-log-basename={3} --relay-log-index={4} "
               "--relay-log-basename={5} --log-type=all "
               "--sequence=2,4-7,11,13 {6}").format(cmd_base, self.slave1_dir,
                                                    slave1_bin_index,
                                                    slave1_bin_basename,
                                                    slave1_relay_index,
                                                    slave1_relay_basename,
                                                    slave1_src)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Hack modified date/time for a few binary log files.
        files_to_hack_date = ['slave2-bin.000002', 'slave2-relay-bin.000005',
                              'slave2-relay-bin.000010']
        # Hacked date/time: 2 days and 1 second before current.
        hacked_time = time.time() - (86400 * 2) - 1
        for f_name in files_to_hack_date:
            file_path = os.path.join(slave2_src, f_name)
            os.utime(file_path, (hacked_time, hacked_time))

        # Move older binary log files (prior to a specific date).
        test_num += 1
        comment = ("Test case {0} - move binary logs from slave modified "
                   "3 days ago (no files to move).").format(test_num)
        cmd = ("{0} --server={1} --bin-log-index={2} --bin-log-basename={3} "
               "--relay-log-index={4} --relay-log-basename={5} --log-type=all "
               "--modified-before=3 {6}").format(cmd_base, slave2_con,
                                                 slave2_bin_index,
                                                 slave2_bin_basename,
                                                 slave2_relay_index,
                                                 slave2_relay_basename,
                                                 self.slave2_dir)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0}a - move binary logs from slave modified "
                   "2 days ago.").format(test_num)
        cmd = ("{0} --server={1} --bin-log-index={2} --bin-log-basename={3} "
               "--relay-log-index={4} --relay-log-basename={5} --log-type=all "
               "--modified-before=2 {6}").format(cmd_base, slave2_con,
                                                 slave2_bin_index,
                                                 slave2_bin_basename,
                                                 slave2_relay_index,
                                                 slave2_relay_basename,
                                                 self.slave2_dir)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        self.results.append("Test case {0}b - check moved files and changes "
                            "in index file:\n".format(test_num))
        self.check_moved_binlogs(self.slave2_dir, slave2_src,
                                 'slave2-bin.index', 'slave2-relay-bin',
                                 'slave2-relay-bin.index')

        comment = "Test case {0}c - move files back.".format(test_num)
        cmd = ("{0} --binlog-dir={1} --bin-log-index={2} "
               "--bin-log-basename={3} --relay-log-index={4} "
               "--relay-log-basename={5} --log-type=all "
               "--modified-before=2 {6}").format(cmd_base, self.slave2_dir,
                                                 slave2_bin_index,
                                                 slave2_bin_basename,
                                                 slave2_relay_index,
                                                 slave2_relay_basename,
                                                 slave2_src)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0}a - move binary logs from slave modified "
                   "before yesterday.").format(test_num)
        yesterday_time = time.localtime(time.time() - 86400)
        yesterday = time.strftime('%Y-%m-%d', yesterday_time)
        cmd = ("{0} --server={1} --bin-log-index={2} --bin-log-basename={3} "
               "--relay-log-index={4} --relay-log-basename={5} --log-type=all "
               "--modified-before={6} {7}").format(cmd_base, slave2_con,
                                                   slave2_bin_index,
                                                   slave2_bin_basename,
                                                   slave2_relay_index,
                                                   slave2_relay_basename,
                                                   yesterday, self.slave2_dir)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        self.results.append("Test case {0}b - check moved files and changes "
                            "in index file:\n".format(test_num))
        self.check_moved_binlogs(self.slave2_dir, slave2_src,
                                 'slave2-bin.index', 'slave2-relay-bin',
                                 'slave2-relay-bin.index')

        comment = "Test case {0}c - move files back.".format(test_num)
        cmd = ("{0} --binlog-dir={1} --bin-log-index={2} "
               "--bin-log-basename={3} --relay-log-index={4} "
               "--relay-log-basename={5} --log-type=all "
               "--modified-before={6} {7}").format(cmd_base, self.slave2_dir,
                                                   slave2_bin_index,
                                                   slave2_bin_basename,
                                                   slave2_relay_index,
                                                   slave2_relay_basename,
                                                   yesterday, slave2_src)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Mask non-deterministic data.
        self.replace_substring_portion(", size: 1", ";", ", size: 1??;")
        # Remove version information.
        self.remove_result_and_lines_after("MySQL Utilities mysqlbinlogmove"
                                           " version", 1)
        # Warning messages for older MySQL versions (variables not available).
        self.remove_result("# WARNING: Variable 'relay_log_basename' is not "
                           "available for server ")
        self.remove_result("# WARNING: Variable 'log_bin_basename' is not "
                           "available for server ")
        self.remove_result("# WARNING: The bin basename is not required for "
                           "server versions >= 5.6.2 (value ignored).")
        self.remove_result("# WARNING: The bin index is not required for "
                           "server versions >= 5.6.4 (value ignored).")
        self.remove_result("# WARNING: The relay basename is not required for "
                           "server versions >= 5.6.2 (value ignored).")

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)
