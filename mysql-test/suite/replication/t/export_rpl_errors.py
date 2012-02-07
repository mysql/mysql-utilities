#!/usr/bin/env python

import os
import replicate
import mutlib
from mysql.utilities.exception import MUTLibError

_RPL_OPTIONS = ["--rpl-file=test.txt", "--comment-rpl", "--rpl-user=root"]

class test(replicate.test):
    """check replication errors for export utility
    This test executes a series of export database operations on a single
    server using a variety of replication options exercising the errors
    associated with the --rpl commands and processing.
    """

    def check_prerequisites(self):
        return replicate.test.check_prerequisites(self)

    def setup(self):
        result = replicate.test.setup(self)

        index = self.servers.find_server_by_name("new_server1")
        if index >= 0:
            self.server3 = self.servers.get_server(index)
            try:
                res = self.server3.show_server_variable("server_id")
            except MUTLibError, e:
                raise MUTLibError("Cannot get new server server_id: %s" %
                                  e.errmsg)
            self.s3_serverid = int(res[0][1])
        else:
            self.s3_serverid = self.servers.get_next_id()
            res = self.servers.spawn_new_server(self.server0, self.s1_serverid,
                                               "new_server1")
            if not res:
                raise MUTLibError("Cannot spawn replication new server.")
            self.server3 = res[0]
            self.servers.add_new_server(self.server3, True)
            
        try:
            self.server1.exec_query("DROP DATABASE util_test")
        except:
            pass

        return result
    
    def run(self):
        self.res_fname = "result.txt"
        from_conn = "--server=" + self.build_connection_string(self.server1)

        test_num = 1
        # Check --rpl option errors    
        for option in _RPL_OPTIONS:
            cmd_str = "mysqldbexport.py %s util_test " % from_conn
            comment = "Test case %s - error: %s but no --rpl" % \
                      (test_num, option)
            res = mutlib.System_test.run_test_case(self, 2, cmd_str + option,
                                                   comment)
            if not res:
                raise MUTLibError("%s: failed" % comment)
            test_num += 1
            
        all_options = " ".join(_RPL_OPTIONS)
        comment = "Test case %s - error: %s but no --rpl" % \
                  (test_num, all_options)
        res = mutlib.System_test.run_test_case(self, 2, cmd_str + all_options,
                                               comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        test_num += 1
        
        cmd_str = "mysqldbexport.py util_test --export=both " + \
                  "--rpl-user=rpl:rpl %s " % from_conn

        comment = "Test case %s - error: --rpl-file bad path" % test_num
        option = " --rpl=master --rpl-file=/bad/path/not/there.atall "
        res = mutlib.System_test.run_test_case(self, 1, cmd_str + option,
                                               comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        test_num += 1
        
        self.server1.exec_query("CREATE DATABASE util_test")
        self.server1.exec_query("CREATE USER imnotamouse@localhost")

        cmd_str = "mysqldbexport.py util_test --export=data %s " % from_conn

        comment = "Test case %s - warning: --rpl-user missing" % test_num
        option = " --rpl=master "
        res = mutlib.System_test.run_test_case(self, 0, cmd_str + option,
                                               comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        test_num += 1

        comment = "Test case %s - error: --rpl-user missing user" % test_num
        option = " --rpl=master --rpl-user=missing "
        res = mutlib.System_test.run_test_case(self, 1, cmd_str + option,
                                               comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        test_num += 1

        comment = "Test case %s - error: --rpl-user missing privileges" % \
                  test_num
        option = " --rpl=master --rpl-user=imnotamouse "
        res = mutlib.System_test.run_test_case(self, 1, cmd_str + option,
                                               comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        test_num += 1

        self.server1.exec_query("DROP DATABASE util_test")
        self.server1.exec_query("DROP USER imnotamouse@localhost")
        self.server2.exec_query("STOP SLAVE")
        self.server2.exec_query("RESET SLAVE")

        comment = "Test case %s - error: slave not connected" % test_num
        option = " --rpl=slave "
        res = mutlib.System_test.run_test_case(self, 1, cmd_str + option,
                                               comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        test_num += 1
        
        from_conn = "--server=" + self.build_connection_string(self.server3)

        cmd_str = "mysqldbexport.py util_test --export=both " + \
                  "--rpl-user=rpl:rpl %s " % from_conn

        comment = "Test case %s - error: no binlog" % test_num
        option = " --rpl=master "
        res = mutlib.System_test.run_test_case(self, 1, cmd_str + option,
                                               comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        test_num += 1

        self.replace_result("CHANGE MASTER", "CHANGE MASTER <goes here>\n")
        self.replace_result("# CHANGE MASTER", "# CHANGE MASTER <goes here>\n")
    
        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        return replicate.test.cleanup(self)

