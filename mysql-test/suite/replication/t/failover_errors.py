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
import rpl_admin_gtid
import socket
from mysql.utilities.exception import MUTLibError

class test(rpl_admin_gtid.test):
    """test replication failover utility
    This test exercises the mysqlfailover utility known error conditions.
    Note: this test requires GTID enabled servers.
    """

    def check_prerequisites(self):
        return rpl_admin_gtid.test.check_prerequisites(self)

    def setup(self):
        return rpl_admin_gtid.test.setup(self)
    
    def run(self):
        self.res_fname = "result.txt"

        master_conn = self.build_connection_string(self.server1).strip(' ')
        slave1_conn = self.build_connection_string(self.server2).strip(' ')
        slave2_conn = self.build_connection_string(self.server3).strip(' ')
        slave3_conn = self.build_connection_string(self.server4).strip(' ')
        slave4_conn = self.build_connection_string(self.server5).strip(' ')

        comment = "Test case 1 - No master"
        cmd_str = "mysqlfailover.py " 
        cmd_opts = " --discover-slaves-login=root:root"
        res = mutlib.System_test.run_test_case(self, 2, cmd_str+cmd_opts,
                                               comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        comment = "Test case 2 - No slaves or discover-slaves-login"
        cmd_str = "mysqlfailover.py " 
        cmd_opts = " --master=root:root@localhost"
        res = mutlib.System_test.run_test_case(self, 2, cmd_str+cmd_opts,
                                               comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        comment = "Test case 3 - Low value for interval."
        cmd_str = "mysqlfailover.py --interval=1" 
        cmd_opts = " --master=root:root@localhost"
        res = mutlib.System_test.run_test_case(self, 2, cmd_str+cmd_opts,
                                               comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        comment = "Test case 4 - elect mode but no candidates"
        cmd_str = "mysqlfailover.py " 
        cmd_opts = " --master=root:root@localhost --failover-mode=elect "
        cmd_opts += "--slaves=%s " % slave1_conn
        res = mutlib.System_test.run_test_case(self, 2, cmd_str+cmd_opts,
                                               comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
            
        # Test for missing --rpl-user
        
        # Add server5 to the topology
        conn_str = " --slave=%s" % self.build_connection_string(self.server5)
        conn_str += " --master=%s " % master_conn 
        cmd = "mysqlreplicate.py --rpl-user=rpl:rpl %s" % conn_str
        res = self.exec_util(cmd, self.res_fname)
        if res != 0:
            return False

        comment = "Test case 5 - FILE/TABLE mix and missing --rpl-user"
        cmd_str = "mysqlfailover.py "        
        cmd_opts = " --master=%s --log=a.txt" % master_conn
        cmd_opts += " --slaves=%s " % ",".join([slave1_conn, slave2_conn,
                                               slave3_conn, slave4_conn])
        res = mutlib.System_test.run_test_case(self, 1, cmd_str+cmd_opts,
                                               comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        
        # Now test to see what happens when master is listed as a slave
        comment = "Test case 6 - Master listed as a slave - literal" 
        cmd_str = "mysqlfailover.py health "        
        cmd_opts = " --master=%s " % master_conn
        cmd_opts += " --slaves=%s " % ",".join([slave1_conn, slave2_conn,
                                               slave3_conn, master_conn])
        res = mutlib.System_test.run_test_case(self, 2, cmd_str+cmd_opts,
                                               comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        comment = "Test case 7 - Master listed as a slave - alias" 
        cmd_str = "mysqlfailover.py health "        
        cmd_opts = " --master=%s " % master_conn
        cmd_opts += " --slaves=root:root@%s:%s " % \
                    (socket.gethostname().split('.', 1)[0], self.server1.port)
        res = mutlib.System_test.run_test_case(self, 2, cmd_str+cmd_opts,
                                               comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        comment = "Test case 8 - Master listed as a candiate - alias" 
        cmd_str = "mysqlfailover.py health "        
        cmd_opts = " --master=%s " % master_conn
        cmd_opts += " --slaves=%s " % ",".join([slave1_conn, slave2_conn])
        cmd_opts += " --candidates=root:root@%s:%s " % \
                    (socket.gethostname().split('.', 1)[0], self.server1.port)
        res = mutlib.System_test.run_test_case(self, 2, cmd_str+cmd_opts,
                                               comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        self.reset_topology()
        
        self.replace_substring(str(self.m_port), "PORT1")
        self.replace_substring(str(self.s1_port), "PORT2")
        self.replace_substring(str(self.s2_port), "PORT3")
        self.replace_substring(str(self.s3_port), "PORT4")
        self.replace_substring(str(self.s4_port), "PORT5")

        return True

    def get_result(self):
        return self.compare(__name__, self.results)
    
    def record(self):
        return self.save_result_file(__name__, self.results)
    
    def cleanup(self):
        if self.res_fname:
            try:
                os.unlink(self.res_fname)
                os.unlink("a.txt")
            except:
                pass
        return True

