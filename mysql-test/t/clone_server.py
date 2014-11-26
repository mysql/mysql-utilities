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
clone_server test.
"""

import os

import mutlib

from mysql.utilities.common.server import Server
from mysql.utilities.exception import UtilError, MUTLibError
from mutlib.ssl_certs import (CREATE_SSL_USER_2, SSL_CA, SSL_CERT, SSL_KEY,
                              SSL_OPTS_UTIL, STD_DATA_PATH, ssl_server_opts)


class test(mutlib.System_test):
    """clone server
    This test clones a server from a single server.
    """

    server0 = None
    new_server = None

    def check_prerequisites(self):
        return self.check_num_servers(1)

    def setup(self):
        # No setup needed
        return True

    @staticmethod
    def check_connect(port, name="cloned_server", conn_dict=None):
        """Check connection.

        port[in]    Server port.
        name[in]    Server name.
        """
        conn = {"user": "root", "passwd": "root", "host": "localhost",
                "port": port}

        if conn_dict is not None:
            conn.update(conn_dict)

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
        quote_char = "'" if os.name == "posix" else '"'
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
            port1, 'o' * o_path_size))
        cmd_str = ("{0}--new-data={2}{1}{2} "
                   "".format(cmd_str, full_datadir, quote_char))
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

        basedir = os.path.normpath(rows[0][1])
        port2 = int(self.servers.get_next_port())
        cmd_str = ("mysqlserverclone.py --root-password=root --delete-data "
                   "--new-port={0} --basedir={2}{1}{2} "
                   "".format(port2, basedir, quote_char))

        test_num += 1
        comment = ("Test case {0} - clone a server from "
                   "basedir".format(test_num))
        self.results.append(comment + "\n")
        full_datadir = os.path.join(os.getcwd(), "temp_{0}".format(port2))
        cmd_str = ("{0} --new-data={2}{1}{2} "
                   "".format(cmd_str, full_datadir, quote_char))

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

        # Test clone server option mysqld with SSL and basedir option
        # Also Used for next test, clone a running server with SSL
        test_num += 1
        comment = ("Test case {0} - clone a server from "
                   "basedir with SSL".format(test_num))
        self.results.append(comment + "\n")
        cmd_str = '{0} --mysqld="{1}"'.format(cmd_str, ssl_server_opts())
        res = self.exec_util(cmd_str, "start.txt")
        with open("start.txt") as f:
            for line in f:
                # Don't save lines that have [Warning]
                if "[Warning]" in line:
                    continue
                self.results.append(line)
        if res:
            raise MUTLibError("{0}: failed".format(comment))

        ssl_server = self.check_connect(port2, "cloned_server_basedir")
        ssl_server.exec_query(CREATE_SSL_USER_2)

        test_num += 1
        comment = ("Test case {0} - clone a running server with SSL "
                   "and using spaces in the path".format(test_num))
        port3 = int(self.servers.get_next_port())
        self.results.append(comment + "\n")
        full_datadir = os.path.join(os.getcwd(), "temp with spaces "
                                                 "{0}".format(port3))
        cmd_str = ("mysqlserverclone.py --server={0} --delete-data "
                   ).format(self.build_custom_connection_string(ssl_server,
                                                                "root_ssl",
                                                                "root_ssl"))
        cmd_str = ("{0} --new-data={2}{1}{2} "
                   "".format(cmd_str, full_datadir, quote_char))
        cmd_str = ('{0} {1} --new-port={2} --root-password=root --mysqld='
                   '"{3}"').format(cmd_str,
                                   SSL_OPTS_UTIL.format(STD_DATA_PATH),
                                   port3,
                                   ssl_server_opts())
        res = self.exec_util(cmd_str, "start.txt")
        with open("start.txt") as f:
            for line in f:
                # Don't save lines that have [Warning]
                if "[Warning]" in line:
                    continue
                self.results.append(line)
        if res:
            raise MUTLibError("{0}: failed".format(comment))

        new_server = self.check_connect(port3)
        new_server.exec_query(CREATE_SSL_USER_2)

        conn_ssl = {
            "user": "root_ssl",
            "passwd": "root_ssl",
            "ssl_cert": SSL_CERT.format(STD_DATA_PATH),
            "ssl_ca": SSL_CA.format(STD_DATA_PATH),
            "ssl_key": SSL_KEY.format(STD_DATA_PATH),
        }

        new_server_ssl = self.check_connect(port3, conn_dict=conn_ssl)

        self.servers.stop_server(ssl_server)
        self.servers.clear_last_port()

        self.servers.stop_server(new_server_ssl)
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
