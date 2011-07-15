#!/usr/bin/env python

import os
import compare_db
from mysql.utilities.exception import MUTLibError

class test(compare_db.test):
    """check errors for dbcompare
    This test executes a series of error conditions for the check database
    utility. It uses the compare_db test as a parent for setup and teardown
    methods.
    """

    def check_prerequisites(self):
        return compare_db.test.check_prerequisites(self)

    def setup(self):
        self.server1 = self.servers.get_server(0)
        if self.need_server:
            try:
                self.servers.spawn_new_servers(2)
            except MUTLibError, e:
                raise MUTLibError("Cannot spawn needed servers: " + e.errmsg)
        self.server2 = self.servers.get_server(1)
        self.drop_all()
        return True

    def run(self):
        self.server1 = self.servers.get_server(0)
        self.res_fname = "result.txt"

        s1_conn = "--server1=" + self.build_connection_string(self.server1)
        s2_conn = "--server2=" + self.build_connection_string(self.server2)
       
        cmd_str = "mysqldbcompare.py -a -vvv inventory:inventory "
        cmd_opts = "--server1=joeunk:@:dooer " + s2_conn
        comment = "Test case 1 - Invalid --server1 "
        res = self.run_test_case(2, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        cmd_opts = "--server2=joeunk:@:dooer " + s1_conn
        comment = "Test case 2 - Invalid --server2 "
        res = self.run_test_case(2, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        cmd_str = "mysqldbcompare.py %s %s" % (s1_conn, s2_conn)
        cmd_opts = " inventory.inventory" 
        comment = "Test case 3 - malformed argument%s " % cmd_opts
        res = self.run_test_case(1, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        
        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        return compare_db.test.cleanup(self)
