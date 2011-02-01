#!/usr/bin/env python

import os
import mysql_test
from mysql.utilities.exception import MySQLUtilError, MUTException

class test(mysql_test.System_test):
    """simple db diff
    This test executes a simple diff of two databases on separate servers.
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
            except MySQLUtilError, e:
                raise MUTException("Cannot spawn needed servers: %s" % \
                                   e.errmsg)
        self.server2 = self.servers.get_server(1)
        self.drop_all()
        data_file = os.path.normpath(self.testdir + "/data/basic_data.sql")
        try:
            res = self.server1.read_and_exec_SQL(data_file, self.debug)
            res = self.server2.read_and_exec_SQL(data_file, self.debug)
        except MySQLUtilError, e:
            raise MUTException("Failed to read commands from file %s: " % \
                               data_file + e.errmsg)
        try:
            # Now do some alterations...
            res = self.server2.exec_query("ALTER TABLE util_test.t1 ADD "
                                          "COLUMN b int")
            res = self.server2.exec_query("ALTER TABLE util_test.t2 "
                                          "ENGINE = MEMORY")
            # Event has time in its definition. Remove for deterministic return
            res = self.server1.exec_query("USE util_test;")
            res = self.server1.exec_query("DROP EVENT util_test.e1")
            res = self.server2.exec_query("USE util_test;")
            res = self.server2.exec_query("DROP EVENT util_test.e1")
        except MySQLUtilError, e:
            raise MUTException("Failed to execute query: %s" % e.errmsg)

        return True
    
    def run(self):
        self.server1 = self.servers.get_server(0)
        self.res_fname = self.testdir + "result.txt"
        
        s1_conn = "--server1=" + self.build_connection_string(self.server1)
        s2_conn = "--server2=" + self.build_connection_string(self.server2)
       
        cmd_str = "mysqldiff.py %s %s " % (s1_conn, s2_conn) + \
                  " --format=unified "

        comment = "Test case 1 - diff a sample database"
        res = self.run_test_case(1, cmd_str + "util_test:util_test", comment)
        if not res:
            raise MUTException("%s: failed" % comment)

        comment = "Test case 2 - diff a single object - not same"
        res = self.run_test_case(1, cmd_str + "util_test.t2:util_test.t2",
                                 comment)
        if not res:
            raise MUTException("%s: failed" % comment)

        comment = "Test case 3 - diff a single object - is same"
        res = self.run_test_case(0, cmd_str + "util_test.t3:util_test.t3",
                                 comment)
        if not res:
            raise MUTException("%s: failed" % comment)

        comment = "Test case 4 - diff multiple objects - are same"
        res = self.run_test_case(0, cmd_str + "util_test.t3:util_test.t3 "
                                 "util_test.t4:util_test.t4",
                                 comment)
        if not res:
            raise MUTException("%s: failed" % comment)

        comment = "Test case 5 - diff multiple objects + database - some same"
        res = self.run_test_case(1, cmd_str + "util_test.t3:util_test.t3 "
                                 "util_test.t4:util_test.t4 "
                                 "util_test:util_test --force ",
                                 comment)
        if not res:
            raise MUTException("%s: failed" % comment)

        return True
          
    def get_result(self):
        return self.compare(__name__, self.results)
    
    def record(self):
        return self.save_result_file(__name__, self.results)
    
    def drop_db(self, server, db):
        # Check before you drop to avoid warning
        try:
            res = server.exec_query("SHOW DATABASES LIKE 'util_%'")
        except:
            return True # Ok to exit here as there weren't any dbs to drop
        try:
            res = server.exec_query("DROP DATABASE %s" % db)
        except:
            return False
        return True
    
    def drop_all(self):
        self.drop_db(self.server1, "util_test")
        self.drop_db(self.server2, "util_test")
        return True

    def cleanup(self):
        if self.res_fname:
            os.unlink(self.res_fname)
        return self.drop_all()




