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
import mutlib
from mysql.utilities.exception import UtilError, MUTLibError

class test(mutlib.System_test):
    """show replication topology
    This test runs the mysqlrplshow utility on a known master-slave topology
    to print the topology. 
    """

    def check_prerequisites(self):
        self.server_list = [None, None, None, None, None, None, None]
        self.port_repl = []
        return self.check_num_servers(1)

    def get_server(self, name):
        server = None
        server_id = None
        
        serverid = self.servers.get_next_id()
        new_port = self.servers.get_next_port()
        mysqld_params = ' --mysqld="--log-bin=mysql-bin ' + \
                        ' --report-host=%s --report-port=%s"' % \
                        ('localhost', new_port)
        self.servers.clear_last_port()
        res = self.servers.spawn_new_server(self.server_list[0], serverid,
                                           name, mysqld_params)
        if not res:
            raise MUTLibError("Cannot spawn replication slave server.")
        server = res[0]
        self.servers.add_new_server(server, True)

        return server

    def setup(self):
        self.server_list[0] = self.servers.get_server(0)
        self.server_list[1] = self.get_server("rep_slave_show")
        if self.server_list[1] is None:
            return False
        self.server_list[2] = self.get_server("rep_master_show")
        if self.server_list[2] is None:
            return False
        self.server_list[3] = self.get_server("rep_relay_slave")
        if self.server_list[3] is None:
            return False
        self.server_list[4] = self.get_server("slave_leaf")
        if self.server_list[4] is None:
            return False
        self.server_list[5] = self.get_server("multi_master1")
        if self.server_list[5] is None:
            return False
        self.server_list[6] = self.get_server("multi_master2")
        if self.server_list[6] is None:
            return False
        self.port_repl.append(self.server_list[1].port)
        self.port_repl.append(self.server_list[2].port)
        self.port_repl.append(self.server_list[3].port)
        self.port_repl.append(self.server_list[4].port)
        self.port_repl.append(self.server_list[5].port)
        self.port_repl.append(self.server_list[6].port)

        return True

    def run(self):
        self.res_fname = "result.txt"

        master_str = "--master=%s" % \
                     self.build_connection_string(self.server_list[2])
        slave_str = " --slave=%s" % \
                    self.build_connection_string(self.server_list[1])
        relay_slave_slave = " --slave=%s" % \
                           self.build_connection_string(self.server_list[3])
        relay_slave_master = " --master=%s" % \
                             self.build_connection_string(self.server_list[3])
        slave_leaf = " --slave=%s" % \
                     self.build_connection_string(self.server_list[4])

        cmd_str = "mysqlrplshow.py --disco=root:root " + master_str

        comment = "Test case 1 - show topology of master with no slaves"
        cmd_opts = "  --show-list --recurse "
        res = mutlib.System_test.run_test_case(self, 0, cmd_str+cmd_opts,
                                                   comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        conn_str = master_str + slave_str
        
        cmd = "mysqlreplicate.py --rpl-user=rpl:rpl " 
        try:
            res = self.exec_util(cmd+master_str+slave_str,
                                 self.res_fname)
            res = self.exec_util(cmd+master_str+relay_slave_slave,
                                 self.res_fname)
            res = self.exec_util(cmd+relay_slave_master+slave_leaf,
                                 self.res_fname)
            
        except UtilError, e:
            raise MUTLibError(e.errmsg)

        cmd_str = "mysqlrplshow.py --disco=root:root " + master_str

        comment = "Test case 2 - show topology"
        cmd_opts = "  --show-list --recurse "
        res = mutlib.System_test.run_test_case(self, 0, cmd_str+cmd_opts,
                                                   comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
   
        comment = "Test case 3 - show topology with --max-depth"
        cmd_opts = "  --show-list --recurse --max-depth=1"
        res = mutlib.System_test.run_test_case(self, 0, cmd_str+cmd_opts,
                                                   comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        try:
            circle_master = " --master=%s" % \
                            self.build_connection_string(self.server_list[4])
            circle_slave = " --slave=%s" % \
                           self.build_connection_string(self.server_list[2])
            res = self.exec_util(cmd+circle_master+circle_slave,
                                 self.res_fname)
            
        except UtilError, e:
            raise MUTLibError(e.errmsg)

        comment = "Test case 4 - show topology with circular replication"
        cmd_opts = "  --show-list --recurse "
        res = mutlib.System_test.run_test_case(self, 0, cmd_str+cmd_opts,
                                                   comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        
        # Create a master:master toplogy
        cmd = "mysqlreplicate.py --rpl-user=rpl:rpl " 
        try:
            cmd_str = cmd + "--master=%s --slave=%s" % \
                      (self.build_connection_string(self.server_list[5]),
                       self.build_connection_string(self.server_list[6]))                        
            res = self.exec_util(cmd_str, self.res_fname)
            cmd_str = cmd + "--master=%s --slave=%s" % \
                      (self.build_connection_string(self.server_list[6]),
                       self.build_connection_string(self.server_list[5]))                        
            res = self.exec_util(cmd_str, self.res_fname)
        except UtilError, e:
            raise MUTLibError(e.errmsg)

        comment = "Test case 5 - show topology with master:master replication"
        cmd_str = "mysqlrplshow.py --master=%s --disco=root:root " % \
                  self.build_connection_string(self.server_list[5])
        cmd_opts = "  --show-list --recurse "
        res = mutlib.System_test.run_test_case(self, 0, cmd_str+cmd_opts,
                                                   comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
            
        # Here we need to kill one of the servers to show that the
        # phantom server error from a stale SHOW SLAVE HOSTS is
        # fixed and the slave does *not* show on the graph.

        self.servers.stop_server(self.server_list[4])
        self.servers.remove_server(self.server_list[4])
        self.server_list[4] = None

        # This shows there is indeed stale data in the view
        res = self.server_list[3].exec_query("SHOW SLAVE HOSTS")
        self.results.append("Test case 6 : SHOW SLAVE HOSTS contains %d row.\n" %
                            len(res))

        comment = "Test case 6 - show topology with phantom slave"
        cmd_str = "mysqlrplshow.py --disco=root:root " + relay_slave_master
        cmd_opts = "  --show-list "
        res = mutlib.System_test.run_test_case(self, 0, cmd_str+cmd_opts,
                                               comment)

        self.do_replacements()
            
        if not res:
            raise MUTLibError("%s: failed" % comment)

        for i in range(6,0,-1):
            self.stop_replication(self.server_list[i])
        
        return True
    
    def do_replacements(self):
        self.replace_substring(" (28000)", "")
        self.replace_substring("127.0.0.1", "localhost")
        i = 1
        for port in self.port_repl:
            self.replace_substring("%s" % port, "PORT%d" % i)
            i += 1
        self.replace_result("Error connecting to a slave",
                            "Error connecting to a slave ...\n")
        self.replace_result("Error 2002: Can't connect to",
                            "Error ####: Can't connect to local MySQL server\n")
        self.replace_result("Error 2003: Can't connect to",
                            "Error ####: Can't connect to local MySQL server\n")

    def get_result(self):
        return self.compare(__name__, self.results)
    
    def record(self):
        return self.save_result_file(__name__, self.results)
    
    def stop_replication(self, server):
        if server is not None:
            res = server.exec_query("STOP SLAVE")
            res = server.exec_query("RESET SLAVE")
            res = server.exec_query("RESET MASTER")
    
    def cleanup(self):
        if self.res_fname:
            os.unlink(self.res_fname)
        return True


