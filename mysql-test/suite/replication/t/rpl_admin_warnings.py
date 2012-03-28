#!/usr/bin/env python

import os
import mutlib
import rpl_admin
from mysql.utilities.exception import MUTLibError

class test(rpl_admin.test):
    """test replication administration commands
    This test exercises the mysqlrpladmin utility warnings concerning options.
    It uses the rpl_admin test for setup and teardown methods.
    """

    def check_prerequisites(self):
        return rpl_admin.test.check_prerequisites(self)

    def setup(self):
        return rpl_admin.test.setup(self)

    def run(self):
        self.res_fname = "result.txt"
        
        master_conn = self.build_connection_string(self.server1).strip(' ')
        slave1_conn = self.build_connection_string(self.server2).strip(' ')
        slave2_conn = self.build_connection_string(self.server3).strip(' ')
        slave3_conn = self.build_connection_string(self.server4).strip(' ')
        
        master_str = "--master=" + master_conn
        slaves_str = "--slaves=" + \
                     ",".join([slave1_conn, slave2_conn, slave3_conn])
        candidates_str = "--candidates=" + \
                         ",".join([slave1_conn, slave2_conn, slave3_conn])
        
        comment = "Test case 1 - warning for --exec* and not switchover or failover"
        cmd_str = "mysqlrpladmin.py --master=%s " % master_conn
        cmd_opts = " %s health --quiet --format=csv " % slaves_str
        cmd_opts += " --exec-before=dummy --exec-after=dummy"
        res = mutlib.System_test.run_test_case(self, 0, cmd_str+cmd_opts,
                                               comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        comment = "Test case 2 - warning for --candidate and not switchover"
        cmd_str = "mysqlrpladmin.py --master=%s " % master_conn
        cmd_opts = " %s health --quiet --format=csv " % slaves_str
        cmd_opts += " %s " % candidates_str
        res = mutlib.System_test.run_test_case(self, 0, cmd_str+cmd_opts,
                                               comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        comment = "Test case 3 - warning for --new-master and not switchover"
        cmd_str = "mysqlrpladmin.py --master=%s " % master_conn
        cmd_opts = " %s health --quiet --format=tab " % slaves_str
        cmd_opts += " --new-master=%s " % slave2_conn
        res = mutlib.System_test.run_test_case(self, 0, cmd_str+cmd_opts,
                                               comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        comment = "Test case 4 - warning for --format and not health or gtid"
        cmd_str = "mysqlrpladmin.py --master=%s " % master_conn
        cmd_opts = " %s stop --quiet --format=tab " % slaves_str
        res = mutlib.System_test.run_test_case(self, 0, cmd_str+cmd_opts,
                                               comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        # Now we return the topology to its original state for other tests
        rpl_admin.test.reset_topology(self)

        # Mask out non-deterministic data
        rpl_admin.test.do_masks(self)

        return True

    def get_result(self):
        return self.compare(__name__, self.results)
    
    def record(self):
        return self.save_result_file(__name__, self.results)
    
    def cleanup(self):
        return rpl_admin.test.cleanup(self)



