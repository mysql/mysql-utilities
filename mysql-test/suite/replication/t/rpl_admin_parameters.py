#!/usr/bin/env python

import os
import mutlib
import rpl_admin
from mysql.utilities.exception import MUTLibError

_LOGNAME = "temp_log.txt"
_LOG_ENTRIES = [
    "2012-03-11 15:55:33 PM INFO TEST MESSAGE 1.\n",
    "2022-04-21 15:55:33 PM INFO TEST MESSAGE 2.\n",
]

class test(rpl_admin.test):
    """test replication administration commands
    This test exercises the mysqlrpladmin utility parameters.
    It uses the rpl_admin test for setup and teardown methods.
    """

    # Some of the parameters cannot be tested because they are threshold
    # values used in timing. These include --ping, --timeout, --max-position,
    # and --seconds-behind. We include a test case for regression that
    # specifies these options but does not test them.

    def check_prerequisites(self):
        return rpl_admin.test.check_prerequisites(self)

    def setup(self):
        return rpl_admin.test.setup(self)

    def run(self):
        self.res_fname = "result.txt"
        
        base_cmd = "mysqlrpladmin.py --ping=5 --timeout=7 " + \
                   "--seconds-behind=30 --max-position=100 "

        master_conn = self.build_connection_string(self.server1).strip(' ')
        slave1_conn = self.build_connection_string(self.server2).strip(' ')
        slave2_conn = self.build_connection_string(self.server3).strip(' ')
        slave3_conn = self.build_connection_string(self.server4).strip(' ')
        
        master_str = "--master=" + master_conn
        slaves_str = "--slaves=" + \
                     ",".join([slave1_conn, slave2_conn, slave3_conn])

        comment = "Test case 1 - show help"
        cmd_str = base_cmd + " --help"
        res = mutlib.System_test.run_test_case(self, 0, cmd_str, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        comment = "Test case 2 - test slave discovery"
        cmd_str = "%s %s " % (base_cmd, master_str) 
        cmd_opts = " --discover-slaves-login=root:root health"
        res = mutlib.System_test.run_test_case(self, 0, cmd_str+cmd_opts,
                                               comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)            
        
        comment = "Test case 3 - switchover with verbosity"
        cmd_str = "%s %s " % (base_cmd, master_str)
        cmd_opts = " --discover-slaves-login=root:root --verbose switchover "
        cmd_opts += " --demote-master --no-health --new-master=%s" % slave1_conn
        res = mutlib.System_test.run_test_case(self, 0, cmd_str+cmd_opts,
                                               comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        comment = "Test case 4 - switchover with quiet"
        cmd_str = "%s --master=%s " % (base_cmd, slave1_conn)
        cmd_opts = " --discover-slaves-login=root:root --quiet switchover "
        cmd_opts += " --demote-master --new-master=%s" % master_conn
        cmd_opts += " --log=%s --log-age=1 " % _LOGNAME
        res = mutlib.System_test.run_test_case(self, 0, cmd_str+cmd_opts,
                                               comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
            
        # Now check the log and dump its entries
        log_file = open(_LOGNAME, "r")
        self.results.append("A switchover writes %s entries in the log.\n" %
                            len(log_file.readlines()))
        log_file.close()
            
        # Now overwrite the log file and populate with known 'old' entries
        log_file = open(_LOGNAME, "w+")
        log_file.writelines(_LOG_ENTRIES)
        self.results.append("There are (before) %s entries in the log.\n" %
                            len(_LOG_ENTRIES))
        log_file.close()
        
        comment = "Test case 5 - switchover with logs"
        cmd_str = "%s %s " % (base_cmd, master_str)
        cmd_opts = " --discover-slaves-login=root:root switchover "
        cmd_opts += " --demote-master --new-master=%s " % slave1_conn
        cmd_opts += " --log=%s --log-age=1 " % _LOGNAME
        res = mutlib.System_test.run_test_case(self, 0, cmd_str+cmd_opts,
                                               comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        
        # Now check the log and dump its entries
        log_file = open(_LOGNAME, "r")
        self.results.append("There are (after) %s entries in the log.\n" %
                            len(log_file.readlines()))
        log_file.close()
        try:
            os.unlink(_LOGNAME)
        except:
            pass
        
        comment = "Test case 6 - attempt risky switchover without force"
        cmd_str = "%s --master=%s " % (base_cmd, slave2_conn)
        new_slaves = " --slaves=" + ",".join([master_conn, slave1_conn, slave3_conn])
        cmd_opts = new_slaves + " switchover "
        cmd_opts += " --new-master=%s " % slave2_conn
        res = mutlib.System_test.run_test_case(self, 0, cmd_str+cmd_opts,
                                               comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        comment = "Test case 7 - attempt risky switchover with --force"
        cmd_str = "%s --master=%s --force " % (base_cmd, slave2_conn)
        new_slaves = " --slaves=" + ",".join([master_conn, slave1_conn, slave3_conn])
        cmd_opts = new_slaves + " switchover "
        cmd_opts += " --new-master=%s " % slave2_conn
        res = mutlib.System_test.run_test_case(self, 0, cmd_str+cmd_opts,
                                               comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        
        # Now we return the topology to its original state for other tests
        rpl_admin.test.reset_topology(self)

        # Mask out non-deterministic data
        rpl_admin.test.do_masks(self)
        
        self.replace_substring("%s" % self.server1.get_version(),
                               "XXXXXXXXXXXXXXXXXXXXXX")
        self.replace_result("# CHANGE MASTER TO MASTER_HOST",
                            "# CHANGE MASTER TO MASTER_HOST [...]\n")

        return True

    def get_result(self):
        return self.compare(__name__, self.results)
    
    def record(self):
        return self.save_result_file(__name__, self.results)
    
    def cleanup(self):
        try:
            os.rmdir("watchout_here")
        except:
            pass
        try:
            os.rmdir("watchout_here_too")
        except:
            pass
        return rpl_admin.test.cleanup(self)



