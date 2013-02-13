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
import replicate
import mutlib
from mysql.utilities.exception import MUTLibError

_RPL_FILE = "rpl_test.txt"
_RPL_OPTIONS = ["--comment-rpl", "--rpl-file=%s" % _RPL_FILE]

class test(replicate.test):
    """check --rpl parameter for export utility
    This test executes a series of export database operations on a single
    server using a variety of replication options. It uses the replicate test
    as a parent for setup and teardown methods.
    """

    def check_prerequisites(self):
        # Check MySQL server version - Must be 5.1.0 or higher
        if not self.servers.get_server(0).check_version_compat(5, 1, 0):
            raise MUTLibError("Test requires server version 5.1.0 or higher")
        self.check_gtid_unsafe()
        return replicate.test.check_prerequisites(self)

    def setup(self):
        self.res_fname = "result.txt"
        result = replicate.test.setup(self)
        if not result:
            return False
        
        master_str = "--master=%s" % self.build_connection_string(self.server1)
        slave_str = " --slave=%s" % self.build_connection_string(self.server2)
        conn_str = master_str + slave_str
        res = self.server2.exec_query("STOP SLAVE")
        res = self.server2.exec_query("RESET SLAVE")
        res = self.server1.exec_query("STOP SLAVE")
        res = self.server1.exec_query("RESET SLAVE")
        
        data_file = os.path.normpath("./std_data/basic_data.sql")
        try:
            res = self.server1.exec_query("DROP DATABASE IF EXISTS util_test")
            res = self.server2.exec_query("DROP DATABASE IF EXISTS util_test")
            res = self.server1.read_and_exec_SQL(data_file, self.debug)
            res = self.server2.read_and_exec_SQL(data_file, self.debug)
        except MUTLibError, e:
            raise MUTLibError("Failed to read commands from file %s: " % \
                               data_file + e.errmsg)

        cmd = "mysqlreplicate.py --rpl-user=rpl:rpl %s" % conn_str
        try:
            res = self.exec_util(cmd, self.res_fname)
        except MUTLibError, e:
            raise MUTLibError(e.errmsg)

        return True

    def run(self):
        from_conn = "--server=" + self.build_connection_string(self.server1)

        cmd_str = "mysqldbexport.py util_test --export=both " + \
                  "--skip=events,grants,procedures,functions,views " + \
                  "--rpl-user=rpl:rpl --rpl=master %s " % from_conn

        test_num = 1
        for rpl_opt in _RPL_OPTIONS:
            comment = "Test case %s : --rpl=master and %s" % \
                      (test_num, rpl_opt)
            cmd_opts = "%s" % rpl_opt
            res = mutlib.System_test.run_test_case(self, 0,
                                                   cmd_str + cmd_opts,
                                                   comment)
            if not res:
                raise MUTLibError("%s: failed" % comment)
            test_num += 1
        comment = "Test case %s : --rpl=master and %s" % \
                  (test_num, " ".join(_RPL_OPTIONS))
        cmd_opts = " %s" % " ".join(_RPL_OPTIONS)
        res = mutlib.System_test.run_test_case(self, 0, cmd_str + cmd_opts,
                                               comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        test_num += 1

        self.replace_result("CHANGE MASTER", "CHANGE MASTER <goes here>\n")
        self.replace_result("# CHANGE MASTER", "# CHANGE MASTER <goes here>\n")

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        try:
            os.unlink(_RPL_FILE)
        except:
            pass
        return replicate.test.cleanup(self)

