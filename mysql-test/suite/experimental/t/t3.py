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
    """Experimental test #3
    This example tests the return codes for the methods. Uncomment out the
    False returns and comment out the True returns to see failed execution.
    """

    def check_prerequisites(self):
        return True
        #return False

    def setup(self):
        return True
        #return False
    
    def run(self):
        return True
        #return False
  
    def get_result(self):
        return (True, None)
        #return (False, "Test message\nAnother test message\n")
    
    def record(self):
        # Not a comparative test, returning True
        return True
        #return False
    
    def cleanup(self):
        return True
        #return False


