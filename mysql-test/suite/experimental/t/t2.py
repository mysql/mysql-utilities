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
import mutlib

class test(mutlib.System_test):
    """Experimental test #2
    This is a demonstration of a sample test using comparative results.
    In this test, we simulate the execution of a test case and compare
    the results returning a failed result and a diff of the result file.
    """
    
    def check_prerequisites(self):
        return self.check_num_servers(0)
    
    def setup(self):
        return True
    
    def run(self):

        # A result list will be generated here by the callee.
        self.ret_val = []
        self.ret_val.append("Line 1\n")
        self.ret_val.append("Line 2\n")

        # Note: comment out the next line and uncomment out the following line
        #       to see an unsuccessful test run
        self.ret_val.append("Line 3\n")
        #self.ret_val.append("Something wonky here\n")
        self.ret_val.append("Line 4\n")
        self.ret_val.append("Line 5\n")
        return True
        
    def get_result(self):

        # Returning a diff is easy - call the compare method with the
        # name of the test (__name__) and the string list where you stored
        # the results of the test run. Note: this could be a self-generated
        # list or the resulf of the exec_util() method.
        return self.compare(__name__, self.ret_val)

    def record(self):

        # We have a comparative test, so here I need to save result file.
        return self.save_result_file(__name__, self.ret_val)
            
    def cleanup(self):
        return True


