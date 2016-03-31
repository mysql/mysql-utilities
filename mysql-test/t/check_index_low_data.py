#
# Copyright (c) 2014, Oracle and/or its affiliates. All rights reserved.
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
check_index_low_data test.
"""

import check_index_parameters

from mysql.utilities.exception import MUTLibError

TEST_TABLE = ("CREATE TABLE util_test_a.test_low ("
              "number mediumint(9) NOT NULL,"
              " str_text varchar(64) NOT NULL,"
              " PRIMARY KEY (number),"
              " KEY str_text (str_text)"
              ") ENGINE=InnoDB DEFAULT CHARSET=utf8;")
INSERT_ROWS1 = ("INSERT INTO util_test_a.test_low (number,str_text) "
                "VALUES (1,'a'),(2,'b'),(3,'c'),(4,'a')")
INSERT_ROWS2 = ("INSERT INTO util_test_a.test_low (number,str_text) "
                "SELECT number+4,str_text from util_test_a.test_low")
INSERT_ROWS3 = ("INSERT INTO util_test_a.test_low (number,str_text) "
                "SELECT number+10,str_text from util_test_a.test_low")


class test(check_index_parameters.test):
    """check for best and worst indexes with low data
    This test executes the check index utility parameters on a single server.
    It uses the check_index_parameters test as a parent for setup and
    teardown methods.
    """

    test_num = 1

    def check_prerequisites(self):
        res = check_index_parameters.test.check_prerequisites(self)
        self.test_num = 1
        self.res_fname = "result.txt"
        return res

    def setup(self):
        if not check_index_parameters.test.setup(self):
            return False
        self.server1.exec_query(TEST_TABLE)
        return True

    def run_test_cases(self):
        """Run test cases.
        """
        from_conn = "--server=" + self.build_connection_string(self.server1)
        cmd_str = ("mysqlindexcheck.py {0} util_test_a.test_low "
                   "--stats -v --format=vertical ".format(from_conn))

        comment = ("Test case {0} - best indexes - "
                   "low data".format(self.test_num))
        res = self.run_test_case(0, cmd_str + "--best=5", comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        self.test_num += 1

        comment = ("Test case {0} - worst indexes - "
                   "low data".format(self.test_num))
        res = self.run_test_case(0, cmd_str + "--worst=5", comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        self.test_num += 1

        return True

    def run(self):

        # Start with empty table
        self.run_test_cases()

        # Add some data
        self.server1.exec_query(INSERT_ROWS1)
        self.run_test_cases()

        # Add some more data
        self.server1.exec_query(INSERT_ROWS2)
        self.run_test_cases()

        # Add some more data
        self.server1.exec_query(INSERT_ROWS3)
        self.run_test_cases()

        # Mask results
        if self.servers.get_server(0).check_version_compat(5, 7, 9):
            self.replace_substring("cardinality: 3", "cardinality: XX")
            self.replace_substring("percent: 18.75", "percent: XXX.XX")
        elif self.servers.get_server(0).check_version_compat(5, 7, 5):
            self.replace_substring("cardinality: 12", "cardinality: XX")
            self.replace_substring("percent: 75.00", "percent: XXX.XX")
        else:
            self.replace_substring("cardinality: 16", "cardinality: XX")
            self.replace_substring("percent: 100.00", "percent: XXX.XX")

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        return check_index_parameters.test.cleanup(self)
