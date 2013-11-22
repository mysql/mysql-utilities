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
import export_basic
from mysql.utilities.exception import MUTLibError, UtilError


class test(export_basic.test):
    """Export errors
    This test executes the export utility on a single server to exercise
    the error conditions.
    """

    def check_prerequisites(self):
        return export_basic.test.check_prerequisites(self)

    def setup(self):
        self.server1 = self.servers.get_server(0)
        self.server0 = self.servers.get_server(0)
        try:
            self.server1.exec_query("CREATE USER 'joe'@'localhost'")
        except UtilError as err:
            raise MUTLibError("ERROR: Unable to create USER 'joe'@'localhost':"
                              " {0}".format(err.errmsg))
        return export_basic.test.setup(self)

    def run(self):
        self.server1 = self.servers.get_server(0)
        self.res_fname = "result.txt"

        from_conn = "--server={0}".format(
            self.build_connection_string(self.server1))

        cmd = "mysqldbexport.py {0} util_test --skip-gtid ".format(from_conn)

        test_num = 1
        comment = "Test case {0} - bad --skip values".format(test_num)
        cmd = "{0} --skip=events,wiki-waki,woo-woo ".format(cmd)
        res = self.run_test_case(1, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - exporting data and skipping "
                   "data".format(test_num))
        cmd = "{0} --skip=data --export=data".format(cmd)
        res = self.run_test_case(1, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        cmd_str = "mysqldbexport.py {0} --skip-gtid ".format(from_conn)
        comment = "Test case {0} - no database specified".format(test_num)
        res = self.run_test_case(2, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        cmd_str = ("mysqldbexport.py --server=rocks_rocks_rocks "
                   "--skip-gtid util_test ")
        comment = "Test case {0} - cannot parse --server".format(test_num)
        res = self.run_test_case(2, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        cmd_str = ("mysqldbexport.py --skip-gtid --server=nope:nada@localhost:"
                   "{0} util_test".format(self.server0.port))
        comment = ("Test case {0} - error: cannot connect to "
                   "server".format(test_num))
        res = self.run_test_case(1, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Watchout for Windows: it doesn't use sockets!
        joe_conn = "--server=joe@localhost:{0}".format(self.server1.port)
        if os.name == "posix" and self.server1.socket is not None:
            joe_conn = "{0}:{1}".format(joe_conn, self.server1.socket)

        test_num += 1
        cmd_str = "mysqldbexport.py {0} util_test --skip-gtid ".format(
            joe_conn)
        comment = ("Test case {0} - error: not enough "
                   "privileges".format(test_num))
        res = self.run_test_case(1, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        cmd_str = "mysqldbexport.py {0} notthereatall --skip-gtid ".format(
            from_conn)
        comment = "Test case {0} - database does not exist".format(test_num)
        res = self.run_test_case(1, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        cmd_str = ("mysqldbexport.py {0} util_test --export=definitions"
                   " --skip-gtid ".format(joe_conn))
        comment = ("Test case {0} - error: not enough "
                   "privileges".format(test_num))
        res = self.run_test_case(1, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        cmd_str = "mysqldbexport.py {0} util_test --all --skip-gtid".format(
            from_conn)
        comment = "Test case {0} - error: db list and --all".format(test_num)
        res = self.run_test_case(2, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        cmd_str = ("mysqldbexport.py {0} --all "
                   "--character-set=unsupported_charset".format(from_conn))
        comment = "Test case 10 - invalid --character-set"
        res = self.run_test_case(1, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        self.replace_substring("1045 (28000)", "1045")

        self.replace_substring("on [::1]", "on localhost")

        self.remove_result("# WARNING: The server supports GTIDs")

        self.replace_result("mysqldbexport: error: Server connection "
                            "values invalid",
                            "mysqldbexport: error: Server connection "
                            "values invalid\n")

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        try:
            self.server1.exec_query("DROP USER 'joe'@'localhost'")
        except UtilError:
            pass
        return export_basic.test.cleanup(self)
