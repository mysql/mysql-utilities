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
import check_rpl
import mutlib
from mysql.utilities.exception import MUTLibError

class test(check_rpl.test):
    """check replication conditions
    This test runs the mysqlrplcheck utility on a known master-slave topology
    to test various parameters. It uses the check_rpl test as a parent for
    setup and teardown methods.
    """

    def check_prerequisites(self):
        return check_rpl.test.check_prerequisites(self)

    def setup(self):
        res = check_rpl.test.setup(self)
        index = self.servers.find_server_by_name("rep_slave_ignore")
        if index >= 0:
            self.server3 = self.servers.get_server(index)
            try:
                res = self.server3.show_server_variable("server_id")
            except MUTLibError, e:
                raise MUTLibError("Cannot get replication slave " +
                                   "server_id: %s" % e.errmsg)
            self.s3_serverid = int(res[0][1])
        else:
            self.s3_serverid = self.servers.get_next_id()
            res = self.servers.spawn_new_server(self.server0, self.s3_serverid,
                                               "rep_slave_ignore", ' --mysqld='
                                                '"--log-bin=mysql-bin '
                                                '--replicate-ignore-db=t123"')
            if not res:
                raise MUTLibError("Cannot spawn replication slave server.")
            self.server3 = res[0]
            self.servers.add_new_server(self.server3, True)
        return res

    def run(self):
        self.res_fname = "result.txt"

        master_str = "--master=%s" % self.build_connection_string(self.server2)
        slave_str = " --slave=%s" % self.build_connection_string(self.server1)
        slave_ignore_str = " --slave=%s" % \
                           self.build_connection_string(self.server3)
        conn_str = master_str + slave_str
        
        cmd = "mysqlreplicate.py --rpl-user=rpl:rpl %s" % conn_str
        try:
            res = self.exec_util(cmd, self.res_fname)
        except MUTLibError, e:
            raise MUTLibError(e.errmsg)

        cmd_str = "mysqlrplcheck.py " + conn_str

        comment = "Test case 1 - show help"
        cmd_opts = " --help"
        res = mutlib.System_test.run_test_case(self, 0, cmd_str+cmd_opts,
                                                   comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
            
        comment = "Test case 2 - master_info"
        cmd_opts = " --master-info=m.info -v"
        res = mutlib.System_test.run_test_case(self, 1, cmd_str+cmd_opts,
                                                   comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
            
        comment = "Test case 3 - width"
        cmd_opts = " --width=65"
        res = mutlib.System_test.run_test_case(self, 0, cmd_str+cmd_opts,
                                                   comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        comment = "Test case 4 - quiet"
        cmd_opts = " --quiet"
        res = mutlib.System_test.run_test_case(self, 0, cmd_str+cmd_opts,
                                                   comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        comment = "Test case 5 - test failure with quiet"
        cmd_opts = " --master-info=m.info --quiet"
        res = mutlib.System_test.run_test_case(self, 1, cmd_str+cmd_opts,
                                                   comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
            
        # Now show how quiet performs with warning and suppress
        
        conn_str = master_str + slave_ignore_str
        cmd_str = "mysqlrplcheck.py " + conn_str
        
        cmd = "mysqlreplicate.py --rpl-user=rpl:rpl %s" % conn_str
        try:
            res = self.exec_util(cmd, self.res_fname)
        except MUTLibError, e:
            raise MUTLibError(e.errmsg)

        comment = "Test case 6 - test warning without quiet"
        cmd_opts = " "
        res = mutlib.System_test.run_test_case(self, 1, cmd_str+cmd_opts,
                                                   comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        comment = "Test case 7 - test warning with quiet"
        cmd_opts = " --quiet"
        res = mutlib.System_test.run_test_case(self, 1, cmd_str+cmd_opts,
                                                   comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        comment = "Test case 8 - test suppress warning without quiet"
        cmd_opts = " --suppress"
        res = mutlib.System_test.run_test_case(self, 1, cmd_str+cmd_opts,
                                                   comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        comment = "Test case 9 - test suppress warning with quiet"
        cmd_opts = " --suppress --quiet"
        res = mutlib.System_test.run_test_case(self, 1, cmd_str+cmd_opts,
                                                   comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        self.do_replacements()

        return True

    def get_result(self):
        return self.compare(__name__, self.results)
    
    def record(self):
        return self.save_result_file(__name__, self.results)
    
    def cleanup(self):
        return check_rpl.test.cleanup(self)



