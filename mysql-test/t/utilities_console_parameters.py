#
# Copyright (c) 2012, 2013, Oracle and/or its affiliates. All rights reserved.
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
from mysql.utilities.exception import MUTLibError

_BASE_COMMENT = "Test Case %d: "

class test(mutlib.System_test):
    """mysql utilities console - parameters
    This test executes tests of the parameters for mysqluc. Note that piping
    and the --execute are tested in the utilities_console_base and 
    utilities_console_pipe tests. 
    """

    def check_prerequisites(self):
        self.server0 = None
        return self.check_num_servers(1)

    def setup(self):
        self.server0 = self.servers.get_server(0)
        return True
    
    def do_test(self, test_num, comment, command):
        res = self.run_test_case(0, command, _BASE_COMMENT%test_num + comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
            
    def run(self):
        self.res_fname = "result.txt"
        
        # Setup options to show
        test_num = 1
        cmd_str = "mysqluc.py %s"
        
        # show help
        cmd_opt = '--help'
        self.do_test(test_num, "Help", cmd_str % cmd_opt)
        test_num += 1

        # do normal execution
        cmd_opt = '-e "help mysqldiff"'
        self.do_test(test_num, "Normal", cmd_str % cmd_opt)
        test_num += 1

        # do verbose output
        cmd_opt = '--verbose -e "help mysqldiff"'
        self.do_test(test_num, "Verbosity", cmd_str % cmd_opt)
        test_num += 1

        # do quiet output
        cmd_opt = '--quiet -e "help mysqldiff"'
        self.do_test(test_num, "Quiet", cmd_str % cmd_opt)
        test_num += 1

        # width adjusted
        cmd_opt = '-e "help mysqldiff" --width=55'
        self.do_test(test_num, "Normal - width 55", cmd_str % cmd_opt)
        test_num += 1

        # width adjusted
        cmd_opt = '-e "help mysqldiff" --width=66'
        self.do_test(test_num, "Normal - width 66", cmd_str % cmd_opt)
        test_num += 1
        
        # test replacement
        cmd_opt = ' -e "set SERVER=%s;show variables;' % \
                  self.build_connection_string(self.server0)
        if os.name == 'posix':
            cmd_opt += 'mysqldiff --server1=\$SERVER"'
        else:
            cmd_opt += 'mysqldiff --server1=$SERVER"'
        self.do_test(test_num, "Replacement", cmd_str % cmd_opt)
        test_num += 1
        
        self.replace_result("SERVER", "SERVER      XXXXXXXXXXXXXXXXXXXXXXXX\n")
        self.replace_result("utildir", "utildir    XXXXXXXXXXXXXX\n")
        self.replace_result("Quiet mode, saving output to",
                            "Quiet mode, saving output to XXXXXXXXXXXXXX\n")
        self.remove_result("Launching console ...")
         
        return True    
          
    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)
    
    def cleanup(self):
        if self.res_fname:
            os.unlink(self.res_fname)
        return True




