#!/usr/bin/env python

import os
import check_rpl
import mutlib
from mysql.utilities.exception import MUTLibError

class test(check_rpl.test):
    """check replication conditions
    This test runs the mysqlrplcheck utility on a known master-slave topology
    to test various errors. It uses the check_rpl test as a parent for
    setup and teardown methods.
    
    Note: Many of the errors from the mysqlreplicate utility are not included
    in this test. Additionally, errors that require unique setup conditions
    cannot be tested easily. Thus, the errors represented in this test cover
    only the mysqlrplcheck utility and command/rpl.py file.
    """

    def check_prerequisites(self):
        return check_rpl.test.check_prerequisites(self)

    def setup(self):
        return check_rpl.test.setup(self)

    def run(self):
        self.res_fname = "result.txt"

        master_str = "--master=%s" % self.build_connection_string(self.server2)
        slave_str = " --slave=%s" % self.build_connection_string(self.server1)
        conn_str = master_str + slave_str
        
        cmd = "mysqlreplicate.py --rpl-user=rpl:rpl " 
        try:
            res = self.exec_util(cmd, self.res_fname)
        except MUTLibError, e:
            raise MUTLibError(e.errmsg)

        cmd_str = "mysqlrplcheck.py " + conn_str

        comment = "Test case 1 - master parameter invalid"
        cmd_opts = " %s --master=root_root_root" % slave_str
        res = mutlib.System_test.run_test_case(self, 2, cmd_str+cmd_opts,
                                                   comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
            
        comment = "Test case 2 - slave parameter invalid"
        cmd_opts = " %s --slave=root_root_root" % master_str
        res = mutlib.System_test.run_test_case(self, 2, cmd_str+cmd_opts,
                                                   comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        comment = "Test case 3 - same server"
        same_str = self.build_connection_string(self.server2)
        cmd_opts = " --master=%s --slave=%s" % (same_str, same_str)
        res = mutlib.System_test.run_test_case(self, 1, cmd_str+cmd_opts,
                                                   comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        comment = "Test case 4 - error: invalid login to server (master)"
        res = mutlib.System_test.run_test_case(self, 1, cmd_str +
                        slave_str + " --master=nope@nada:localhost:5510",
                        comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        conn_values = self.get_connection_values(self.server1)
        
        comment = "Test case 5 - error: invalid login to server (slave)"
        res = mutlib.System_test.run_test_case(self, 1, cmd_str +
                        master_str + " --slave=nope@nada:localhost:5511",
                        comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        self.do_replacements()

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
        return check_rpl.test.cleanup(self)



