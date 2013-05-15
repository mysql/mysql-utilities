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
import sys
import frm_reader_base
from mysql.utilities.exception import MUTLibError, UtilDBError
from mysql.utilities.common.format import format_tabular_list

class test(frm_reader_base.test):
    """.frm file reader
    This test executes test cases to test the .frm reader in default mode.
    """

    def check_prerequisites(self):
        if not self.servers.get_server(0).check_version_compat(5, 6, 12):
            raise MUTLibError("Test requires server version 5.6.12 and later.")
        return frm_reader_base.test.check_prerequisites(self)

    def setup(self):
        return frm_reader_base.test.setup(self)

    def run(self):
        self.res_fname = "result.txt"

        if self.debug:
            print
        test_num = 1

        port = self.servers.get_next_port()
        self.cmd = "mysqlfrm.py --server=%s --port=%s " % \
                   (self.build_connection_string(self.server1), port)

        # Perform test of all .frm files in a known database folder
        datadir = self.server1.show_server_variable("datadir")[0][1]
        frm_file_path = os.path.normpath("%s/frm_test/" % datadir)
        comment = "Test case %s: - Check .frm files in a db folder" % test_num
        res = self.run_test_case(0, self.cmd + frm_file_path, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        test_num += 1

        # Perform test of all .frm files in a random folder
        frm_file_path = os.path.normpath("./std_data/frm_files")
        comment = "Test case %s: - Check .frm files in a db folder" % test_num
        res = self.run_test_case(0, self.cmd + frm_file_path, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
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

        comment = "Test case %s: - User the --user option" % test_num
        frm_file_path = os.path.join(frm_file_path, "t1.frm")
        cmd_str = " ".join([self.cmd, frm_file_path, "--user=%s" % user])
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        test_num += 1

        self.replace_result("# Starting the spawned server on port",
                            "# Starting the spawned server on port XXXXXXX\n")
        self.replace_result("# CREATE statement",
                            "# CREATE statement for [...]\n")
        self.replace_result("# std_data",
                            "# std_data/frm_files/t9.frm\n")

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        return frm_reader_base.test.cleanup(self)
