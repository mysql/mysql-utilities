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
compare_db_sql test.
"""

import compare_db

from mysql.utilities.exception import MUTLibError


class test(compare_db.test):
    """simple db diff
    This test executes a consistency check of two databases on
    separate servers generating transformation SQL statements. It uses the
    compare_db test as a base for all setup and teardown methods.
    """

    def check_prerequisites(self):
        return compare_db.test.check_prerequisites(self)

    def setup(self):
        return compare_db.test.setup(self)

    def run(self):
        self.server1 = self.servers.get_server(0)
        self.res_fname = "result.txt"

        s1_conn = "--server1=" + self.build_connection_string(self.server1)
        s2_conn = "--server2=" + self.build_connection_string(self.server2)

        cmd_str = "mysqldbcompare.py {0} {1} ".format(s1_conn, s2_conn)

        test_num = 1
        comment = ("Test case {0} - check a sample database generate "
                   "SQL".format(test_num))
        res = self.run_test_case(0, cmd_str + "inventory:inventory -a "
                                              "--difftype=sql", comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        self.alter_data()

        test_num += 1
        comment = ("Test case {0} - check database with known differences "
                   "generate SQL direction = server1 "
                   "(default)".format(test_num))
        res = self.run_test_case(1, cmd_str + "inventory:inventory -a "
                                              "--difftype=sql --format=CSV",
                                 comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - check database with known differences "
                   "generate SQL direction = server2".format(test_num))
        res = self.run_test_case(1, cmd_str + "inventory:inventory -a "
                                              "--difftype=sql --format=CSV "
                                              "--changes-for=server2", comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - check database with known differences "
                   "generate SQL direction = server1 with "
                   "reverse".format(test_num))
        res = self.run_test_case(1, cmd_str + "inventory:inventory -a "
                                              "--difftype=sql --format=CSV "
                                              "--changes-for=server1 "
                                              "--show-reverse",
                                 comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - check database with known differences "
                   "generate SQL direction = server2 with "
                   "reverse".format(test_num))
        res = self.run_test_case(1, cmd_str + "inventory:inventory -a "
                                              "--difftype=sql --format=CSV "
                                              "--changes-for=server2 "
                                              "--show-reverse",
                                 comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Test with data that yields the same span key (size 8).
        test_num += 1
        comment = ("Test case {0} - data with multiple lines per span "
                   "(no differences).".format(test_num))
        cmd_arg = 'multi_span_row:multi_span_row -a --difftype=sql'
        cmd = 'mysqldbcompare.py {0} {1} {2}'.format(s1_conn, s2_conn, cmd_arg)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Change data to detect all changed rows within the same span.
        self.server2.exec_query(
            'UPDATE multi_span_row.t SET data = 2 WHERE id != 1651723'
        )

        test_num += 1
        comment = ("Test case {0} - data with multiple lines per span "
                   "(changed rows).".format(test_num))
        cmd_arg = 'multi_span_row:multi_span_row -a --difftype=sql'
        cmd = 'mysqldbcompare.py {0} {1} {2}'.format(s1_conn, s2_conn, cmd_arg)
        res = self.run_test_case(1, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Change data to detect missing rows within the same span.
        self.server2.exec_query(
            'DELETE FROM multi_span_row.t WHERE id = 1908449'
        )

        test_num += 1
        comment = ("Test case {0} - data with multiple lines per span "
                   "(missing row).".format(test_num))
        cmd_arg = 'multi_span_row:multi_span_row -a --difftype=sql'
        cmd = 'mysqldbcompare.py {0} {1} {2}'.format(s1_conn, s2_conn, cmd_arg)
        res = self.run_test_case(1, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - data with multiple lines per span "
                   "(missing row; changes for server2).".format(test_num))
        cmd_arg = ('multi_span_row:multi_span_row -a --difftype=sql '
                   '--changes-for=server2')
        cmd = 'mysqldbcompare.py {0} {1} {2}'.format(s1_conn, s2_conn, cmd_arg)
        res = self.run_test_case(1, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        self.do_replacements()

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        return compare_db.test.cleanup(self)
