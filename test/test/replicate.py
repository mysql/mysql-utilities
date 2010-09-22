#!/usr/bin/env python

import os
import mysql_test

class test(mysql_test.System_test):
    """setup replication
    This test executes a simple replication setup among two servers.
    """

    def check_prerequisites(self):
        self.server1 = self.servers.get_server(0)
        self.server2 = None
        return self.check_num_servers(1)

    def setup(self):

        # For this setup, we clone the original server making two new servers
        # to be used as a master and a slave for the tests then destroy them
        # in cleanup()

        port1 = int(self.servers.get_next_port())
        port2 = int(self.servers.get_next_port())

        self.s1_serverid = self.servers.get_next_id()
        self.s2_serverid = self.servers.get_next_id()

        conn_val = self.get_connection_values(self.server1)
        try:
            res = self.servers.start_new_server(self.server1, "temp_data1",
                                                port1, self.s1_serverid,
                                                "root", "replicate1",
                                                "--log-bin=mysql-bin")
        except MySQLUtilError, e:
            print e.errmsg
            
        self.server1 = res[0]
        if not self.server1:
            return False        

        res = self.servers.start_new_server(self.server1, "temp_data2", port2,
                                            self.s2_serverid, "root",
                                            "replicate2",
                                            "--log-bin=mysql-bin")
        self.server2 = res[0]
        if not self.server2:
            return False

        return True
    
    def run_test_case(self, server1, server2, s_id,
                      comment, options=None, save_for_compare=False,
                      expected_result=0):
        #
        # Note: server1 is slave, server2 is master
        #
        
        master_str = "--master=%s" % self.build_connection_string(server2)
        slave_str = " --slave=%s" % self.build_connection_string(server1)
        conn_str = master_str + slave_str
        
        # Test case 1 - setup replication among two servers
        if not save_for_compare:
            self.results.append(comment)
        cmd = "mysqlreplicate.py --server-id=%d " % s_id
        cmd += "--rpl-user=rpl:rpl %s" % (conn_str)
        if options:
            cmd += " %s" % options
        if not save_for_compare:
            self.results.append(cmd)
        res = self.exec_util(cmd, self.res_fname)
        if not save_for_compare:
            self.results.append(res)
        
        if res != expected_result:
            return False

        # Now test the result and record the action.
        try:
            res = server1.exec_query("SHOW SLAVE STATUS")
            if not save_for_compare:
                self.results.append(res)
        except MySQLUtilError, e:
            return False

        if save_for_compare:
            self.results.append(comment+"\n")
            for line in open(self.res_fname).readlines():
                # Don't save lines that have [Warning]
                index = line.find("[Warning]")
                if index <= 0:
                    self.results.append(line)

        return True
    
    def run(self):
        self.res_fname = self.testdir + "result.txt"
        
        comment = "Test case 1 - replicate server1 as slave of server2 "
        res = self.run_test_case(self.server1, self.server2, self.s1_serverid,
                                 comment, True)
        if not res:
            return False
        
        try:
            res = self.server1.exec_query("STOP SLAVE")
        except:
            return False

        comment = "Test case 2 - replicate server2 as slave of server1 "
        res = self.run_test_case(self.server2, self.server1, self.s2_serverid,
                                 comment, True)
        if not res:
            return False
        
        try:
            res = self.server2.exec_query("STOP SLAVE")
        except:
            return False

        return True

    def check_test_case(self, index, comment):
        msg = None
        test_passed = True
        
        # Check test case
        if self.results[index] == 0:
            if self.results[index+1] == ():
                return (false, "%s: Slave status missing." % comment)
            test_result = self.results[index+1][0]
            if test_result[0] != "Waiting for master to send event":
                test_passed = False
                msg = "%s: Slave failed to communicate with master." % comment
        else:
            test_passed = False
            msg = "%s: Replication event failed." % comment
        return (test_passed, msg)

    def get_result(self):
        # tc1 tc2 content
        # --- --- -----
        #  0   4  comment
        #  1   5  command
        #  2   6  result of exec_util
        #  3   7  result of SHOW SLAVE STATUS
        
        res = self.check_test_case(2, "Test case 1")
        if not res[0]:
            return res

        res = self.check_test_case(6, "Test case 2")
        if not res[0]:
            return res

        return (True, None)
    
    def record(self):
        # Not a comparative test, returning True
        return True
    
    def cleanup(self):
        if self.res_fname:
            os.unlink(self.res_fname)
        res1 = True
        res2 = True
        if self.server1:
            res1 = self.servers.stop_server(self.server1)
            self.servers.clear_last_port()
            self.server1 = None
        if self.server2:
            res2 = self.servers.stop_server(self.server2)
            self.servers.clear_last_port()
            self.server2 = None
        return res1 and res2



