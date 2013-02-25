#!/usr/bin/env python
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

"""
This file contains the mysql utilities client.
"""

from mysql.utilities.common.tools import check_python_version    

# Check Python version compatibility
check_python_version()

import optparse
import os
import sys

try:
    import mysql.connector
except:
    print("ERROR: The Connector/Python module is not installed or "
          "is not accessible from this terminal.")
    sys.exit(2)

try:
    from mysql.utilities.command.utilitiesconsole import UtilitiesConsole
    from mysql.utilities import VERSION_FRM, VERSION_STRING
    from mysql.utilities.common.options import add_verbosity, check_verbosity
    from mysql.utilities.exception import UtilError
except:
    print("ERROR: MySQL Utilities are either not installed or are not "
          "accessible from this terminal.")
    sys.exit(2)

# Constants
NAME = "MySQL Utilities Client - mysqluc "
DESCRIPTION = "mysqluc - Command line client for running MySQL Utilities"
USAGE = "%prog "
WELCOME_MESSAGE = """
Welcome to the MySQL Utilities Client (mysqluc) version %s 
Copyright (c) 2000, 2012, Oracle and/or its affiliates. All rights reserved.\n
Oracle is a registered trademark of Oracle Corporation and/or its affiliates.
Other names may be trademarks of their respective owners.

Type 'help' for a list of commands or press TAB twice for list of utilities.
"""
GOODBYE_MESSAGE = "\nThanks for using the MySQL Utilities Client!\n"
PRINT_WIDTH = 75
UTIL_PATH = "/scripts"

def build_variable_dictionary_list(args):
    """Build a variable dictionary from the arguments
    
    Returns list - list of variables
    """
    variables = []
    arguments = list(args)
    for i, arg in enumerate(arguments):
        if '=' in arg:
            name, value = arg.split('=')
            variables.append({'name': name, 'value': value})
            arguments.pop(i)
    
    if len(arguments) % 2:
        parser.error("Unbalanced arguments. Please check your command.")
    for i in range(0, len(arguments), 2):
        variables.append({'name': arguments[i], 'value': arguments[i+1]})
    return variables

# Setup the command parser
parser = optparse.OptionParser(
    version=VERSION_FRM.format(program=os.path.basename(sys.argv[0])),
    description=DESCRIPTION,
    usage=USAGE,
    add_help_option=False)
parser.add_option("--help", action="help")

# Add display width option
parser.add_option("--width", action="store", dest="width",
                  type="int", help="display width",
                  default=PRINT_WIDTH)

# Add utility directory option
parser.add_option("--utildir", action="store", dest="utildir",
                  type="string", help="location of utilities",
                  default=UTIL_PATH)

# Add execute mode
parser.add_option("-e", "--execute", action="store", dest="commands",
                  type="string", help="Execute commands and exit. Multiple "
                  "commands are separated with semi-colons. Note: some "
                  "platforms may require double quotes around command list.",
                  default=None)

# Add verbosity mode
add_verbosity(parser, True)

# Now we process the rest of the arguments.
opt, args = parser.parse_args()

# Warn if quiet and verbosity are both specified
check_verbosity(opt)

if opt.verbosity is None:
    verbosity = 0
else:
    verbosity = opt.verbosity

quiet = opt.quiet
if opt.quiet is None:
    quiet = False

options = {
    'verbosity' : verbosity,
    'quiet'     : quiet,
    'width'     : opt.width,
    'utildir'   : opt.utildir,
    'variables' : build_variable_dictionary_list(args),
    'prompt'    : 'mysqluc> ',
    'welcome'   : WELCOME_MESSAGE % VERSION_STRING,
    'goodbye'   : GOODBYE_MESSAGE,
    'commands'  : opt.commands,
    'custom'    : True, # We are using custom commands
}

try:
    print("Launching console ...")
    util_con = UtilitiesConsole(options)
    util_con.run_console()
except KeyboardInterrupt:
    print(options['goodbye'])
except UtilError:
    _, e, _ = sys.exc_info()
    print("ERROR: %s" % e.errmsg)

sys.exit()
