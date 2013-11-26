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
import shutil
import frm_reader_base
from mysql.utilities.exception import MUTLibError


NEW_FRM_DIR = ".{0}test_frm".format(os.sep)
FILES_READ = ['me.too.periods.frm', 't1.frm', 't2.frm', 't3.frm',
              't4.frm', 't5.frm', 't6.frm', 't7.frm', 't8.frm',
              'this.has.periods.frm']


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
        cmd = "mysqlfrm.py --server={0} --port={1} ".format(
            self.build_connection_string(self.server1), port)

        # Show the help
        comment = "Test case {0}: - Show help".format(test_num)
        res = self.run_test_case(0, "{0} --help".format(cmd), comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        test_num += 1

        # Perform test of all .frm files in a known database folder
        datadir = self.server1.show_server_variable("datadir")[0][1]
        frm_file_path = os.path.normpath("{0}/frm_test/".format(datadir))
        comment = ("Test case {0}: - Check .frm files in a "
                   "db folder".format(test_num))
        res = self.run_test_case(0, cmd + frm_file_path, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        test_num += 1

        # Perform test of all .frm files in a random folder
        frm_file_path = os.path.normpath("./std_data/frm_files")
        comment = ("Test case {0}: - Check .frm files in a db "
                   "folder".format(test_num))
        res = self.run_test_case(0, cmd + frm_file_path, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        test_num += 1

        # Export new .frm files with new storage engine specified.

        if os.path.exists(NEW_FRM_DIR):  # delete directory if it exists
            shutil.rmtree(NEW_FRM_DIR)
        os.mkdir(NEW_FRM_DIR)

        new_cmd = ("{0} --new-storage-engine=MEMORY --frmdir={1} "
                   "{2}".format(cmd, NEW_FRM_DIR, frm_file_path))
        comment = ("Test case {0}: - Export .frm files in a db "
                   "folder".format(test_num))
        res = self.run_test_case(0, new_cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        # Check to see that files were created
        files_found = os.listdir(NEW_FRM_DIR)
        files_found.sort()
        if not files_found == FILES_READ:
            raise MUTLibError("{0}: failed to create new "
                              ".frm_files".format(comment))
        try:
            for frm_file in files_found:
                os.unlink("{0}/{1}".format(NEW_FRM_DIR, frm_file))
            shutil.rmtree(NEW_FRM_DIR)
        except OSError:
            pass
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
        frm_file_path = os.path.join(frm_file_path, "t1.frm")
        cmd_str = " ".join([cmd, frm_file_path, "--user={0}".format(user),
                            "-v"])
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        self.replace_result("# Starting the spawned server on port",
                            "# Starting the spawned server on port XXXXXXX\n")
        self.replace_result("# CREATE statement",
                            "# CREATE statement for [...]\n")
        self.replace_result("# std_data", "# std_data/frm_files/t9.frm\n")
        self.replace_substring(user, "JOE_USER")
        self.replace_substring("# Copy of .frm file with new storage engine "
                               "saved as .\\test_frm\\",
                               "# Copy of .frm file with new storage engine "
                               "saved as ./test_frm/")

        # Mask version
        self.replace_result(
            "MySQL Utilities mysqlfrm version",
            "MySQL Utilities mysqlfrm version X.Y.Z "
            "(part of MySQL Workbench ... XXXXXX)\n"
        )

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        return frm_reader_base.test.cleanup(self)
