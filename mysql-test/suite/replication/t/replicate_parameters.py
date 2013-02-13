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
import replicate
from mysql.utilities.exception import MUTLibError

class test(replicate.test):
    """check parameters for the replicate utility
    This test executes the replicate utility parameters. It uses the
    replicate test as a parent for setup and teardown methods.
    """

    def check_prerequisites(self):
        return replicate.test.check_prerequisites(self)

    def setup(self):
        return replicate.test.setup(self)

    def run(self):
        self.res_fname = "result.txt"
                      
        comment = "Test case 1 - use the test feature"
        res = self.run_test_case(self.server2, self.server1, self.s2_serverid,
                                 comment, "--test-db=db_not_there_yet", True)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        try:
            res = self.server2.exec_query("STOP SLAVE")
        except:
            pass

        comment = "Test case 2 - show the help"
        res = self.run_test_case(self.server1, self.server2, self.s1_serverid,
                                 comment, "--help", True)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        comment = "Test case 3 - use the verbose feature"
        res = self.run_test_case(self.server2, self.server1, self.s2_serverid,
                                 comment, " --verbose", True)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        try:
            res = self.server2.exec_query("STOP SLAVE")
        except:
            pass
        
        comment = "Test case 4 - use the start-from-beginning feature"
        res = self.run_test_case(self.server2, self.server1, self.s2_serverid,
                                 comment, " --start-from-beginning", True)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        self.remove_result("# status:")
        self.remove_result("# error: ")
        self.remove_result("# CHANGE MASTER TO MASTER_HOST")
        self.mask_result("# master id =", "= ", "= XXX")
        self.mask_result("#  slave id =", "= ", "= XXX")
        self.replace_result("# master uuid = ",
                            "# master uuid = XXXXX\n")
        self.replace_result("#  slave uuid = ",
                            "#  slave uuid = XXXXX\n")

        return True

    def get_result(self):
        return self.compare(__name__, self.results)
    
    def record(self):
        return self.save_result_file(__name__, self.results)
    
    def cleanup(self):
        return replicate.test.cleanup(self)


