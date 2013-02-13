#
# Copyright (c) 2010, 2013, Oracle and/or its affiliates. All rights reserved.
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
import diskusage_basic
from mysql.utilities.exception import MUTLibError

class test(diskusage_basic.test):
    """Disk usage parameters
    This test executes the disk space utility
    on a single server using a variety of parameters.
    It uses the diskusage_basic test for setup and teardown methods.
    """

    def check_prerequisites(self):
        if self.servers.get_server(0).check_version_compat(5, 6, 2):
            raise MUTLibError("Test requires server version prior to 5.6.2")
        return diskusage_basic.test.check_prerequisites(self)

    def setup(self):
        return diskusage_basic.test.setup(self)

    def run(self):
        self.res_fname = "result.txt"

        from_conn = "--server=%s" % self.build_connection_string(self.server1)

        cmd_base = "mysqldiskusage.py %s util_test --format=csv" % from_conn
        test_num = 1
        comment = "Test Case %d : Showing help " % test_num
        cmd_opts = " --help"
        res = self.run_test_case(0, cmd_base+cmd_opts, comment)
        if not res:
            raise MUTLibError("DISKUSAGE: %s: failed" % comment)
        self.results.append("\n")
        test_num += 1

        # no headers - only works when format != GRID
        comment = "Test Case %d : No headers " % test_num
        cmd_opts = " --no-headers "
        res = self.run_test_case(0, cmd_base+cmd_opts, comment)
        if not res:
            raise MUTLibError("DISKUSAGE: %s: failed" % comment)
        self.results.append("\n")
        test_num += 1

        # binlog
        comment = "Test Case %d : Show binlog usage " % test_num
        cmd_opts = " --binlog"
        res = self.run_test_case(0, cmd_base+cmd_opts, comment)
        if not res:
            raise MUTLibError("DISKUSAGE: %s: failed" % comment)
        self.results.append("\n")
        test_num += 1

        # logs
        comment = "Test Case %d : Show log usage " % test_num
        cmd_opts = " --logs"
        res = self.run_test_case(0, cmd_base+cmd_opts, comment)
        if not res:
            raise MUTLibError("DISKUSAGE: %s: failed" % comment)
        self.results.append("\n")
        test_num += 1

        try:
            res = self.server1.show_server_variable('datadir')
            if res == []:
                raise MUTLibError("DISKUSAGE: Cannot get datadir.")
            datadir = res[0][1]
            os.mkdir(os.path.join(datadir, 'mt_db'))
        except:
            raise MUTLibError("DISKUSAGE: Can't test empty db.")

        # InnoDB
        comment = "Test Case %d : Show InnoDB usage " % test_num
        cmd_opts = " --innodb"
        res = self.run_test_case(0, cmd_base+cmd_opts, comment)
        if not res:
            raise MUTLibError("DISKUSAGE: %s: failed" % comment)
        self.results.append("\n")
        test_num += 1

        # empty dbs
        comment = "Test Case %d : Include empty database " % test_num
        cmd_opts = " --empty mt_db"
        res = self.run_test_case(0, cmd_base+cmd_opts, comment)
        if not res:
            raise MUTLibError("DISKUSAGE: %s: failed" % comment)
        self.results.append("\n")
        test_num += 1

        # all
        comment = "Test Case %d : Show all usage " % test_num
        cmd_base = "mysqldiskusage.py %s --format=csv" % from_conn
        cmd_opts = " --all"
        res = self.run_test_case(0, cmd_base+cmd_opts, comment)
        if not res:
            raise MUTLibError("DISKUSAGE: %s: failed" % comment)
        self.results.append("\n")
        test_num += 1

        # verbose with all
        comment = "Test Case %d : Show all plus verbose " % test_num
        cmd_opts = " -lambi -vv"
        res = self.run_test_case(0, cmd_base+cmd_opts, comment)
        if not res:
            raise MUTLibError("DISKUSAGE: %s: failed" % comment)
        self.results.append("\n")
        test_num += 1

        # quiet with all
        comment = "Test Case %d : Show all plus quiet " % test_num
        cmd_opts = " -lambi --quiet"
        res = self.run_test_case(0, cmd_base+cmd_opts, comment)
        if not res:
            raise MUTLibError("DISKUSAGE: %s: failed" % comment)
        self.results.append("\n")
        test_num += 1

        diskusage_basic.test.mask(self)

        self.mask_column_result("mysql,", ",", 2, "XXXXXXX")
        self.mask_column_result("util_test", ",", 2, "XXXXXXX")
        self.mask_column_result("mysql,X", ",", 3, "XXXXXXX")
        self.mask_column_result("util_test,X", ",", 3, "XXXXXXX")
        self.mask_column_result("mysql,X", ",", 4, "XXXXXXX")
        self.mask_column_result("util_test,X", ",", 4, "XXXXXXX")
        self.mask_column_result("mysql,X", ",", 5, "XXXXXXX")
        self.mask_column_result("util_test,X", ",", 5, "XXXXXXX")

        self.replace_result("error_log.err", "error_log.err,XXXX\n")

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        return diskusage_basic.test.cleanup(self)
