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
import export_basic
from mysql.utilities.exception import MUTLibError

class test(export_basic.test):
    """check export db skips
    This test executes a series of export database operations using a variety
    of skip oject parameters. It uses the export_basic test as a parent for
    setup and teardown methods.
    """

    def check_prerequisites(self):
        return export_basic.test.check_prerequisites(self)

    def setup(self):
        return export_basic.test.setup(self)

    def run(self):
        self.res_fname = "result.txt"

        from_conn = "--server=%s" % self.build_connection_string(self.server1)

        cmd_str = "mysqldbexport.py %s util_test --format=CSV " % from_conn + \
                  "--display=NAMES  --skip-gtid --skip=data"

        test_num = 1
        comment = "Test case %d - baseline" % test_num
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        _SKIPS=[",grants", ",events", ",functions", ",procedures",
                ",triggers", ",views", ",tables"]
        skip_str = ""
        for skip in _SKIPS:
            test_num += 1
            skip_str += skip
            cmd_opts = "%s%s" % (cmd_str, skip_str)
            comment = "Test case %d - no data,%s" % (test_num, skip_str)
            res = self.run_test_case(0, cmd_opts, comment)
            if not res:
                raise MUTLibError("%s: failed" % comment)

        self.remove_result("# WARNING: The server supports GTIDs")

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        return export_basic.test.cleanup(self)
