#
# Copyright (c) 2016, Oracle and/or its affiliates. All rights reserved.
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
grants_show test.
"""
import os

import show_grants

from mysql.utilities.exception import MUTLibError


_DEFAULT_MYSQL_OPTS = ('"--report-host=localhost --report-port={0} '
                       '--bind-address=:: --sql-mode=ANSI_QUOTES"')


class test(show_grants.test):
    """Test mysqlgrants basic usage with a server with sql_mode=ANSI_QUOTES.

    This test runs the mysqlgrants utility to test its features.
    Server with sql_mode=ANSI_QUOTES
    """
    server1 = None
    need_server = False

    def setup(self):
        mysqld = _DEFAULT_MYSQL_OPTS.format(self.servers.view_next_port())
        self.server1 = self.servers.spawn_server("show_grants_srv_ansi_quotes",
                                                 mysqld, True)
        data_files = ["./std_data/basic_data_ansi_quotes.sql",
                      "./std_data/backtick_data_ansi_quotes.sql"]
        show_grants.test.setup(self, spawn_servers=False,
                               data_files=data_files)

        if self.server1.select_variable("SQL_MODE") != "ANSI_QUOTES":
            raise MUTLibError("Failed to set SQL_MODE=ANSI_QUOTES to server"
                              " {0}:{1}".format(self.server1.host,
                                                self.server1.port))
        return True

    def run(self):
        cmd_base = 'mysqlgrants.py --server={0}'.format(
            self.build_connection_string(self.server1))

        test_num = 1
        comment = ("Test case {0} - Privileges are inherited from global "
                   "level to db level  and from db level to tables and "
                   "routines".format(test_num))
        cmd = ("{0} util_test util_test.t3 util_test.t2 util_test.p1 "
               "util_test.f1".format(cmd_base))
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - show grantees, using all types of objects:"
                   " tables, databases and stored routines".format(test_num))
        if os.name == 'posix':
            cmd_arg = ("'\"db`:db\"' '\"db`:db\".\"`t`.`export_2\"' "
                       "'\"db`:db\".\"fu`nc\"' '\"db`:db\".\"pr``oc\"' ")
        else:
            cmd_arg = (
                '"\\"db`:db\\"" "\\"db`:db\\".\\"`t`.`export_2\\"" '
                '"\\"db`:db\\".\\"fu`nc\\"" "\\"db`:db\\".\\"pr``oc\\"" '
            )

        cmd = ("{0} util_test util_test.t1 util_test.t2 "
               "util_test.does_not_exist util_test.v1 db_does_not_exist "
               "util_test.t3 {1}".format(cmd_base, cmd_arg))
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - show grants for all objects of a "
                   "database using wildcard".format(test_num))
        cmd = "{0} util_test.* ".format(cmd_base,)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # mask non deterministic output
        self.do_masks()

        return True

    def do_masks(self):
        """Masks non deterministic output.
        """
        self.replace_substring(str(self.server1.port), "PORT1")
        self.remove_result("# - 'root'@'")

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        kill_list = ["show_grants_srv_ansi_quotes"]
        return (show_grants.test.cleanup(self)
                and self.kill_server_list(kill_list))
