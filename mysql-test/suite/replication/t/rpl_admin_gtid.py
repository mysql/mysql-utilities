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

_DEFAULT_MYSQL_OPTS = '"--log-bin=mysql-bin --skip-slave-start ' + \
                      '--log-slave-updates --gtid-mode=on ' + \
                      '--enforce-gtid-consistency --report-host=localhost ' + \
                      '--report-port=%s ' + \
                      '--sync-master-info=1 --master-info-repository=table"'

_DEFAULT_MYSQL_OPTS_FILE = '"--log-bin=mysql-bin --skip-slave-start ' + \
                           '--log-slave-updates --gtid-mode=on ' + \
                           '--enforce-gtid-consistency ' + \
                           '--report-host=localhost --report-port=%s ' + \
                           '--sync-master-info=1 --master-info-repository=file"'

class test(rpl_admin.test):
    """test replication administration commands
    This test runs the mysqlrpladmin utility on a known topology.
    
    Note: this test requires GTID enabled servers.
    """

    def check_prerequisites(self):
        if not self.servers.get_server(0).check_version_compat(5, 6, 9):
            raise MUTLibError("Test requires server version 5.6.9")
        return self.check_num_servers(1)

    def setup(self):
        self.res_fname = "result.txt"
        
        # Spawn servers
        self.server0 = self.servers.get_server(0)
        mysqld = _DEFAULT_MYSQL_OPTS % self.servers.view_next_port()
        self.server1 = self.spawn_server("rep_master_gtid", mysqld, True)
        mysqld = _DEFAULT_MYSQL_OPTS % self.servers.view_next_port()
        self.server2 = self.spawn_server("rep_slave1_gtid", mysqld, True)
        mysqld = _DEFAULT_MYSQL_OPTS % self.servers.view_next_port()
        self.server3 = self.spawn_server("rep_slave2_gtid", mysqld, True)
        mysqld = _DEFAULT_MYSQL_OPTS % self.servers.view_next_port()
        self.server4 = self.spawn_server("rep_slave3_gtid", mysqld, True)
        # Spawn a server with MIR=FILE
        mysqld = _DEFAULT_MYSQL_OPTS_FILE % self.servers.view_next_port()
        self.server5 = self.spawn_server("rep_slave4_gtid", mysqld, True)

        self.m_port = self.server1.port
        self.s1_port = self.server2.port
        self.s2_port = self.server3.port
        self.s3_port = self.server4.port
        self.s4_port = self.server5.port
        
        rpl_admin.test.reset_topology(self)

        return True

    def run(self):
        
        # As first phase, repeat rpl_admin tests
        phase1 =  rpl_admin.test.run(self)
        if not phase1:
            return False
        
        test_num = 14
        
        rpl_admin.test.reset_topology(self)

        master_conn = self.build_connection_string(self.server1).strip(' ')
        slave1_conn = self.build_connection_string(self.server2).strip(' ')
        slave2_conn = self.build_connection_string(self.server3).strip(' ')
        slave3_conn = self.build_connection_string(self.server4).strip(' ')
        slave4_conn = self.build_connection_string(self.server5).strip(' ')
        
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
        
        # Remove GTIDs here because they are not deterministic when run with
        # other tests that reuse these servers.
        self.remove_result("localhost,%s,MASTER," % self.m_port)
        self.remove_result("localhost,%s,SLAVE," % self.s1_port)
        self.remove_result("localhost,%s,SLAVE," % self.s2_port)
        self.remove_result("localhost,%s,SLAVE," % self.s3_port)

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
        slaves = ",".join(["root:root@127.0.0.1:%s" % self.server2.port,
                           slave2_conn, slave3_conn])
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
        
        # Test for BUG#14080657
        self.server2.exec_query("GRANT REPLICATION SLAVE ON *.* TO 'rpl'@'rpl'")
        
        cmd_str = "mysqlrpladmin.py --master=%s " % slave3_conn
        comment = "Test case %s - elect with missing rpl user" % test_num
        cmd_opts = " --slaves=%s elect -vvv --candidates=%s " % \
                   (slaves, slave1_conn)
        res = mutlib.System_test.run_test_case(self, 0, cmd_str+cmd_opts,
                                               comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        test_num += 1
        
        # Now we return the topology to its original state for other tests
        rpl_admin.test.reset_topology(self)

        # Test for missing --rpl-user
        
        # Add server5 to the topology
        conn_str = " --slave=%s" % self.build_connection_string(self.server5)
        conn_str += self.master_str 
        cmd = "mysqlreplicate.py --rpl-user=rpl:rpl %s" % conn_str
        res = self.exec_util(cmd, self.res_fname)
        if res != 0:
            return False

        comment = "Test case %s - mix FILE/TABLE and missing --rpl-user" % test_num
        slaves = ",".join([slave1_conn, slave2_conn, slave3_conn, slave4_conn])
        cmd_str = "mysqlrpladmin.py --master=%s " % master_conn
        cmd_opts = " --discover-slaves-login=root:root switchover "
        cmd_opts += "--new-master=root:root@localhost:%s " % self.s4_port
        res = mutlib.System_test.run_test_case(self, 1, cmd_str+cmd_opts,
                                               comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        test_num += 1

        comment = "Test case %s - mix FILE/TABLE and --rpl-user" % test_num
        slaves = ",".join([slave1_conn, slave2_conn, slave3_conn, slave4_conn])
        cmd_str = "mysqlrpladmin.py --master=%s " % master_conn
        cmd_opts = " --discover-slaves-login=root:root switchover "
        cmd_opts += "--new-master=root:root@localhost:%s " % self.s4_port
        cmd_opts += " --rpl-user=rpl:rpl "
        res = mutlib.System_test.run_test_case(self, 0, cmd_str+cmd_opts,
                                               comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        test_num += 1

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

