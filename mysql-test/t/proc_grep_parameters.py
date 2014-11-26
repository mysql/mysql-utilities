#
# Copyright (c) 2010, 2014, Oracle and/or its affiliates. All rights reserved.
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
proc_grep_parameters test.
"""

import os
import proc_grep
import subprocess
import tempfile
import time

from mutlib.mutlib import kill_process
from mysql.utilities.common.tools import get_tool_path
from mysql.utilities.exception import MUTLibError, UtilError
from mysql.utilities.common.server import get_connection_dictionary


class test(proc_grep.test):
    """Process grep
    This test executes the process grep utility parameters.
    It uses the proc_grep test as a parent for setup and teardown methods.
    """

    mysql_path = None

    def check_prerequisites(self):
        return proc_grep.test.check_prerequisites(self)

    def setup(self):
        proc_grep.test.setup(self)
        rows = self.server1.exec_query("SHOW VARIABLES LIKE 'basedir'")
        if rows:
            basedir = rows[0][1]
        else:
            raise MUTLibError("Unable to determine 'basedir' for base server.")

        try:
            self.mysql_path = get_tool_path(basedir, "mysql")
        except UtilError as err:
            raise MUTLibError("Unable to find mysql client tool for server "
                              "{0}@{1} on basedir={2}. "
                              "ERROR: {3}".format(self.server1.host,
                                                  self.server1.port, basedir,
                                                  err.errmsg))
        return True

    def run(self):
        self.res_fname = "result.txt"
        from_conn = self.build_connection_string(self.server1)
        conn_val = self.get_connection_values(self.server1)

        cmd_str = "mysqlprocgrep.py --server={0} ".format(from_conn)
        test_num = 1
        comment = "Test case {0} - do the help".format(test_num)
        res = self.run_test_case(0, cmd_str + "--help", comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Remove version information
        self.remove_result_and_lines_after("MySQL Utilities mysqlprocgrep.py "
                                           "version", 6)

        test_num += 1
        comment = "Test case {0} - do the SQL for a simple search".format(
            test_num)
        cmd_str = "mysqlprocgrep.py --sql --match-user={0} ".format(
            conn_val[0])
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # execute the mysql client to create a new connection
        conn_dict = get_connection_dictionary(self.server1)
        arguments = [
            self.mysql_path,
            "-u{0}".format(conn_dict['user']),
            "-p{0}".format(conn_dict['passwd']),
            "-h127.0.0.1",
            "--port={0}".format(conn_dict['port']),
            "mysql",
        ]
        out_file = tempfile.TemporaryFile()
        proc = subprocess.Popen(arguments, stdout=out_file,
                                stdin=subprocess.PIPE, stderr=out_file)
        # wait for console to start
        time.sleep(5)
        test_num += 1
        processes = self.server1.exec_query("show processlist")
        for proc_item in processes:
            if proc_item[3] == "mysql" and proc_item[4] == "Sleep":
                proc_id = proc_item[0]
            else:
                proc_id = 0
        comment = "Test case {0} - do kill".format(
            test_num)
        cmd_str = "mysqlprocgrep.py {0}{1} {2} {3} {4} {5}{6} {7}".format(
            "--match-user=", conn_val[0], "--match-command=Sleep",
            "--match-db=mysql", "--kill-connection", "--server=",
            from_conn, "--format=CSV")
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        kill_process(proc)

        # Mask out process list for deterministic result
        self.replace_result("{0},".format(proc_id), "XXX,...\n")

        self.mask_result("    USER LIKE 'root'", "    USER LIKE 'root'",
                         "    USER LIKE 'XXXX'")

        # Mask funny output on Windows
        if os.name != "posix":
            self.replace_result("    USER LIKE ", "    USER LIKE 'XXXX'\n")

        # Mask version
        self.replace_result(
            "MySQL Utilities mysqlprocgrep version",
            "MySQL Utilities mysqlprocgrep version X.Y.Z\n")

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        return proc_grep.test.cleanup(self)
