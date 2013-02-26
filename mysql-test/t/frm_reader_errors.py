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
        self.drop_all()
        self.frm_output = "frm_output.txt"
        self.s1_serverid = None

        index = self.servers.find_server_by_name("frm_test")
        if index >= 0:
            self.server1 = self.servers.get_server(index)
            try:
                res = self.server1.show_server_variable("server_id")
            except MUTLibError as err:
                raise MUTLibError("Cannot get frm test server " +
                                   "server_id: %s" % err.errmsg)
            self.s1_serverid = int(res[0][1])
        else:
            self.s1_serverid = self.servers.get_next_id()
            res = self.servers.spawn_new_server(self.server0, self.s1_serverid,
                                               "frm_test", ' --mysqld='
                                                '"--log-bin=mysql-bin "')
            if not res:
                raise MUTLibError("Cannot spawn frm_test server.")
            self.server1 = res[0]
            self.servers.add_new_server(self.server1, True)

        return True

    def run(self):
        self.res_fname = "result.txt"

        if self.debug:
            print
        test_num = 1

        self.cmd = "mysqlfrm.py --server=%s " % \
                   self.build_connection_string(self.server1)

        comment = "Test case %s: - Not path or files" % test_num
        res = self.run_test_case(2, self.cmd, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        test_num += 1

        datadir = self.server1.show_server_variable("datadir")[0][1]
        frm_file_path = os.path.normpath("%s/frm_test/orig.frm" % datadir)
        comment = "Test case %s: - Option --port required" % test_num
        res = self.run_test_case(2, self.cmd + frm_file_path, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        test_num += 1

        comment = "Test case %s: - Option --port requires int" % test_num
        res = self.run_test_case(2, self.cmd + frm_file_path + " --port=NI",
                                 comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        test_num += 1

        comment = "Test case %s: - No server and no access" % test_num
        res = self.run_test_case(1, "mysqlfrm.py " + frm_file_path +
                                 " --port=3333", comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        test_num += 1

        comment = "Test case %s: - Connection errors" % test_num
        res = self.run_test_case(2, "mysqlfrm.py --server=noone:2:2@local " +
                                 frm_file_path + " --port=3333", comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        test_num += 1

        comment = "Test case %s: - Connection errors" % test_num
        res = self.run_test_case(2, "mysqlfrm.py --server=XXXX@localhost " +
                                 frm_file_path + " --port=3333", comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        test_num += 1

        comment = "Test case %s: - Invalid port" % test_num
        res = self.run_test_case(2, self.cmd + frm_file_path +
                                 " --port=%s" % self.server1.port,
                                 comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        test_num += 1

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

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        return frm_reader_base.test.cleanup(self)
