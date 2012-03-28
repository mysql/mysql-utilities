#!/usr/bin/env python

import os
import mutlib
from mysql.utilities.exception import MUTLibError

_DEFAULT_MYSQL_OPTS = '"--log-bin=mysql-bin --report-host=localhost --report-port=%s "'

class test(mutlib.System_test):
    """test replication administration commands
    This test runs the mysqlrpladmin utility on a known topology.
    
    Note: this test will run against older servers. See rpl_admin_gtid
    test for test cases for GTID enabled servers.
    """

    def check_prerequisites(self):
        if self.servers.get_server(0).check_version_compat(5, 6, 5):
            raise MUTLibError("Test requires server version prior to 5.6.5")
        return self.check_num_servers(1)

    def spawn_server(self, name, mysqld=None):
        if self.debug:
            print "# Spawning %s" % name
        index = self.servers.find_server_by_name(name)
        if index >= 0:
            if self.debug:
                print "# Found it in the servers list."
            server = self.servers.get_server(index)
            try:
                res = server.show_server_variable("server_id")
            except MUTLibError, e:
                raise MUTLibError("Cannot get replication server " +
                                   "server_id: %s" % e.errmsg)
        else:
            if self.debug:
                print "# Cloning server0."
            serverid = self.servers.get_next_id()
            if mysqld is None:
                mysqld = _DEFAULT_MYSQL_OPTS % self.servers.view_next_port()
            res = self.servers.spawn_new_server(self.server0, serverid,
                                                name, mysqld)
            if not res:
                raise MUTLibError("Cannot spawn replication server '%s'." &
                                  name)
            self.servers.add_new_server(res[0], True)
            server = res[0]
            
        return server

    def setup(self):
        self.res_fname = "result.txt"
        
        # Spawn servers
        self.server0 = self.servers.get_server(0)
        self.server1 = self.spawn_server("rep_master")
        self.server2 = self.spawn_server("rep_slave1")
        self.server3 = self.spawn_server("rep_slave2")
        self.server4 = self.spawn_server("rep_slave3")

        self.m_port = self.server1.port
        self.s1_port = self.server2.port
        self.s2_port = self.server3.port
        self.s3_port = self.server4.port

        # Form replication topology - 1 master, 3 slaves
        return self.reset_topology()

    def run(self):
        
        cmd_str = "mysqlrpladmin.py %s " % self.master_str
        
        master_conn = self.build_connection_string(self.server1).strip(' ')
        slave1_conn = self.build_connection_string(self.server2).strip(' ')
        slave2_conn = self.build_connection_string(self.server3).strip(' ')
        slave3_conn = self.build_connection_string(self.server4).strip(' ')
        
        slaves_str = ",".join([slave1_conn, slave2_conn, slave3_conn])
        
        comment = "Test case 1 - show health before switchover"
        cmd_opts = " --slaves=%s --format=vertical health" % slaves_str
        res = mutlib.System_test.run_test_case(self, 0, cmd_str+cmd_opts,
                                               comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        # Perform switchover from original master to all other slaves and back.
        test_cases = [
            # (master, [slaves_before], candidate, new_master, [slaves_after])
            (master_conn, [slave1_conn, slave2_conn, slave3_conn],
             slave1_conn, "slave1", [slave2_conn, slave3_conn, master_conn]),
            (slave1_conn, [slave2_conn, slave3_conn, master_conn],
             slave2_conn, "slave2", [slave1_conn, slave3_conn, master_conn]),
            (slave2_conn, [slave1_conn, slave3_conn, master_conn],
             slave3_conn, "slave3", [slave2_conn, slave1_conn, master_conn]),
            (slave3_conn, [slave2_conn, slave1_conn, master_conn],
             master_conn, "master", [slave1_conn, slave2_conn, slave3_conn]),
        ]
        test_num = 2
        for case in test_cases:
            slaves_str = ",".join(case[1])
            comment = "Test case %s - switchover to %s" % (test_num, case[3])
            cmd_str = "mysqlrpladmin.py --master=%s " % case[0]
            cmd_opts = " --new-master=%s --demote-master " % case[2]
            cmd_opts += " --slaves=%s switchover" % slaves_str
            res = mutlib.System_test.run_test_case(self, 0, cmd_str+cmd_opts,
                                                   comment)
            if not res:
                raise MUTLibError("%s: failed" % comment)
            test_num += 1
            slaves_str = ",".join(case[4])
            cmd_str = "mysqlrpladmin.py --master=%s " % case[2]
            comment = "Test case %s - show health after switchover" % test_num
            cmd_opts = " --slaves=%s --format=vertical health" % slaves_str
            res = mutlib.System_test.run_test_case(self, 0, cmd_str+cmd_opts,
                                                   comment)
            if not res:
                raise MUTLibError("%s: failed" % comment)
            test_num += 1

        # Perform stop, start, and reset
        commands = ['stop', 'start', 'stop', 'reset']
        for cmd in commands:
            comment = "Test case %s - run command %s" % (test_num, cmd)
            cmd_str = "mysqlrpladmin.py --master=%s " % master_conn
            cmd_opts = " --slaves=%s %s" % (slaves_str, cmd)
            res = mutlib.System_test.run_test_case(self, 0, cmd_str+cmd_opts,
                                                   comment)
            if not res:
                raise MUTLibError("%s: failed" % comment)
            test_num += 1
            
        # Now we return the topology to its original state for other tests
        self.reset_topology()

        # Mask out non-deterministic data
        self.do_masks()

        return True

    def do_masks(self):
        self.replace_substring("%s" % self.m_port, "PORT1")
        self.replace_substring("%s" % self.s1_port, "PORT2")
        self.replace_substring("%s" % self.s2_port, "PORT3")
        self.replace_substring("%s" % self.s3_port, "PORT4")
        
    def reset_topology(self):
        # Form replication topology - 1 master, 3 slaves
        self.master_str = "--master=%s" % \
                          self.build_connection_string(self.server1)
        for slave in [self.server2, self.server3, self.server4]:
            slave_str = " --slave=%s" % self.build_connection_string(slave)
            conn_str = self.master_str + slave_str
            cmd = "mysqlreplicate.py --rpl-user=rpl:rpl %s" % conn_str
            res = self.exec_util(cmd, self.res_fname)
            if res != 0:
                return False

        return True

    def get_result(self):
        return self.compare(__name__, self.results)
    
    def record(self):
        return self.save_result_file(__name__, self.results)
    
    def cleanup(self):
        if self.res_fname:
            try:
                os.unlink(self.res_fname)
            except:
                pass
        return True

