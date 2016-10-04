#
# Copyright (c) 2014, 2016, Oracle and/or its affiliates. All rights reserved.
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
binlog_rotate test.
"""

import os

import mutlib

from mysql.utilities.exception import MUTLibError


def binlog_file_exists(search_path, binlog_file, debug=False):
    """Tells if a binlog file exist in the given search path

    search_path[in]    the system path where to look at.
    binlog_file[in]    binlog file name to check if exists.
    debug[in]          Print debug messages. False by default

    Returns true in case the binlog file exists in the given path, false
    otherwise.
    """
    file_path = os.path.join(search_path, binlog_file)
    if os.path.exists(file_path):
        if debug:
            print("The binlog file '{0}' was found in {1}"
                  "".format(binlog_file, search_path))
        return True
    else:
        if debug:
            print("The binlog file '{0}' was NOT found in {1}"
                  "".format(binlog_file, search_path))
        return False


def binlog_range_files_exists(binlog_range, search_path,
                              binlog_base="mysql-bin.000000", debug=False):
    """Tells if a binlog file range exist in the given search path

    binlog_range[in]   A tuple with the binlog range to check, i.e (0,3)
    search_path[in]    The system path where to look at.
    binlog_base[in]    Binlog file base name.
    debug[in]          Print debug messages. False by default

    Returns a list of True or False values, True whenever the binlog file
    exists in the given path or False if not.
    otherwise.
    """
    # binlog files to check
    binlog_files = []

    # Fill the binlog file list with binlog file names to check.
    binlog_file_name, binlog_counter = binlog_base.split('.')
    for index in range(binlog_range[0], binlog_range[1] + 1):
        z_len = len(binlog_counter)
        binlog_file = ("{0}.{1}".format(binlog_file_name,
                                        repr(index).zfill(z_len)))
        binlog_files.append(binlog_file)

    # results
    results = []

    for binlog_file in binlog_files:
        results.append(binlog_file_exists(search_path, binlog_file, debug))

    return results


class test(mutlib.System_test):
    """Tests the rotate binlog utility
    This test executes the rotate binlog utility on a single server.
    """

    server1 = None
    server1_datadir = None

    def check_prerequisites(self):
        # Need at least one server.
        return self.check_num_servers(1)

    def setup(self):
        mysqld = (
            "--log-bin=mysql-bin --report-port={0}"
        ).format(self.servers.view_next_port())
        self.server1 = self.servers.spawn_server(
            "server1_binlog_rotate", mysqld, True)

        # Get datadir
        rows = self.server1.exec_query("SHOW VARIABLES LIKE 'datadir'")
        if not rows:
            raise MUTLibError("Unable to determine datadir of cloned server "
                              "at {0}:{1}".format(self.server1.host,
                                                  self.server1.port))
        self.server1_datadir = rows[0][1]

        return True

    def run(self):
        self.res_fname = "result.txt"
        from_conn = "--server={0}".format(
            self.build_connection_string(self.server1))

        cmd_str = "mysqlbinlogrotate.py {0}".format(from_conn)

        test_num = 1
        comment = ("Test case {0} - simple rotate"
                   "".format(test_num))
        cmd = "{0}".format(cmd_str)
        res = self.run_test_case(0, cmd, comment)
        if not res or not binlog_file_exists(self.server1_datadir,
                                             "mysql-bin.000002", self.debug):
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - simple rotate (-vv)"
                   "".format(test_num))
        cmd = "{0} -vv".format(cmd_str)
        res = self.run_test_case(0, cmd, comment)
        if not res or not binlog_file_exists(self.server1_datadir,
                                             "mysql-bin.000003", self.debug):
            raise MUTLibError("{0}: failed".format(comment))

        # Mask version
        self.replace_result(
            "MySQL Utilities mysqlbinlogpurge version",
            "MySQL Utilities mysqlbinlogpurge version X.Y.Z "
            "(part of MySQL Workbench ... XXXXXX)\n"
        )

        self.replace_result(
            "# Active binlog file: ",
            "# Active binlog file: 'XXXXX-XXX:XXXXXX' (size: XXX bytes)\n"
        )

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        # Kill the servers that are only for this test.
        kill_list = ['server1_binlog_rotate']
        return self.kill_server_list(kill_list)
