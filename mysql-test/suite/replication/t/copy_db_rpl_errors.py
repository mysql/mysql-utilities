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
copy_db_rpl_errors test.
"""

import export_rpl_errors
import mutlib

from mysql.utilities.exception import MUTLibError


class test(export_rpl_errors.test):
    """check replication errors for copy utility
    This test executes a series of copy database operations on a master and
    slave using a variety of replication options exercising the errors
    associated with the --rpl commands and processing. It uses the
    export_rpl_errors test for setup and tear down methods.
    """

    def check_prerequisites(self):
        if self.servers.get_server(0).check_version_compat(5, 6, 5):
            raise MUTLibError("Test requires server version prior to 5.6.5")
        return export_rpl_errors.test.check_prerequisites(self)

    def setup(self):
        return export_rpl_errors.test.setup(self)

    def run(self):
        self.res_fname = "result.txt"
        test_num = 1

        from_conn = "--source={0}".format(
            self.build_connection_string(self.server1))
        to_conn = "--destination={0}".format(
            self.build_connection_string(self.server2))

        cmd_str = "mysqldbcopy.py util_test {0} {1} ".format(from_conn,
                                                             to_conn)

        comment = "Test case {0} - error: --rpl=both".format(test_num)
        option = " --rpl=both "
        res = mutlib.System_test.run_test_case(self, 2, cmd_str + option,
                                               comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        test_num += 1

        self.server1.exec_query("CREATE USER imnotamouse@localhost")

        comment = "Test case {0} - warning: --rpl-user missing".format(
            test_num)
        option = " --rpl=master "
        res = mutlib.System_test.run_test_case(self, 1, cmd_str + option,
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
        self.server2.exec_query("STOP SLAVE")
        self.server2.exec_query("RESET SLAVE")

        comment = "Test case {0} - error: slave not connected".format(
            test_num)
        option = " --rpl=slave "
        res = mutlib.System_test.run_test_case(self, 1, cmd_str + option,
                                               comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        test_num += 1

        from_conn = "--server={0}".format(
            self.build_connection_string(self.server3))
        self.server3.exec_query("CREATE DATABASE util_test")

        cmd_str = ("mysqldbexport.py util_test --export=both "
                   "--rpl-user=rpl:rpl {0} ".format(from_conn))

        comment = "Test case {0} - error: no binlog".format(test_num)
        option = " --rpl=master "
        res = mutlib.System_test.run_test_case(self, 1, cmd_str + option,
                                               comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        self.replace_substring(str(self.server1.port), "PORT1")
        self.replace_substring(str(self.server2.port), "PORT2")

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        return export_rpl_errors.test.cleanup(self)
