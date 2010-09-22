#!/usr/bin/env python

import os
import mysql_test
import mysql.utilities.common as mysql
from mysql.utilities.common import MySQLUtilError

class test(mysql_test.System_test):
    """copy user
    This test copies a user from one server to another copying all grants.
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
                return False
        self.server2 = self.servers.get_server(1)
        self.drop_all()
        data_file = self.testdir + "/data/basic_users.sql"
        return self.server1.read_and_exec_SQL(data_file, self.verbose, True)
        
    def show_user_grants(self, server, user):
        query = "SHOW GRANTS FOR %s" % (user)
        try:
            res = server.exec_query(query)
            if res is not None:
                for row in res:
                    self.results.append(row[0]+"\n")
        except MySQLUtilError, e:
            pass
            
    def run(self):
        self.res_fname = self.testdir + "result.txt"

        from_conn = "--source=" + self.build_connection_string(self.server1)
        to_conn = "--destination=" + self.build_connection_string(self.server2)
        cmd_str = "mysqluserclone.py %s %s " % (from_conn, to_conn)
       
        # Test case 1 - copy a user to a single user
        comment = "Test case 1 - copy a single user joe_pass@user to " + \
                  "a single user: jill@user"
        res = self.run_test_case(0, cmd_str + " joe_pass@user jill:duh@user",
                                 comment)
        if not res:
            return False

        self.show_user_grants(self.server2, "'jill'@'user'")

        # Test case 2 - copy a user to a multiple users
        comment= "Test case 2 - copy a single user amy_nopass@user to " + \
                            "multiple users: jack@user and john@user"
        res = self.run_test_case(0, cmd_str + " amy_nopass@user " +
                                 "jack:duh@user john@user", comment)
        if not res:
            return False

        self.show_user_grants(self.server2,"jack@user")
        self.show_user_grants(self.server2,"john@user")

        # Test case 3 - attempt to copy a non-existant user
        comment= "Test case 3 - attempt to copy a non-existant user"
        res = self.run_test_case(1, cmd_str + " nosuch@user jack@user",
                                 comment)
        if not res:
            return False

        # Test case 4 - attempt to copy a user to a user that already exists
        comment= "Test case 4 - attempt to copy a user to a user that " + \
                 "already exists"
        res = self.run_test_case(1, cmd_str + " joe_pass@user jill:duh@user",
                                 comment)
        if not res:
            return False

        # Test case 5 - attempt to copy a user to a user that already exists
        #               with overwrite
        self.show_user_grants(self.server2, "jill@user")
        comment= "Test case 5 - attempt to copy a user to a user that " + \
                 "already exists with --force"
        res = self.run_test_case(0, cmd_str + " joe_pass@user " +
                                 "jill:duh@user --force", comment)
        if not res:
            return False
        # No show overwritten grants
        self.show_user_grants(self.server2, "jill@user")

        return True

    def get_result(self):
        return self.compare(__name__, self.results)
    
    def record(self):
        return self.save_result_file(__name__, self.results)
    
    def drop_user(self, user_name, server):
        user = mysql.User(server, user_name, False)
        if user.exists():
            res = user.drop()
            if res is not None:
                print "cleanup: failed to drop user %s" % user_name
        return True

    def drop_all(self):
        res = self.drop_user("joe_pass@user", self.server1)
        res = self.drop_user("'joe_nopass'@'user'", self.server1)
        res = self.drop_user("'amy_nopass'@'user'", self.server1)
        res = self.drop_user("'jill'@'user'", self.server1)
        res = self.drop_user("'jack'@'user'", self.server1)
        res = self.drop_user("'john'@'user'", self.server1)
        res = self.drop_user("joe_pass@user", self.server2)
        res = self.drop_user("'joe_nopass'@'user'", self.server2)
        res = self.drop_user("'amy_nopass'@'user'", self.server2)
        res = self.drop_user("'jill'@'user'", self.server2)
        res = self.drop_user("'jack'@'user'", self.server2)
        res = self.drop_user("'john'@'user'", self.server2)
        query = "DROP DATABASE util_test"
        try:
            res = self.server1.exec_query(query)
        except:
            pass
        try:
            res = self.server2.exec_query(query)
        except:
            pass
    
    def cleanup(self):
        if self.res_fname:
            os.unlink(self.res_fname)
        self.drop_all()
        return True





