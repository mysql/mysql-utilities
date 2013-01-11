#!/usr/bin/env python

import os
import copy_user

from mysql.utilities.exception import MUTLibError

class test(copy_user.test):
    """clone user parameter checking
    This test exercises the parameters for the clone user utility. It uses
    the copy_user test as a parent for setup and teardown methods.
    """

    def check_prerequisites(self):
        return copy_user.test.check_prerequisites(self)

    def setup(self):
        return copy_user.test.setup(self)

    def run(self):
        self.res_fname = "result.txt"

        from_conn = "--source=" + self.build_connection_string(self.server1)
        to_conn = "--destination=" + self.build_connection_string(self.server2)
        cmd_str = "mysqluserclone.py %s %s " % (from_conn, to_conn)

        comment = "Test case 1 - show the grant statements"
        res = self.run_test_case(0, cmd_str + " --dump joe_nopass@user " + \
                                 "jack@user john@user jill@user", comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        comment = "Test case 2 - show the help"
        res = self.run_test_case(0, cmd_str + " --help", comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        comment = "Test case 3 - use the quiet parameter"
        res = self.run_test_case(0, cmd_str + "joe_nopass@user --force" + \
                                 " jack@user john@user jill@user --quiet ",
                                 comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        cmd_str = "mysqluserclone.py --source=%s" % \
                  self.build_connection_string(self.server2)
        comment = "Test case 4 - use --dump and --list to show all users"
        res = self.run_test_case(0, cmd_str + " --list --dump --format=csv",
                                 comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
            
        self.remove_result("root,")
        self.remove_result("# Dumping grants for user 'root'")
        self.remove_result("GRANT ALL PRIVILEGES ON *.* TO 'root'")
        self.remove_result("GRANT PROXY ON ''@'' TO 'root'")
        self.remove_result("# Cannot show grants for user")

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        return copy_user.test.cleanup(self)
