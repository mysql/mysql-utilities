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
import t2

class test(t2.test):
    """Experimental test #4
    This is a demonstration of how to reuse other tests to run additional
    test cases. This is a sample test using comparative results.
    In this test, we reuse the test 't2' and simulate running a different
    utility. We reuse the prerequisite, setup, and cleanup of t2.
    """

    def check_prerequisites(self):
        return t2.test.check_prerequisites(self)
    
    def setup(self):
        return t2.test.setup(self)
    
    def run(self):

        # A result list will be generated here by the callee.
        self.ret_val = []
        self.ret_val.append("Wack-a-mole 1\n")
        # Note: comment out the next line and uncomment out the following line
        #       to see an unsuccessful test run
        self.ret_val.append("Wack-a-mole 2\n")
        #self.ret_val.append("Something hinky happened here\n")
        self.ret_val.append("Wack-a-mole 3\n")
        return True

    def get_result(self):
        return self.compare(__name__, self.ret_val)

    def record(self):
        return self.save_result_file(__name__, self.ret_val)
            
    def cleanup(self):
        return t2.test.cleanup(self)

