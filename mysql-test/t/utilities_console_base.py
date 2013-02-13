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
    """mysql utilities console - base commands
    This test executes tests of the base commands for mysqluc.
    
    These include:

    Command                 Description                                        
    ----------------------  --------------------------------------------------
    help utilities          Display list of all utilities supported.           
    help <utility>          Display help for a specific utility.               
    help | help commands    Show this list.                                    
    exit | quit             Exit the console.                                  
    set <variable>=<value>  Store a variable for recall in commands.           
    show options            Display list of options specified by the user on   
                            launch.                                            
    show variables          Display list of variables.                         

    These commands are executed using the --execute option to simulate an
    interactive environment.
    """

    def check_prerequisites(self):
        return True

    def setup(self):
        return True
    
    def do_test(self, test_num, comment, command):
        res = self.run_test_case(0, command, _BASE_COMMENT%test_num + comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
            
    def do_coverage_tests(self, base_command):
        test_num = 1
        
        # Simple single-command tests
        _SIMPLE_COMMANDS = [
            ("Show Help", "help"),
            ("Show Help Commands", "help commands"),
            ("Show Help Commands", "HELP COMMANDS"),
            ("Show Utilities", "help utilities"),
            ("Show Options", "show options"),
            ("Do Exit", "exit"),
            ("Do Quit", "QUIT"),
        ]
        for cmd in _SIMPLE_COMMANDS:
            self.do_test(test_num, cmd[0], base_command % cmd[1])
            test_num += 1

        # Negative tests
        self.do_test(test_num, "Invalid Command", base_command % 'WHATSIT?')
        test_num += 1

        self.do_test(test_num, "Invalid Command Sequence",
                     base_command % 'So;this; is ; a; Crock!')
        test_num += 1

        # Do more complex commands separating them by ;
        _COMPLEX_COMMANDS = [
            ("Show Help + Help Utilities", "help;help utilities"),
            ("Show Utilities + Options", "help utilities ; show options"),
            ("Show Utilities + Options + NULL", "help utilities;show options;"),
            ("Do Exit + Quit", "exit;quit"),
        ]
        for cmd in _COMPLEX_COMMANDS:
            self.do_test(test_num, cmd[0], base_command % cmd[1])
            test_num += 1

        # Set then show some variables
        self.do_test(test_num, "Set and Show Variables",
                base_command % "set killer=123;set ABC='test123';show variables")
        test_num += 1
        
        # Show we cannot execute extraneous commands
        self.do_test(test_num, "Attempt to run extraneous command.",
                     base_command % "mkdir make_mischief")

        self.replace_result("utildir", "utildir    XXXXXXXXXXXXXX\n")
        self.remove_result("Launching console ...")
        self.replace_result("The utility mysqla is not accessible (from the",
                            "The utility mysqla is not accessible (...)\n")
            
        return True    
            
    def run(self):
        self.res_fname = "result.txt"
        
        # Setup options to show
        cmd_str = 'mysqluc.py --width=77 -e "%s" '

        return self.do_coverage_tests(cmd_str)
          
    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)
    
    def cleanup(self):
        if self.res_fname:
            os.unlink(self.res_fname)
        return True




