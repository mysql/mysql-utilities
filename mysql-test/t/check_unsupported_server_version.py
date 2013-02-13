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
import mutlib
from mysql.utilities.exception import MUTLibError, UtilDBError

class test(mutlib.System_test):
    """
    This test executes a script to verify the message for an unsupported server
    It test the message for the unsupported version of the First server passed
    as parameter and passed as the second parameter.
    """

    def check_prerequisites(self):
        OK = self.check_num_servers(2)
        if OK:
            self.old_server = None
            self.new_server = None
            stop = self.servers.num_servers()
            for index in range(0, stop):
                server = self.servers.get_server(index)
                if not server.check_version_compat(5, 1, 30):
                    self.old_server = index
                else:
                    self.new_server = index
                if self.old_server and self.new_server:
                    break
        if (not OK or 
            self.old_server is None or 
            self.new_server is None): 
            fail_msg = ("Test requires two servers. One server with %s" %
                        "version 5.1.30 or higher and one prior to 5.1.30")
            raise MUTLibError(fail_msg) 
        # Need at least one server.
        self.server1 = None
        self.server2 = None
        return self.check_num_servers(1)

    def setup(self):
        self.server1 = self.servers.get_server(self.old_server)
        self.server2 = self.servers.get_server(self.new_server)           
        return True
    
    def run(self):
        self.res_fname = "result.txt"
               
        olds_conn = self.build_connection_string(self.server1)
        news_conn = self.build_connection_string(self.server2)
        
        num_test = 1
        comment = ("Test case %s - compare two databases %s" %
                   (num_test, "on unsupported server"))
        cmd_str = "mysqldbcompare.py %s %s" % ("--server1=" + olds_conn,
                                               "--server2=" + news_conn)
        cmd_opts = " util_test.util_test -a "
        res = self.run_test_case(1, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        self.results.append("\n")
        
        num_test += 1
        comment = ("Test case %s - compare two databases %s" % 
                  (num_test, "on unsupported 2nd server"))
        
        cmd_str = "mysqldbcompare.py %s %s" % ("--server1=" + news_conn,
                                               "--server2=" + olds_conn)
        cmd_opts = " util_test.util_test -a "
        res = self.run_test_case(1, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        
        return True
          
    def get_result(self):
        return self.compare(__name__, self.results)
    
    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        if self.res_fname:
            try:
                os.unlink(self.res_fname)
            except:
                pass
        #self.servers.shutdown_spawned_servers()
        return True
