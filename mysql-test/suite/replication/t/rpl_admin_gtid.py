#!/usr/bin/env python

import os
import mutlib
import rpl_admin
from mysql.utilities.exception import MUTLibError

_DEFAULT_MYSQL_OPTS = '"--log-bin=mysql-bin --skip-slave-start --log-slave-updates --gtid-mode=on --disable-gtid-unsafe-statements --report-host=localhost --report-port=%s "'

class test(rpl_admin.test):
    """test replication administration commands
    This test runs the mysqlrpladmin utility on a known topology.
    
    Note: this test requires GTID enabled servers.
    """

    def check_prerequisites(self):
        if not self.servers.get_server(0).check_version_compat(5, 6, 5):
            raise MUTLibError("Test requires server version 5.6.5")
        return self.check_num_servers(1)

    def setup(self):
        self.res_fname = "result.txt"

        # Spawn servers
        self.server0 = self.servers.get_server(0)
        mysqld = _DEFAULT_MYSQL_OPTS % self.servers.view_next_port()
        self.server1 = self.spawn_server("rep_master_gtid", mysqld)
        mysqld = _DEFAULT_MYSQL_OPTS % self.servers.view_next_port()
        self.server2 = self.spawn_server("rep_slave1_gtid", mysqld)
        mysqld = _DEFAULT_MYSQL_OPTS % self.servers.view_next_port()
        self.server3 = self.spawn_server("rep_slave2_gtid", mysqld)
        mysqld = _DEFAULT_MYSQL_OPTS % self.servers.view_next_port()
        self.server4 = self.spawn_server("rep_slave3_gtid", mysqld)
        
        self.m_port = self.server1.port
        self.s1_port = self.server2.port
        self.s2_port = self.server3.port
        self.s3_port = self.server4.port
        
        rpl_admin.test.reset_topology(self)

        return True

    def run(self):
        
        # As first phase, repeat rpl_admin tests
        phase1 =  rpl_admin.test.run(self)
        if not phase1:
            return False
        
        test_num = 14
        
        master_conn = self.build_connection_string(self.server1).strip(' ')
        slave1_conn = self.build_connection_string(self.server2).strip(' ')
        slave2_conn = self.build_connection_string(self.server3).strip(' ')
        slave3_conn = self.build_connection_string(self.server4).strip(' ')
        
        comment = "Test case %s - elect" % test_num
        slaves = ",".join([slave1_conn, slave2_conn, slave3_conn])
        cmd_str = "mysqlrpladmin.py --master=%s " % master_conn
        cmd_opts = " --candidates=%s  " % slaves
        cmd_opts += " --slaves=%s elect" % slaves
        res = mutlib.System_test.run_test_case(self, 0, cmd_str+cmd_opts,
                                               comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        test_num += 1

        comment = "Test case %s - gtid" % test_num
        slaves = ",".join([slave1_conn, slave2_conn, slave3_conn])
        cmd_str = "mysqlrpladmin.py --master=%s " % master_conn
        cmd_opts = " --slaves=%s gtid --format=csv " % slaves
        res = mutlib.System_test.run_test_case(self, 0, cmd_str+cmd_opts,
                                               comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        test_num += 1
        
        # Mask GTIDs
        self.replace_result("localhost,%s,MASTER," % self.m_port,
                            "localhost,PORT1,MASTER,GTID_HERE\n")
        self.replace_result("localhost,%s,SLAVE," % self.s1_port,
                            "localhost,PORT2,SLAVE,GTID_HERE\n")
        self.replace_result("localhost,%s,SLAVE," % self.s2_port,
                            "localhost,PORT3,SLAVE,GTID_HERE\n")
        self.replace_result("localhost,%s,SLAVE," % self.s3_port,
                            "localhost,PORT4,SLAVE,GTID_HERE\n")

        comment = "Test case %s - heatlh with discover" % test_num
        slaves = ",".join([slave1_conn, slave2_conn, slave3_conn])
        cmd_str = "mysqlrpladmin.py --master=%s " % master_conn
        cmd_opts = " --discover-slaves-login=root:root health --format=csv "
        res = mutlib.System_test.run_test_case(self, 0, cmd_str+cmd_opts,
                                               comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        test_num += 1

        comment = "Test case %s - failover to %s:%s" % \
                  (test_num, self.server4.host, self.server4.port)
        slaves = ",".join([slave1_conn, slave2_conn, slave3_conn])
        cmd_str = "mysqlrpladmin.py --master=%s " % master_conn
        cmd_opts = " --candidates=%s  " % slave3_conn
        cmd_opts += " --slaves=%s failover" % slaves
        res = mutlib.System_test.run_test_case(self, 0, cmd_str+cmd_opts,
                                               comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        test_num += 1
        
        slaves = ",".join([slave1_conn, slave2_conn])
        cmd_str = "mysqlrpladmin.py --master=%s " % slave3_conn
        comment = "Test case %s - show health after failover" % test_num
        cmd_opts = " --slaves=%s --format=vertical health" % slaves
        res = mutlib.System_test.run_test_case(self, 0, cmd_str+cmd_opts,
                                               comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        test_num += 1
        
        # Now we return the topology to its original state for other tests
        rpl_admin.test.reset_topology(self)

        # Mask out non-deterministic data
        rpl_admin.test.do_masks(self)
        
        return True

    def get_result(self):
        return (True, '')
        return self.compare(__name__, self.results)
    
    def record(self):
        return self.save_result_file(__name__, self.results)
    
    def cleanup(self):
        return rpl_admin.test.cleanup(self)

