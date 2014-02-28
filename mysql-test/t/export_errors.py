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
        export_basic.test.setup(self)
        try:
            self.server1.exec_query("CREATE USER 'joe'@'localhost'")
            # Need to grant some privileges to joe on util_test to be able to
            # see the database, otherwise it is as it does not exist.
            self.server1.exec_query("GRANT ALL ON util_test.* TO "
                                    "'joe'@'localhost'")
            self.server1.exec_query("REVOKE SELECT ON util_test.* FROM "
                                    "'joe'@'localhost'")
        except UtilError as err:
            raise MUTLibError("Cannot create user joe'@'localhost' with "
                              "necessary privileges: {0}".format(err.errmsg))
        return True

    def run(self):
        self.res_fname = "result.txt"

        from_conn = "--server={0}".format(
            self.build_connection_string(self.server1)
        )

        cmd = "mysqldbexport.py {0} util_test --skip-gtid".format(from_conn)

        test_num = 1
        comment = "Test case {0} - bad --skip values".format(test_num)
        cmd_str = "{0} --skip=events,wiki-waki,woo-woo ".format(cmd)
        res = self.run_test_case(1, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - exporting data and skipping "
                   "data").format(test_num)
        cmd_str = "{0} --skip=data --export=data".format(cmd)
        res = self.run_test_case(1, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        cmd = "mysqldbexport.py {0} --skip-gtid".format(from_conn)

        test_num += 1
        comment = "Test case {0} - no database specified".format(test_num)
        res = self.run_test_case(2, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        cmd = "mysqldbexport.py util_test --skip-gtid"

        test_num += 1
        comment = "Test case {0} - cannot parse --server".format(test_num)
        cmd_str = "{0} --server=rocks_rocks_rocks".format(cmd)
        res = self.run_test_case(2, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - error: cannot connect to "
                   "server").format(test_num)
        cmd_str = ("{0} --server=nope:nada@localhost:"
                   "{1}").format(cmd, self.server1.port)
        res = self.run_test_case(1, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Watchout for Windows: it doesn't use sockets!
        joe_conn = "--server=joe@localhost:{0}".format(self.server1.port)
        if os.name == "posix" and self.server1.socket is not None:
            joe_conn = "{0}:{1}".format(joe_conn, self.server1.socket)

        test_num += 1
        comment = ("Test case {0} - error: not enough "
                   "privileges").format(test_num)
        cmd_str = "{0} {1}".format(cmd, joe_conn)
        res = self.run_test_case(1, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        cmd = "mysqldbexport.py --skip-gtid"

        test_num += 1
        comment = "Test case {0} - database does not exist".format(test_num)
        cmd_str = "{0} {1} notthereatall".format(cmd, from_conn)
        res = self.run_test_case(1, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        cmd = "mysqldbexport.py util_test --skip-gtid"

        test_num += 1
        comment = ("Test case {0} - error: not enough "
                   "privileges").format(test_num)
        cmd_str = "{0} {1} --export=definitions".format(cmd, joe_conn)
        res = self.run_test_case(1, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        cmd = "mysqldbexport.py {0} util_test --skip-gtid".format(from_conn)

        test_num += 1
        comment = "Test case {0} - error: db list and --all".format(test_num)
        cmd_str = "{0} --all".format(cmd)
        res = self.run_test_case(2, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = "Test case {0} - invalid --character-set".format(test_num)
        cmd_str = ("mysqldbexport.py {0} --all "
                   "--character-set=unsupported_charset".format(from_conn))
        res = self.run_test_case(1, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - error: invalid multiprocess "
                   "value.").format(test_num)
        cmd_str = "{0} --multiprocess=0.5".format(cmd)
        res = self.run_test_case(2, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - error: multiprocess value smaller than "
                   "zero.").format(test_num)
        cmd_str = "{0} --multiprocess=-1".format(cmd)
        res = self.run_test_case(2, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Mask non deterministic output.
        self.replace_substring("Error 1045 (28000):", "Error")

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
            pass  # Ignore DROP USER failure (user may not exist).
        return export_basic.test.cleanup(self)
