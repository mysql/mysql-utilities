#
# Copyright (c) 2010, 2013, Oracle and/or its affiliates. All rights reserved.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301 USA
#
import os
import clone_user

from mysql.utilities.exception import MUTLibError

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
        self.res_fname = "result.txt"

        from_conn = "--source=" + self.build_connection_string(self.server1)
        to_conn = "--destination=" + self.build_connection_string(self.server1)

        cmd_str = "mysqluserclone.py --source=noone:nope@localhost:3306 " + \
                  to_conn
        comment = "Test case 1 - error: invalid login to source server"
        res = self.run_test_case(1, cmd_str + " a@b b@c", comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        cmd_str = "mysqluserclone.py --destination=noone:nope@localhost:3306 " + \
                  from_conn
        comment = "Test case 2 - error: invalid login to destination server"
        res = self.run_test_case(1, cmd_str + " a@b b@c", comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        cmd_str = "mysqluserclone.py %s %s " % (from_conn, to_conn)
        comment = "Test case 3 - error: no arguments"
        res = self.run_test_case(2, cmd_str, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        comment = "Test case 4 - error: no new user"
        res = self.run_test_case(2, cmd_str + "joenopass@localhost", comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        comment = "Test case 5 - error: cannot use dump and quiet together"
        res = self.run_test_case(2, cmd_str + " root@localhost " \
                                 " x@f --quiet --dump", comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        cmd_str = "mysqluserclone.py --source=wikiwakawonky %s " % to_conn
        comment = "Test case 6 - error: cannot parser source connection"
        res = self.run_test_case(2, cmd_str + " root@localhost x@f", comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        cmd_str = "mysqluserclone.py --destination=wikiwakawonky %s " % \
                  from_conn
        comment = "Test case 7 - error: cannot parser destination connection"
        res = self.run_test_case(2, cmd_str + " root@localhost x@f", comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
            
        # Replace error code.
        self.replace_result("Error 1045", "Error XXXX: Access denied\n")
        self.replace_result("Error 2003", "Error XXXX: Access denied\n")
        self.replace_result("mysqluserclone.py: error: Source connection "
                            "values invalid",
                            "mysqluserclone.py: error: Source connection "
                            "values invalid\n")
        self.replace_result("mysqluserclone.py: error: Destination connection "
                            "values invalid",
                            "mysqluserclone.py: error: Destination connection "
                            "values invalid\n")

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        return clone_user.test.cleanup(self)
