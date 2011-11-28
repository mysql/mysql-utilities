#!/usr/bin/env python

import os
import mutlib

from mysql.utilities.common.server import Server
from mysql.utilities.exception import MUTLibError

class test(mutlib.System_test):
    """clone server errors
    This test exercises the error conditions for mysqlserverclone.
    """

    def check_prerequisites(self):
        return self.check_num_servers(1)

    def setup(self):
        # No setup needed
        return True
    
    def run(self):
        self.res_fname = "result.txt"
        cmd_str = "mysqlserverclone.py --server=%s " % \
                  self.build_connection_string(self.servers.get_server(0))
       
        port1 = int(self.servers.get_next_port())
        newport = "--new-port=%d " % port1
        comment = "Test case 1 - error: no --new-data option"
        res = self.run_test_case(2, cmd_str, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        comment = "Test case 2 - error: no login"
        res = self.run_test_case(1, "mysqlserverclone.py " +
                                 "--server=root:root@nothere --new-data=/nada "
                                 "--new-id=7 " + newport, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        
        comment = "Test case 3 - error: cannot connect"
        res = self.run_test_case(1, "mysqlserverclone.py --server=root:nope@" +
                                 "nothere --new-data=/nada --new-id=7 " +
                                 "--root-password=nope " + newport,
                                 comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        # Mask known platform-dependent lines
        self.mask_result("Error 2003:", "2003", "####")
        self.replace_result("Error ####: Can't connect to MySQL server",
                            "Error ####: Can't connect to MySQL server"
                            " on 'nothere:####'\n")
       
        cmd_str += "--new-id=%d " % self.servers.get_next_id() + newport + \
                   " --root-password=root "
        comment = "Test case 4 - cannot create directory"
        res = self.run_test_case(1, cmd_str + "--new-data=/not/there/yes",
                                 comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        
        self.replace_result("#  -uroot", "#  -uroot [...]\n")
        
        return True

    def get_result(self):
        return self.compare(__name__, self.results)
    
    def record(self):
        return self.save_result_file(__name__, self.results)
    
    def cleanup(self):
        if self.res_fname:
            os.unlink(self.res_fname)
        return True

