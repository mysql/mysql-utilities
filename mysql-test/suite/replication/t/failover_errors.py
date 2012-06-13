#!/usr/bin/env python

import os
import mutlib
import rpl_admin_gtid
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
        cmd_opts += "--slaves=root:root@localhost "
        res = mutlib.System_test.run_test_case(self, 2, cmd_str+cmd_opts,
                                               comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
            
        # Test for missing --rpl-user
        
        # Add server5 to the topology
        conn_str = " --slave=%s" % self.build_connection_string(self.server5)
        conn_str += "--master=%s " % master_conn 
        cmd = "mysqlreplicate.py --rpl-user=rpl:rpl %s" % conn_str
        res = self.exec_util(cmd, self.res_fname)
        if res != 0:
            return False

        comment = "Test case 5 - FILE/TABLE mix and missing --rpl-user"
        cmd_str = "mysqlfailover.py "        
        cmd_opts = " --master=%s --log=a.txt" % master_conn
        cmd_opts += "--slaves=%s " % ",".join([slave1_conn, slave2_conn,
                                               slave3_conn, slave4_conn])
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

