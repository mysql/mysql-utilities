#!/usr/bin/env python

import os
import clone_user

class test(clone_user.test):
    """clone user error conditions
    This test ensures the known error conditions are tested. It uses the
    cloneuser test as a parent for setup and teardown methods.
     """

    def check_prerequisites(self):
        return clone_user.test.check_prerequisites(self)

    def setup(self):
        return clone_user.test.setup(self)
            
    def run(self):
        self.res_fname = self.testdir + "result.txt"

        from_conn = "--source=" + self.build_connection_string(self.server1)
        to_conn = "--destination=" + self.build_connection_string(self.server1)
       
        cmd_str = "mysqluserclone.py --source=noone:nope@localhost:3306 " + \
                  to_conn
        comment = "Test case 1 - error: invalid login to source server"
        res = self.run_test_case(1, cmd_str + " a@b b@c", comment)
        if not res:
            return False

        cmd_str = "mysqluserclone.py --destination=noone:nope@localhost:3306 " + \
                  from_conn
        comment = "Test case 2 - error: invalid login to destination server"
        res = self.run_test_case(1, cmd_str + " a@b b@c", comment)
        if not res:
            return False

        cmd_str = "mysqluserclone.py %s %s " % (from_conn, to_conn)
        comment = "Test case 3 - error: no arguments"
        res = self.run_test_case(1, cmd_str, comment)
        if not res:
            return False

        comment = "Test case 4 - error: no new user"
        res = self.run_test_case(1, cmd_str + "joenopass@localhost", comment)
        if not res:
            return False

        comment = "Test case 5 - error: cannot use dump and silent together"
        res = self.run_test_case(1, cmd_str + " root@localhost " \
                                 " x@f --silent --dump", comment)
        if not res:
            return False

        return True

    def get_result(self):
        return self.compare(__name__, self.results)
    
    def record(self):
        return self.save_result_file(__name__, self.results)
    
    def cleanup(self):
        return clone_user.test.cleanup(self)


# Don't allow this file to execute as a script       
if (__name__ == '__main__'):
    print "ERROR: This is not an executable file!"
    exit(1)



