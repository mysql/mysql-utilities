#!/usr/bin/env python

import os
import mutlib
from mysql.utilities.exception import MUTLibError, UtilDBError

class test(mutlib.System_test):
    """simple db diff
    This test executes a simple diff of two databases on separate servers.
    """

    def check_prerequisites(self):
        self.check_gtid_unsafe()
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
                raise MUTLibError("Cannot spawn needed servers: %s" % \
                                   e.errmsg)
        self.server2 = self.servers.get_server(1)
        self.drop_all()
        data_file = os.path.normpath("./std_data/basic_data.sql")
        try:
            res = self.server1.read_and_exec_SQL(data_file, self.debug)
            res = self.server2.read_and_exec_SQL(data_file, self.debug)
        except MUTLibError, e:
            raise MUTLibError("Failed to read commands from file %s: " % \
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
        except UtilDBError, e:
            raise MUTLibError("Failed to execute query: %s" % e.errmsg)

        return True
    
    def run(self):
        self.server1 = self.servers.get_server(0)
        self.res_fname = "result.txt"
        
        s1_conn = "--server1=" + self.build_connection_string(self.server1)
        s2_conn = "--server2=" + self.build_connection_string(self.server2)
        s2_conn_dupe = "--server2=" + self.build_connection_string(self.server1)
       
        cmd_str = "mysqldiff.py %s %s " % (s1_conn, s2_conn)

        comment = "Test case 1 - diff a sample database"
        res = self.run_test_case(1, cmd_str + "util_test:util_test", comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        comment = "Test case 2 - diff a single object - not same"
        res = self.run_test_case(1, cmd_str + "util_test.t2:util_test.t2",
                                 comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        comment = "Test case 3 - diff a single object - is same"
        res = self.run_test_case(0, cmd_str + "util_test.t3:util_test.t3",
                                 comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        comment = "Test case 4 - diff multiple objects - are same"
        res = self.run_test_case(0, cmd_str + "util_test.t3:util_test.t3 "
                                 "util_test.t4:util_test.t4",
                                 comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        comment = "Test case 5 - diff multiple objects + database - some same"
        res = self.run_test_case(1, cmd_str + "util_test.t3:util_test.t3 "
                                 "util_test.t4:util_test.t4 "
                                 "util_test:util_test --force ",
                                 comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
            
        # execute a diff on the same server to test messages
        
        self.server1.exec_query("CREATE DATABASE util_test1")
        
        comment = "Test case 6 - diff two databases on same server w/server2"
        cmd_str = "mysqldiff.py %s %s " % (s1_conn, s2_conn_dupe)
        res = self.run_test_case(1, cmd_str + "util_test:util_test1 ",
                                 comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
            
        comment = "Test case 7 - diff two databases on same server"
        cmd_str = "mysqldiff.py %s " % s1_conn
        res = self.run_test_case(1, cmd_str + "util_test:util_test1 ",
                                 comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        # The following are necessary due to changes in character spaces
        # introduced with Python 2.7.X in the difflib.
        
        self.replace_result("+++ util_test.t1", "+++ util_test.t1\n")
        self.replace_result("+++ util_test.t2", "+++ util_test.t2\n")
        self.replace_result("--- util_test.t1", "--- util_test.t1\n")
        self.replace_result("--- util_test.t2", "--- util_test.t2\n")

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
        self.drop_db(self.server1, "util_test1")
        self.drop_db(self.server2, "util_test")
        return True

    def cleanup(self):
        if self.res_fname:
            os.unlink(self.res_fname)
        return self.drop_all()




