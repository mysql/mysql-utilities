#
# Copyright (c) 2010, 2013, Oracle and/or its affiliates. All rights reserved.
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
    """clone server parameters
    This test exercises the parameters for mysqlserverclone
    """

    def check_prerequisites(self):
        return self.check_num_servers(1)

    def setup(self):
        # No setup needed
        self.new_server = None
        return True

    def _test_server_clone(self, cmd_str, comment, kill=True,
                           capture_all=False):
        self.results.append(comment + "\n")
        port1 = int(self.servers.get_next_port())
        cmd_str = "{0} --new-port={1} ".format(cmd_str, port1)
        full_datadir = os.path.join(os.getcwd(), "temp_{0}".format(port1))
        cmd_str = "{0} --new-data={1} --delete ".format(cmd_str, full_datadir)
        res = self.exec_util(cmd_str, "start.txt")
        with open("start.txt") as f:
            for line in f:
                # Don't save lines that have [Warning] or don't start with #
                index = line.find("[Warning]")
                if capture_all or (index <= 0 and line[0] == '#'):
                    self.results.append(line)
        if res:
            raise MUTLibError("{0}: failed".format(comment))

        # Create a new instance
        conn = {"user": "root", "passwd": "root", "host": "localhost",
                "port": port1, "unix_socket": full_datadir + "/mysql.sock"}
        if os.name != "posix":
            conn["unix_socket"] = None

        server_options = {'conn_info': conn, 'role': "cloned_server_2", }
        self.new_server = Server(server_options)
        if self.new_server is None:
            return False

        if kill:
            # Connect to the new instance
            try:
                self.new_server.connect()
            except UtilError:
                self.new_server = None
                raise MUTLibError("Cannot connect to spawned server.")
            self.servers.stop_server(self.new_server)

        return True

    def run(self):
        self.res_fname = "result.txt"
        base_cmd = ("mysqlserverclone.py --server={0} "
                    "--root-password=root ".format(
                        self.build_connection_string(
                            self.servers.get_server(0))))

        #  (comment, command options, kill running server)
        test_cases = [("show help", " --help ", False, True), (
            "write command to file", " --write-command=startme.sh ", True,
            False), ("write command to file shortcut", " -w startme.sh ", True,
                     False), ("verbosity = -v", " -v ", True, False),
            ("verbosity = -vv", " -vv ", True, False),
            ("verbosity = -vvv", " -vvv ", True, False),
            ("-vvv and write command to file shortcut", " -vvv -w startme.sh ",
                True, False),
        ]

        test_num = 1
        for row in test_cases:
            new_comment = "Test case {0} : {1}".format(test_num, row[0])
            if not self._test_server_clone(base_cmd + row[1], new_comment,
                                           row[2], row[3]):
                raise MUTLibError("{0}: failed".format(new_comment))
            test_num += 1

        # Perform a test using the --user option for the current user
        user = None
        try:
            user = os.environ['USERNAME']
        except KeyError:
            user = os.environ['LOGNAME']
        finally:
            if not user:
                raise MUTLibError("Cannot obtain user name for test case.")

        comment = "Test case {0}: - User the --user option".format(test_num)
        if not self._test_server_clone("{0}--user={1}".format(base_cmd, user),
                                       comment, True, False):
            raise MUTLibError("{0}: failed".format(comment))
        test_num += 1

        self.replace_result("#  -uroot", "#  -uroot [...]\n")
        self.replace_result("#                       mysqld:",
                            "#                       mysqld: XXXXXXXXXXXX\n")
        self.replace_result("#                   mysqladmin:",
                            "#                   mysqladmin: XXXXXXXXXXXX\n")
        self.replace_result("#      mysql_system_tables.sql:",
                            "#      mysql_system_tables.sql: XXXXXXXXXXXX\n")
        self.replace_result("# mysql_system_tables_data.sql:",
                            "# mysql_system_tables_data.sql: XXXXXXXXXXXX\n")
        self.replace_result("# mysql_test_data_timezone.sql:",
                            "# mysql_test_data_timezone.sql: XXXXXXXXXXXX\n")
        self.replace_result("#         fill_help_tables.sql:",
                            "#         fill_help_tables.sql: XXXXXXXXXXXX\n")

        self.replace_result("# Cloning the MySQL server running on ",
                            "# Cloning the MySQL server running on "
                            "XXXXX-XXXXX.\n")

        self.remove_result("# trying again...")

        # Remove version information
        self.remove_result_and_lines_after("MySQL Utilities "
                                           "mysqlserverclone version", 6)

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def _remove_file(self, filename):
        try:
            os.unlink(filename)
        except OSError:
            pass

    def cleanup(self):
        files = [self.res_fname, "start.txt", "startme.sh"]
        for file_ in files:
            self._remove_file(file_)
        return True
