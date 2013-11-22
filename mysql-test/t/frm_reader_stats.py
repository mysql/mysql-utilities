#
# Copyright (c) 2013, Oracle and/or its affiliates. All rights reserved.
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
import frm_reader_base
from mysql.utilities.exception import MUTLibError


class test(frm_reader_base.test):
    """.frm file reader
    This test executes test cases to test the .frm reader in diagnostic mode
    showing statistics.
    """

    def check_prerequisites(self):
        if not self.servers.get_server(0).check_version_compat(5, 6, 11):
            raise MUTLibError("Test requires server version 5.6.11 and later.")
        return frm_reader_base.test.check_prerequisites(self)

    def setup(self):
        return frm_reader_base.test.setup(self)

    def run(self):
        self.res_fname = "result.txt"

        if self.debug:
            print
        test_num = 1

        self.cmd = ("mysqlfrm.py --server={0} --diagnostic --show-stats "
                    "".format(self.build_connection_string(self.server1)))

        # Perform test of all .frm files in a known file
        datadir = self.server1.show_server_variable("datadir")[0][1]
        frm_file_path = os.path.normpath("{0}/frm_test/orig.frm".format(
            datadir))
        comment = "Test case {0}: - Check .frm files in a db folder".format(
            test_num)
        res = self.run_test_case(0, self.cmd + frm_file_path, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        test_num += 1

        # Perform test of all .frm files in a random folder
        frm_file_path = os.path.normpath("./std_data/frm_files")
        comment = "Test case {0}: - Check .frm files in a db folder".format(
            test_num)
        res = self.run_test_case(0, self.cmd + frm_file_path, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        self.replace_result("#         Last Modified :",
                            "#         Last Modified : XXXXXXXXXXXXXXXXX\n")
        self.replace_result("#         Creation Time :",
                            "#         Creation Time : XXXXXXXXXXXXXXXXX\n")
        self.replace_result("#         Last Accessed :",
                            "#         Last Accessed : XXXXXXXXXXXXXXXXX\n")
        self.replace_result("#                  Mode :",
                            "#                  Mode : XXXXX\n")
        self.replace_result("# CREATE statement",
                            "# CREATE statement for [...]\n")
        self.replace_result("# Reading .frm file",
                            "# Reading .frm file XXXXXXX\n")
        self.replace_result("#         MySQL Version :",
                            "#         MySQL Version : XXXXXXXX\n")

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        return frm_reader_base.test.cleanup(self)
