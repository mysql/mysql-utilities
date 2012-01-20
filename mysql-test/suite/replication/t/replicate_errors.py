#!/usr/bin/env python

import os
import replicate
import mutlib
from mysql.utilities.exception import MUTLibError

class test(replicate.test):
    """check error conditions
    This test ensures the known error conditions are tested. It uses the
    cloneuser test as a parent for setup and teardown methods.
    """

    def check_prerequisites(self):
        return replicate.test.check_prerequisites(self)

    def setup(self):
        self.server3 = None
        return replicate.test.setup(self)

    def run(self):
        self.res_fname = "result.txt"

        master_str = "--master=%s" % self.build_connection_string(self.server2)
        slave_str = " --slave=%s" % self.build_connection_string(self.server1)
        conn_str = master_str + slave_str

        cmd_str = "mysqlreplicate.py "

        comment = "Test case 1 - error: cannot parse server (slave)"
        res = mutlib.System_test.run_test_case(self, 2, cmd_str +
                        master_str + " --slave=wikiwokiwonky "
                        "--rpl-user=rpl:whatsit", comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        comment = "Test case 2 - error: cannot parse server (master)"
        res = mutlib.System_test.run_test_case(self, 2, cmd_str +
                        slave_str + " --master=wikiwakawonky " +
                        "--rpl-user=rpl:whatsit", comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        comment = "Test case 3 - error: invalid login to server (master)"
        res = mutlib.System_test.run_test_case(self, 1, cmd_str +
                        slave_str + " --master=nope@nada:localhost:5510 " +
                        "--rpl-user=rpl:whatsit", comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        conn_values = self.get_connection_values(self.server1)
        
        comment = "Test case 4 - error: invalid login to server (slave)"
        res = mutlib.System_test.run_test_case(self, 1, cmd_str +
                        master_str + " --slave=nope@nada:localhost:5511 " +
                        "--rpl-user=rpl:whatsit", comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        str = self.build_connection_string(self.server1)
        same_str = "--master=%s --slave=%s " % (str, str)

        comment = "Test case 5a - error: slave and master same machine"
        res = mutlib.System_test.run_test_case(self, 1, cmd_str +
                        same_str + "--rpl-user=rpl:whatsit", comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        same_str = "--master=root@this:3306 --slave=root@that:3306"
        comment = "Test case 5b - error: slave and master same port"
        res = mutlib.System_test.run_test_case(self, 1, cmd_str +
                        same_str + "--rpl-user=rpl:whatsit", comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        # Now we must muck with the servers. We need to turn binary logging
        # off for the next test case.

        self.port3 = int(self.servers.get_next_port())

        res = self.servers.start_new_server(self.server1, 
                                            self.port3,
                                            self.servers.get_next_id(),
                                            "root", "temprep1")
        self.server3 = res[0]
        if not self.server3:
            raise MUTLibError("%s: Failed to create a new slave." % comment)

        new_server_str = self.build_connection_string(self.server3)
        new_master_str = self.build_connection_string(self.server1)
        
        cmd_str = "mysqlreplicate.py --master=%s " % new_server_str
        cmd_str += slave_str
        
        comment = "Test case 6 - error: No binary logging on master"
        cmd = cmd_str + "--rpl-user=rpl:whatsit "
        res = mutlib.System_test.run_test_case(self, 1, cmd, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        self.server3.exec_query("CREATE USER dummy@localhost")
        self.server3.exec_query("GRANT SELECT ON *.* TO dummy@localhost")
        self.server1.exec_query("CREATE USER dummy@localhost")
        self.server1.exec_query("GRANT SELECT ON *.* TO dummy@localhost")

        comment = "Test case 7 - error: replicate() fails"
        
        conn = self.get_connection_values(self.server3)
        
        cmd = "mysqlreplicate.py --slave=dummy@localhost"
        if conn[3] is not None:
            cmd += ":%s" % conn[3]
        if conn[4] is not None and conn[4] != "":
            cmd +=  ":%s" % conn[4]
        cmd += " --rpl-user=rpl:whatsit --master=" + new_master_str 
        res = mutlib.System_test.run_test_case(self, 1, cmd, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
            
        cmd_str = "mysqlreplicate.py %s %s" % (master_str, slave_str)

        res = self.server2.show_server_variable("server_id")
        if not res:
            raise MUTLibError("Cannot get master's server id.")
        master_serverid = res[0][1]
        
        self.server2.exec_query("SET GLOBAL server_id = 0")
        
        comment = "Test case 8 - error: Master server id = 0"
        cmd = cmd_str + "--rpl-user=rpl:whatsit "
        res = mutlib.System_test.run_test_case(self, 1, cmd, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        self.server2.exec_query("SET GLOBAL server_id = %s" % master_serverid)
            
        res = self.server1.show_server_variable("server_id")
        if not res:
            raise MUTLibError("Cannot get slave's server id.")
        slave_serverid = res[0][1]
        
        self.server1.exec_query("SET GLOBAL server_id = 0")
        
        comment = "Test case 9 - error: Slave server id = 0"
        cmd = cmd_str + "--rpl-user=rpl:whatsit "
        res = mutlib.System_test.run_test_case(self, 1, cmd, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        self.server1.exec_query("SET GLOBAL server_id = %s" % slave_serverid)

        comment = "Test case 10 - --master-log-pos but no log file"
        cmd_opts = "--master-log-pos=96 "
        res = mutlib.System_test.run_test_case(self, 2, cmd+cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        comment = "Test case 11 - --master-log-file and --start-from-beginning"
        cmd_opts = "--master-log-file='mysql_bin.00005' --start-from-beginning"
        res = mutlib.System_test.run_test_case(self, 2, cmd+cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        comment = "Test case 12 - --master-log-pos and --start-from-beginning"
        cmd_opts = "--master-log-pos=96 --start-from-beginning"
        res = mutlib.System_test.run_test_case(self, 2, cmd+cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        comment = "Test case 13 - --master-log-file+pos and --start-from-beginning"
        cmd_opts = "--master-log-pos=96 --start-from-beginning "
        cmd_opts += "--master-log-file='mysql_bin.00005'"
        res = mutlib.System_test.run_test_case(self, 2, cmd+cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        # Mask known platform-dependent lines
        self.mask_result("Error 2005:", "(1", '#######')
        self.replace_result("ERROR: Query failed. 1227: Access denied;",
                            "ERROR: Query failed. 1227: Access denied;\n")

        self.replace_result("Error 2002: Can't connect to",
                            "Error ####: Can't connect to local MySQL server "
                            "####...\n")

        self.replace_result("Error 2003: Can't connect to",
                            "Error ####: Can't connect to local MySQL server "
                            "####...\n")

        return True

    def get_result(self):
        return self.compare(__name__, self.results)
    
    def record(self):
        return self.save_result_file(__name__, self.results)
    
    def cleanup(self):
        if self.server3:
            res = self.servers.stop_server(self.server3)
            self.servers.clear_last_port()
            self.server3 = None
        return replicate.test.cleanup(self)



