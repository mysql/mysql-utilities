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
    """show replication topology - error testing
    This test runs the mysqlrplshow utility on a known master-slave topology
    with errors. It uses the show_rpl test as a parent for
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
        
        cmd_str = "mysqlrplshow.py --master=wikiwakawonky --disco=root:root"
        comment = "Test case 1 - error: cannot parse master string"
        res =  mutlib.System_test.run_test_case(self, 2, cmd_str, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        cmd_str = "mysqlrplshow.py --disco=root:root --master=wanda:fish@localhost:%s" % \
                  self.server_list[0].port
        comment = "Test case 2 - error: invalid login to master"
        res =  mutlib.System_test.run_test_case(self, 1, cmd_str, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        show_rpl.test.stop_replication(self, self.server_list[4])
        show_rpl.test.stop_replication(self, self.server_list[3])
        show_rpl.test.stop_replication(self, self.server_list[2])
        show_rpl.test.stop_replication(self, self.server_list[1])

        cmd = "mysqlreplicate.py --rpl-user=rpl:rpl " 
        try:
            res = self.exec_util(cmd+master_str+slave_str,
                                 self.res_fname)            
        except UtilError, e:
            raise MUTLibError(e.errmsg)
        
        cmd_str = "mysqlrplshow.py --disco=root:root " + master_str

        comment = "Test case 3 - show topology - bad format"
        cmd_opts = "  --show-list --recurse --format=XXXXXX"
        res = mutlib.System_test.run_test_case(self, 2, cmd_str+cmd_opts,
                                                   comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        # Create a user to test error for not enough permissions
        self.server_list[2].exec_query("CREATE USER 'josh'@'localhost'")

        cmd_str = "mysqlrplshow.py --disco=root:root --master=josh@localhost:%s" % \
                  self.server_list[2].port
        if not self.server_list[2].socket is None:
            cmd_str += ":" + self.server_list[2].socket
            
        comment = "Test case 4a - show topology - not enough permissions"
        cmd_opts = "  --show-list --recurse "
        res = mutlib.System_test.run_test_case(self, 1, cmd_str+cmd_opts,
                                                   comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
            
        self.server_list[2].exec_query("GRANT REPLICATION SLAVE ON *.* TO "
                                "'josh'@'localhost'")

        comment = "Test case 4b - show topology - not enough permissions"
        cmd_opts = "  --show-list --recurse "
        res = mutlib.System_test.run_test_case(self, 0, cmd_str+cmd_opts,
                                                   comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        comment = "Test case 5 - show topology - bad max-depth"
        cmd_opts = "  --show-list --recurse --max-depth=-1"
        res = mutlib.System_test.run_test_case(self, 2, cmd_str+cmd_opts,
                                                   comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        comment = "Test case 6 - show topology - large max-depth"
        cmd_opts = "  --show-list --recurse --max-depth=9999"
        res = mutlib.System_test.run_test_case(self, 0, cmd_str+cmd_opts,
                                                   comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        comment = "Test case 7 - show topology - discover-slaves-login missing"
        cmd_str = "mysqlrplshow.py --master=josh@localhost:%s" % \
                  self.server_list[2].port
        cmd_opts = "  --show-list --recurse --max-depth=9999"
        res = mutlib.System_test.run_test_case(self, 2, cmd_str+cmd_opts,
                                                   comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
            
        show_rpl.test.do_replacements(self)

        self.replace_result("Error 1045", "Error 1045: Access denied for "
                            "user 'wanda'@'localhost' (using password: "
                            "YES)\n")

        self.replace_result("mysqlrplshow.py: error: Master connection "
                            "values invalid",
                            "mysqlrplshow.py: error: Master connection "
                            "values invalid\n")

        show_rpl.test.stop_replication(self, self.server_list[1])

        return True

    def get_result(self):
        return self.compare(__name__, self.results)
    
    def record(self):
        return self.save_result_file(__name__, self.results)
    
    def cleanup(self):
        self.server_list[2].exec_query("DROP USER 'josh'@'localhost'")
        return show_rpl.test.cleanup(self)



