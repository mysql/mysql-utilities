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
import show_rpl
import mutlib
from mysql.utilities.exception import UtilError, MUTLibError

class test(show_rpl.test):
    """show replication topology - parameter testing
    This test runs the mysqlrplshow utility on a known master-slave topology
    with a variety of parameters. It uses the show_rpl test as a parent for
    setup and teardown methods.
    """

    def check_prerequisites(self):
        return show_rpl.test.check_prerequisites(self)

    def setup(self):
        self.server_list[0] = self.servers.get_server(0)
        self.server_list[1] = self.get_server("rep_slave_show")
        if self.server_list[1] is None:
            return False
        self.server_list[2] = self.get_server("rep_master_show")
        if self.server_list[2] is None:
            return False
            
        self.port_repl = []
        self.port_repl.append(self.server_list[1].port)
        self.port_repl.append(self.server_list[2].port)
        return True

    def run(self):
        self.res_fname = "result.txt"

        master_str = "--master=%s" % \
                     self.build_connection_string(self.server_list[2])
        slave_str = " --slave=%s" % \
                    self.build_connection_string(self.server_list[1])
        conn_str = master_str + slave_str
        
        show_rpl.test.stop_replication(self, self.server_list[4])
        show_rpl.test.stop_replication(self, self.server_list[3])
        show_rpl.test.stop_replication(self, self.server_list[2])
        show_rpl.test.stop_replication(self, self.server_list[1])

        # On Windows, we must force replication to stop.
        if os.name == 'nt':
            res = self.server_list[2].exec_query("SHOW FULL PROCESSLIST")
            for row in res:
                if row[4].lower() == "binlog dump":
                    self.server_list[2].exec_query("KILL CONNECTION %s" % \
                                                   row[0])

        cmd = "mysqlreplicate.py --rpl-user=rpl:rpl " 
        try:
            res = self.exec_util(cmd+master_str+slave_str,
                                 self.res_fname)            
        except UtilError, e:
            raise MUTLibError(e.errmsg)
            
        cmd = "mysqlshow_rpl.py --rpl-user=rpl:rpl " 
        try:
            res = self.exec_util(cmd+master_str+slave_str,
                                 self.res_fname)            
        except UtilError, e:
            raise MUTLibError(e.errmsg)
        
        cmd_str = "mysqlrplshow.py --disco=root:root " + master_str

        comment = "Test case 1 - show topology - without list"
        cmd_opts = "  --recurse "
        res = mutlib.System_test.run_test_case(self, 0, cmd_str+cmd_opts,
                                               comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
   
        comment = "Test case 2 - show topology - with list"
        cmd_opts = "  --recurse --show-list"
        res = mutlib.System_test.run_test_case(self, 0, cmd_str+cmd_opts,
                                               comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
   
        comment = "Test case 3 - show topology - with list and quiet"
        cmd_opts = "  --recurse --quiet --show-list"
        res = mutlib.System_test.run_test_case(self, 0, cmd_str+cmd_opts,
                                               comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
   
        comment = "Test case 4 - show topology - with format and without list"
        cmd_opts = "  --recurse --format=CSV"
        res = mutlib.System_test.run_test_case(self, 0, cmd_str+cmd_opts,
                                               comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
   
        comment = "Test case 5 - show topology - help"
        cmd_opts = " --help"
        res = mutlib.System_test.run_test_case(self, 0, cmd_str+cmd_opts,
                                               comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        _FORMATS = ("CSV", "TAB", "GRID", "VERTICAL")
        test_num = 6
        for format in _FORMATS:
            comment = "Test Case %d : Testing show topology with " % test_num
            comment += "%s format " % format
            cmd_opts = "  --recurse --show-list --format=%s" % format
            res = mutlib.System_test.run_test_case(self, 0, cmd_str+cmd_opts,
                                               comment)
            if not res:
                raise MUTLibError("%s: failed" % comment)

            test_num += 1
            
        show_rpl.test.stop_replication(self, self.server_list[1])

        show_rpl.test.do_replacements(self)

        return True

    def get_result(self):
        return self.compare(__name__, self.results)
    
    def record(self):
        return self.save_result_file(__name__, self.results)
    
    def cleanup(self):
        return show_rpl.test.cleanup(self)



