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
    This test executes the .frm reader error conditions. The errors this test
    cannot test are the following:

      mysqlfrm.py   - running mysqlfrm as root
      read_frm.py   - spawned server failed
      frm_reader.py - byte-by-byte read errors
    """

    def check_prerequisites(self):
        if not self.servers.get_server(0).check_version_compat(5, 6, 11):
            raise MUTLibError("Test requires server version 5.6.11 and later.")
        return frm_reader_base.test.check_prerequisites(self)

    def setup(self):
        self.server0 = self.servers.get_server(0)
        self.frm_output = "frm_output.txt"
        self.s1_serverid = None

        index = self.servers.find_server_by_name("frm_test")
        if index >= 0:
            self.server1 = self.servers.get_server(index)
            try:
                res = self.server1.show_server_variable("server_id")
            except MUTLibError as err:
                raise MUTLibError(
                    "Cannot get frm test server server_id: {0}".format(
                        err.errmsg))
            self.s1_serverid = int(res[0][1])
        else:
            self.s1_serverid = self.servers.get_next_id()
            res = self.servers.spawn_new_server(
                self.server0, self.s1_serverid, "frm_test",
                ' --mysqld="--log-bin=mysql-bin "')
            if not res:
                raise MUTLibError("Cannot spawn frm_test server.")
            self.server1 = res[0]
            self.servers.add_new_server(self.server1, True)

        self.drop_all()

        return True

    def run(self):
        self.res_fname = "result.txt"

        if self.debug:
            print
        test_num = 1

        self.cmd = "mysqlfrm.py --server={0} ".format(
            self.build_connection_string(self.server1))

        comment = "Test case {0}: - Not path or files".format(test_num)
        res = self.run_test_case(2, self.cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        test_num += 1

        datadir = self.server1.show_server_variable("datadir")[0][1]
        frm_file_path = os.path.normpath("{0}/frm_test/orig.frm".format(
            datadir))
        comment = "Test case {0}: - Option --port required".format(test_num)
        res = self.run_test_case(2, self.cmd + frm_file_path, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        test_num += 1

        comment = "Test case {0}: - Option --port requires int".format(
            test_num)
        res = self.run_test_case(2, self.cmd + frm_file_path + " --port=NI",
                                 comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        test_num += 1

        comment = "Test case {0}: - No server and no access".format(test_num)
        res = self.run_test_case(1, "mysqlfrm.py {0} --port=3333".format(
            frm_file_path),  comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        test_num += 1

        comment = "Test case {0}: - Connection errors".format(test_num)
        res = self.run_test_case(2,
                                 "mysqlfrm.py --server=noone:2:2@local {0} "
                                 "--port=3333".format(frm_file_path),
                                 comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        test_num += 1

        comment = "Test case {0}: - Connection errors".format(test_num)
        cmd = " ".join(["mysqlfrm.py",
                        "--server=root:toor@localhost:"
                        "{0}".format(self.server0.port),
                        frm_file_path, "--port=3333"])
        res = self.run_test_case(2, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        test_num += 1

        comment = "Test case {0}: - Invalid port".format(test_num)
        res = self.run_test_case(2, "{0}{1} --port={2}".format(
            self.cmd, frm_file_path, self.server1.port),  comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        test_num += 1

        frm_file_path = os.path.normpath("./std_data/frm_files")
        cmd_str = " ".join(
            [self.cmd, "--port={0}".format(self.server0.port), frm_file_path])
        comment = "Test case {0}: - attempt to use existing port".format(
            test_num)
        res = self.run_test_case(1, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        self.mask_result("Error 2003:", "2003", "####")
        self.replace_result("Error ####: Can't connect to MySQL server",
                            "Error ####: Can't connect to MySQL server"
                            " on XXXXXXXXXXXXXXXXXXXX\n")
        self.replace_result("Error 1045",
                            "Error ####: Can't connect to MySQL server"
                            " on XXXXXXXXXXXXXXXXXXXX\n")
        self.replace_result("ERROR: Cannot read",
                            "ERROR: Cannot read XXXXXX\n")
        self.replace_result("#                  Mode :",
                            "#                  Mode : XXXXX\n")
        self.replace_result("#         MySQL Version :",
                            "#         MySQL Version : XXXXXXXX\n")
        self.replace_substring("{0}".format(self.server0.port), "XXXXX")

        # Must remove these lines because on Windows they are not printed
        # in the same order as other systems.
        self.remove_result("# Source on")

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        return frm_reader_base.test.cleanup(self)
