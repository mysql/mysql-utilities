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
import os
import mutlib

from mysql.utilities.common.server import Server
from mysql.utilities.exception import UtilError, MUTLibError


class test(mutlib.System_test):
    """clone server
    This test clones a server from a single server.
    """

    def check_prerequisites(self):
        return self.check_num_servers(1)

    def setup(self):
        # No setup needed
        self.new_server = None
        return True

    @staticmethod
    def check_connect(port, name="cloned_server"):
        new_server = None

        conn = {"user": "root", "passwd": "root", "host": "127.0.0.1",
                "port": port}

        server_options = {'conn_info': conn, 'role': name, }
        new_server = Server(server_options)
        if new_server is None:
            return None

        # Connect to the new instance
        try:
            new_server.connect()
        except UtilError as err:
            raise MUTLibError("Cannot connect to spawned server: {0}".format(
                err.errmsg))

        return new_server

    def run(self):
        self.server0 = self.servers.get_server(0)
        cmd_str = "mysqlserverclone.py --server={0} --delete-data ".format(
            self.build_connection_string(self.server0))

        port1 = self.servers.get_next_port()
        cmd_str = "{0} --new-port={1} --root-password=root ".format(cmd_str,
                                                                    port1)
        test_num = 1
        comment = "Test case {0} - clone a running server".format(test_num)
        self.results.append(comment + "\n")
        # Create a new-dir whose size with socket file is > 107 chars
        o_path_size = 108 - (len(os.getcwd()) + 22 + len(str(port1)))
        full_datadir = os.path.join(os.getcwd(), "temp_{0}_lo{1}ng".format(
            port1, 'o'*o_path_size))
        cmd_str = "{0}--new-data={1} ".format(cmd_str, full_datadir)
        res = self.exec_util(cmd_str, "start.txt")
        with open("start.txt") as f:
            for line in f:
                # Don't save lines that have [Warning]
                if "[Warning]" in line:
                    continue
                self.results.append(line)
        if res:
            raise MUTLibError("{0}: failed".format(comment))

        self.new_server = self.check_connect(port1)

        # Get basedir
        rows = self.server0.exec_query("SHOW VARIABLES LIKE 'basedir'")
        if not rows:
            raise UtilError("Unable to determine basedir of running server.")

        basedir = rows[0][1]
        port2 = int(self.servers.get_next_port())
        cmd_str = ("mysqlserverclone.py --root-password=root --delete-data "
                   "--new-port={0} --basedir={1} ".format(port2, basedir))

        test_num += 1
        comment = ("Test case {0} - clone a server from "
                   "basedir".format(test_num))
        self.results.append(comment + "\n")
        full_datadir = os.path.join(os.getcwd(), "temp_{0}".format(port2))
        cmd_str = "{0}--new-data={1} ".format(cmd_str, full_datadir)
        res = self.exec_util(cmd_str, "start.txt")
        with open("start.txt") as f:
            for line in f:
                # Don't save lines that have [Warning]
                if "[Warning]" in line:
                    continue
                self.results.append(line)
        if res:
            raise MUTLibError("{0}: failed".format(comment))

        server = self.check_connect(port2, "cloned_server_basedir")

        self.servers.stop_server(server)
        self.servers.clear_last_port()

        self.replace_result("# Cloning the MySQL server running on",
                            "# Cloning the MySQL server running on xxxxx-"
                            "xxxxx.\n")

        self.replace_result("#  -uroot", "#  -uroot [...]\n")
        self.replace_result("# Cloning the MySQL server located at",
                            "# Cloning the MySQL server located at XXXX\n")
        # Since it may or may not appear, depending on size of path or Windows,
        # remove it
        self.remove_result("# WARNING: The socket file path '")

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        is_clean = True
        if self.new_server:  # Add server to server list and then kill it
            self.servers.add_new_server(self.new_server, True)
            is_clean = self.kill_server('cloned_server')
        else:
            self.servers.clear_last_port()
        try:
            os.unlink("start.txt")
        except OSError:
            pass

        return is_clean
