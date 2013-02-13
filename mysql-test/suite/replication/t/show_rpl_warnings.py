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
import rpl_admin
from mysql.utilities.exception import MUTLibError

class test(rpl_admin.test):
    """test show replication topology
    This test exercises the mysqlrplshow utility warnings concerning options.
    It uses the rpl_admin test for setup and teardown methods.
    """

    def check_prerequisites(self):
        if not self.servers.get_server(0).check_version_compat(5, 6, 5):
            raise MUTLibError("Test requires server version 5.6.5 or higher")
        return self.check_num_servers(1)

    def setup(self):
        res = rpl_admin.test.setup(self)
    
        self.server5 = rpl_admin.test.spawn_server(self, "rep_slave4",
                                                   "--log-bin")
    
        self.s4_port = self.server5.port
        
        self.server5.exec_query("GRANT REPLICATION SLAVE ON *.* TO "
                                "'rpl'@'localhost' IDENTIFIED BY 'rpl'")

        self.master_str = " --master=%s" % \
                          self.build_connection_string(self.server1)
        try:
            self.server5.exec_query("STOP SLAVE")
            self.server5.exec_query("RESET SLAVE")
        except:
            pass
        
        slave_str = " --slave=%s" % self.build_connection_string(self.server5)
        conn_str = self.master_str + slave_str
        cmd = "mysqlreplicate.py --rpl-user=rpl:rpl %s" % conn_str
        res1 = self.exec_util(cmd, self.res_fname)

        return res

    def run(self):
        self.res_fname = "result.txt"
        
        master_conn = self.build_connection_string(self.server1).strip(' ')
        slave1_conn = self.build_connection_string(self.server2).strip(' ')
        slave2_conn = self.build_connection_string(self.server3).strip(' ')
        slave3_conn = self.build_connection_string(self.server4).strip(' ')
        slave4_conn = self.build_connection_string(self.server5).strip(' ')
        
        master_str = "--master=" + master_conn
        slaves_str = "--slaves=" + \
                     ",".join([slave1_conn, slave2_conn, slave3_conn])
        
        comment = "Test case 1 - warning for missing --report-host"
        cmd_str = "mysqlrplshow.py --master=%s --disco=root:root " % master_conn
        res = mutlib.System_test.run_test_case(self, 0, cmd_str, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        try:
            self.server5.exec_query("STOP SLAVE")
            self.server5.exec_query("RESET SLAVE")
        except:
            pass

        # Now we return the topology to its original state for other tests
        rpl_admin.test.reset_topology(self)

        # Mask out non-deterministic data
        rpl_admin.test.do_masks(self)
        self.replace_substring(str(self.s4_port), "PORT5")

        return True

    def get_result(self):
        return self.compare(__name__, self.results)
    
    def record(self):
        return self.save_result_file(__name__, self.results)
    
    def cleanup(self):
        return rpl_admin.test.cleanup(self)



