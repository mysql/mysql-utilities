#!/usr/bin/env python

import os
import replicate
import mutlib
from mysql.utilities.exception import MUTLibError

class test(replicate.test):
    """check replication conditions
    This test runs the mysqlrplcheck utility on a known master-slave topology.
    It uses the replicate test as a parent for setup and teardown methods.
    """

    def check_prerequisites(self):
        if self.servers.get_server(0).check_version_compat(5, 6, 5):
            raise MUTLibError("Test requires server version prior to 5.6.5")
        return replicate.test.check_prerequisites(self)

    def setup(self):
        return replicate.test.setup(self)

    def run(self):
        self.res_fname = "result.txt"

        master_str = "--master=%s" % self.build_connection_string(self.server2)
        slave_str = " --slave=%s" % self.build_connection_string(self.server1)
        conn_str = master_str + slave_str
        
        cmd = "mysqlreplicate.py --rpl-user=rpl:rpl %s" % conn_str
        try:
            res = self.exec_util(cmd, self.res_fname)
        except MUTLibError, e:
            raise MUTLibError(e.errmsg)

        cmd_str = "mysqlrplcheck.py " + conn_str

        comment = "Test case 1 - normal run"
        res = mutlib.System_test.run_test_case(self, 0, cmd_str, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
            
        comment = "Test case 2 - verbose run"
        cmd_opts = " -vv"
        res = mutlib.System_test.run_test_case(self, 0, cmd_str+cmd_opts,
                                                   comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        comment = "Test case 3 - with show slave status"
        cmd_opts = " -s"
        res = mutlib.System_test.run_test_case(self, 0, cmd_str+cmd_opts,
                                                   comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
            
        self.do_replacements()

        return True

    def do_replacements(self):
        
        self.replace_result(" master id = ",
                            " master id = XXXXX\n")
        self.replace_result("  slave id = ",
                            "  slave id = XXXXX\n")
            
        self.replace_result("               Master_Log_File :",
                            "               Master_Log_File : XXXXX\n")
        self.replace_result("           Read_Master_Log_Pos :",
                            "           Read_Master_Log_Pos : XXXXX\n")
        self.replace_result("                   Master_Host :",
                            "                   Master_Host : XXXXX\n")
        self.replace_result("                   Master_Port :",
                            "                   Master_Port : XXXXX\n")
        
        self.replace_result("                Relay_Log_File :",
                            "                Relay_Log_File : XXXXX\n")
        self.replace_result("         Relay_Master_Log_File :",
                            "         Relay_Master_Log_File : XXXXX\n")
        self.replace_result("                 Relay_Log_Pos :",
                            "                 Relay_Log_Pos : XXXXX\n")
        self.replace_result("           Exec_Master_Log_Pos :",
                            "           Exec_Master_Log_Pos : XXXXX\n")
        self.replace_result("               Relay_Log_Space :",
                            "               Relay_Log_Space : XXXXX\n")
        
        self.replace_result("  Master lower_case_table_names:",
                            "  Master lower_case_table_names: XX\n")
        self.replace_result("   Slave lower_case_table_names:",
                            "   Slave lower_case_table_names: XX\n")
        self.remove_result("   Replicate_Ignore_Server_Ids :")
        self.remove_result("              Master_Server_Id :")
    
    def get_result(self):
        return self.compare(__name__, self.results)
    
    def record(self):
        return self.save_result_file(__name__, self.results)
    
    def cleanup(self):
        return replicate.test.cleanup(self)



