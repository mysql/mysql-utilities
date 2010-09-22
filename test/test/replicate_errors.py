#!/usr/bin/env python

import os
import replicate
import mysql_test

class test(replicate.test):
    """check error conditions
    This test ensures the known error conditions are tested. It uses the
    cloneuser test as a parent for setup and teardown methods.
    """

    def check_prerequisites(self):
        return replicate.test.check_prerequisites(self)

    def setup(self):
        self.port1 = int(self.servers.get_next_port())
        self.port2 = int(self.servers.get_next_port())
        self.port3 = int(self.servers.get_next_port())
        
        return replicate.test.setup(self)

    def run(self):
        self.res_fname = self.testdir + "result.txt"

        master_str = "--master=%s" % self.build_connection_string(self.server2)
        slave_str = " --slave=%s" % self.build_connection_string(self.server1)
        conn_str = master_str + slave_str

        cmd_str = "mysqlreplicate.py "
      
        comment = "Test case 1 - error: invalid login to server (master)"
        res = mysql_test.System_test.run_test_case(self, 1, cmd_str +
                        slave_str + " --master=nope@nada:localhost:%d " % \
                        self.port1 + "--rpl-user=rpl:whatsit", comment)
        if not res:
            return False

        conn_values = self.get_connection_values(self.server1)
        
        comment = "Test case 2 - error: invalid login to server (slave)"
        res = mysql_test.System_test.run_test_case(self, 1, cmd_str +
                        master_str + " --slave=nope@nada:localhost:%d " % \
                        self.port2 + "--rpl-user=rpl:whatsit", comment)
        if not res:
            return False

        str = self.build_connection_string(self.server1)
        same_str = "--master=%s --slave=%s " % (str, str)

        comment = "Test case 3 - error: slave and master same machine"
        res = mysql_test.System_test.run_test_case(self, 1, cmd_str +
                        same_str + "--rpl-user=rpl:whatsit", comment)
        if not res:
            return False

        # Now we must muck with the servers. We need to turn binary logging
        # off for the next test case.

        res = self.servers.stop_server(self.server2)
        del self.server2
        res = self.servers.start_new_server(self.server1, "temp_data2",
                                            self.port3,
                                            self.servers.get_next_id(),
                                            "root", "temprep1")
        self.server2 = res[0]
        if not self.server2:
            return False

        new_server_str = self.build_connection_string(self.server2)
        new_master_str = self.build_connection_string(self.server1)
        
        cmd_str = "mysqlreplicate.py --master=%s " % new_server_str
        cmd_str += slave_str
        
        comment = "Test case 4 - error: No binary logging on master"
        cmd = cmd_str + "--rpl-user=rpl:whatsit "
        res = mysql_test.System_test.run_test_case(self, 1, cmd, comment)
        if not res:
            return False

        self.server2.exec_query("CREATE USER dummy@localhost")
        self.server2.exec_query("GRANT SELECT ON *.* TO dummy@localhost")
        self.server1.exec_query("CREATE USER dummy@localhost")
        self.server1.exec_query("GRANT SELECT ON *.* TO dummy@localhost")

        comment = "Test case 5 - error: replicate() fails"
        
        conn = self.get_connection_values(self.server2)
        
        cmd = "mysqlreplicate.py --slave=dummy@localhost"
        if conn[3] is not None:
            cmd += ":%s" % conn[3]
        if conn[4] is not None and conn[4] != "":
            cmd +=  ":%s" % conn[4]
        cmd += " --rpl-user=rpl:whatsit --master=" + new_master_str 
        res = mysql_test.System_test.run_test_case(self, 1, cmd, comment)
        if not res:
            return False

        # Mask known platform-dependent lines
        self.mask_result("Error 2005:", "(1", '#######')
        self.replace_result("ERROR: Query failed. 1227: Access denied;",
                            "ERROR: Query failed. 1227: Access denied;\n")

        return True

    def get_result(self):
        return self.compare(__name__, self.results)
    
    def record(self):
        return self.save_result_file(__name__, self.results)
    
    def cleanup(self):
        self.servers.clear_last_port()
        self.servers.clear_last_port()
        self.servers.clear_last_port()
        return replicate.test.cleanup(self)



