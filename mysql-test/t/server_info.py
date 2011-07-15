#!/usr/bin/env python

import os
import mutlib
from mysql.utilities.exception import MUTLibError

class test(mutlib.System_test):
    """simple db serverinfo
    This test executes the serverinfo utility.
    """

    def check_prerequisites(self):
        # Need at least one server.
        self.server1 = None
        self.server2 = None
        self.need_server = False
        if not self.check_num_servers(2):
            self.need_server = True
        return self.check_num_servers(1)

    def setup(self):
        self.server1 = self.servers.get_server(0)
        if self.need_server:
            try:
                self.servers.spawn_new_servers(2)
            except MUTLibError, e:
                raise MUTLibError("Cannot spawn needed servers: " + e.errmsg)
        self.server2 = self.servers.get_server(1)
        return True
    
    def do_replacements(self):
        # Mask out this information to make result file deterministic
        self.replace_result("        version:", "        version: XXXX\n")
        self.replace_result("        datadir:", "        datadir: XXXX\n")
        self.replace_result("        basedir:", "        basedir: XXXX\n")
        self.replace_result("     plugin_dir:", "     plugin_dir: XXXX\n")
        self.replace_result("    config_file:", "    config_file: XXXX\n")
        self.replace_result("     binary_log:", "     binary_log: XXXX\n")
        self.replace_result(" binary_log_pos:", " binary_log_pos: XXXX\n")
        self.replace_result("      relay_log:", "      relay_log: XXXX\n")
        self.replace_result("  relay_log_pos:", "  relay_log_pos: XXXX\n")
        self.replace_result("         server: localhost:",
                            "         server: localhost: XXXX\n")

    def run(self):
        self.server1 = self.servers.get_server(0)
        self.res_fname = "result.txt"
        
        s2_conn = "--server=" + self.build_connection_string(self.server2)
       
        cmd_str = "mysqlserverinfo.py %s " % s2_conn

        comment = "Test case 1 - basic serverinfo "
        cmd_opts = " --format=vertical "
        res = self.run_test_case(0, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        self.do_replacements()

        # NOTICE: Cannot test the -d option with a comparative result file
        #         because it is going to be different on every machine.
        #         Thus, this test case will have to be checked independently.
     
        self.res_fname_temp = "result2.txt"
   
        comment = "Test case 2 - basic serverinfo with -d option"
        self.results.append(comment+'\n')
        cmd_opts = " --format=vertical -d "
        res = 0
        try:
            res = self.exec_util(cmd_str + cmd_opts, self.res_fname_temp)
        except MUTLibError, e:
            raise MUTLibError(e.errmsg)
        if res != 0:
            return False
        
        return True
          
    def get_result(self):
        # First, check result of test case 2
        found = False
        file = open(self.res_fname_temp, 'r')
        for line in file.readlines():
            if line[0:19] == "Defaults for server":
                found = True
                break
        file.close()
        if self.res_fname_temp:
            os.unlink(self.res_fname_temp)
        if not found:
            raise MUTLibError("Test Case 2 failed. No defaults found.")
        return self.compare(__name__, self.results)
    
    def record(self):
        return self.save_result_file(__name__, self.results)
    
    def cleanup(self):
        if self.res_fname:
            os.unlink(self.res_fname)
        return True




