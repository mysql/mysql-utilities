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

import replicate
import mutlib
from mysql.utilities.exception import MUTLibError, UtilError

_RPL_OPTIONS = ["--rpl-file=test.txt", "--comment-rpl", "--rpl-user=root"]


class test(replicate.test):
    """check replication errors for export utility
    This test executes a series of export database operations on a single
    server using a variety of replication options exercising the errors
    associated with the --rpl commands and processing.
    """

    def check_prerequisites(self):
        # Check MySQL server version - Must be 5.1.0 or higher
        if not self.servers.get_server(0).check_version_compat(5, 1, 0):
            raise MUTLibError("Test requires server version 5.1.0 or higher")
        return replicate.test.check_prerequisites(self)

    def setup(self):
        result = replicate.test.setup(self)

        index = self.servers.find_server_by_name("new_server1")
        # If server exists, kill it
        if index >= 0:
            server = self.servers.get_server(index)
            self.servers.stop_server(server)
            self.servers.remove_server(server)

        self.s3_serverid = self.servers.get_next_id()
        res = self.servers.spawn_new_server(self.server0, self.s1_serverid,
                                            "new_server1")
        if not res:
            raise MUTLibError("Cannot spawn replication new server.")
        self.server3 = res[0]
        self.servers.add_new_server(self.server3, True)

        # Create util_test database to avoid not exist error.
        self.server1.exec_query("DROP DATABASE IF EXISTS util_test")
        self.server1.exec_query("CREATE DATABASE util_test")

        return result

    def run(self):
        self.res_fname = "result.txt"
        from_conn = "--server=" + self.build_connection_string(self.server1)

        test_num = 1
        # Check --rpl option errors
        for option in _RPL_OPTIONS:
            cmd_str = "mysqldbexport.py {0} util_test ".format(from_conn)
            comment = ("Test case {0} - error: {1} but no "
                       "--rpl".format(test_num, option))
            res = mutlib.System_test.run_test_case(self, 2, cmd_str + option,
                                                   comment)
            if not res:
                raise MUTLibError("{0}: failed".format(comment))
            test_num += 1

        all_options = " ".join(_RPL_OPTIONS)
        comment = ("Test case {0} - error: {1} but no "
                   "--rpl".format(test_num, all_options))
        res = mutlib.System_test.run_test_case(self, 2, cmd_str + all_options,
                                               comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        test_num += 1

        cmd_str = ("mysqldbexport.py util_test --export=both "
                   "--rpl-user=rpl:rpl {0} ".format(from_conn))

        comment = "Test case {0} - error: --rpl-file bad path".format(test_num)
        option = " --rpl=master --rpl-file=/bad/path/not/there.atall "
        res = mutlib.System_test.run_test_case(self, 1, cmd_str + option,
                                               comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        test_num += 1

        self.server1.exec_query("CREATE USER imnotamouse@localhost")

        cmd_str = "mysqldbexport.py util_test --export=data {0} ".format(
            from_conn)

        comment = "Test case {0} - warning: --rpl-user missing".format(
            test_num)
        option = " --rpl=master "
        res = mutlib.System_test.run_test_case(self, 0, cmd_str + option,
                                               comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        test_num += 1

        comment = "Test case {0} - error: --rpl-user missing user".format(
            test_num)
        option = " --rpl=master --rpl-user=missing "
        res = mutlib.System_test.run_test_case(self, 1, cmd_str + option,
                                               comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        test_num += 1

        comment = ("Test case {0} - error: --rpl-user missing "
                   "privileges".format(test_num))
        option = " --rpl=master --rpl-user=imnotamouse "
        res = mutlib.System_test.run_test_case(self, 1, cmd_str + option,
                                               comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        test_num += 1

        self.server1.exec_query("DROP USER imnotamouse@localhost")

        self.server1.exec_query("STOP SLAVE")
        self.server1.exec_query("RESET SLAVE")
        self.server2.exec_query("STOP SLAVE")
        self.server2.exec_query("RESET SLAVE")

        comment = "Test case {0} - error: slave not connected".format(test_num)
        option = " --rpl=slave "
        res = mutlib.System_test.run_test_case(self, 1, cmd_str + option,
                                               comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        test_num += 1

        from_conn = "--server=" + self.build_connection_string(self.server3)

        self.server3.exec_query("CREATE DATABASE util_test")
        cmd_str = ("mysqldbexport.py util_test --export=both "
                   "--rpl-user=rpl:rpl {0} ".format(from_conn))
        comment = "Test case {0} - error: no binlog".format(test_num)
        option = " --rpl=master "
        res = mutlib.System_test.run_test_case(self, 1, cmd_str + option,
                                               comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        self.replace_result("CHANGE MASTER", "CHANGE MASTER <goes here>\n")
        self.replace_result("# CHANGE MASTER", "# CHANGE MASTER <goes here>\n")
        self.replace_substring(str(self.server1.port), "PORT1")
        self.replace_substring(str(self.server2.port), "PORT2")

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        # Kill the servers that are only used in this test.
        kill_list = ['new_server1']
        return (replicate.test.cleanup(self)
                and self.kill_server_list(kill_list))
