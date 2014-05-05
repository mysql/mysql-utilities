#
# Copyright (c) 2014 Oracle and/or its affiliates. All rights reserved.
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
server_info_errors_socket test.
"""

import os

import mutlib

from mysql.utilities.exception import MUTLibError


class test(mutlib.System_test):
    """check errors for serverinfo on posix systems.
    This test executes a series of error tests using a variety of
    parameters. It uses the server_info test as a parent for setup and teardown
    methods.
    """

    def check_prerequisites(self):
        if os.name != "posix":
            raise MUTLibError("Test requires a POSIX system.")
        return self.check_num_servers(1)

    def setup(self):
        return True

    def run(self):
        self.server1 = self.servers.get_server(0)
        self.res_fname = "result.txt"

        from_conn1 = "--server={0}".format(
            self.build_connection_string(self.server1))

        # BUG#18262507
        test_num = 1
        cmd_str = "mysqlserverinfo.py {0} ".format(from_conn1)
        cmd_opts = " --server=root@localhost:999999:/does/not/exist.mysql.sock"
        cmd = "{0} {1}".format(cmd_str, cmd_opts)
        comment = ("Test case {0} - Socket file does not "
                   "exist".format(test_num))
        res = self.run_test_case(1, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        self.results.append("\n")

        # BUG#18262507
        test_num += 1
        comment = ("Test case {0} - Socket file is not valid".format(test_num))
        # Create fake socket file
        try:
            open('fakesocket.sock', 'w').close()
        except:
            raise MUTLibError("{0}: failed. Unable to create fake socket "
                              "file".format(comment))
        cmd_opts = " --server=root@localhost:999999:fakesocket.sock"

        cmd = "{0} {1}".format(cmd_str, cmd_opts)
        res = self.run_test_case(1, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        self.results.append("\n")

        self.replace_result("ERROR: Server connection values invalid:",
                            "ERROR: Server connection values invalid\n")
        self.replace_substring_portion("ERROR: Unable to connect to server "
                                       "using socket", "Socket file",
                                       "ERROR: Unable to connect to server "
                                       "using socket XXXX. Socket file")
        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        try:
            os.remove("fakesocket.sock")
        except OSError:
            pass
        return True
