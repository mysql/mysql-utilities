#!/usr/bin/env python
#
# Copyright (c) 2012, 2016, Oracle and/or its affiliates. All rights reserved.
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

import os
import sys

from mysql.utilities.common.tools import (check_connector_python,
                                          check_python_version)
from mysql.utilities.common.options import (license_callback,
                                            UtilitiesParser,
                                            check_password_security)

# Check Python version compatibility
check_python_version()

# Check for connector/python
if not check_connector_python():
    sys.exit(1)

try:
    # pylint: disable=C0413,C0411
    from mysql.utilities import VERSION_FRM, VERSION_STRING, COPYRIGHT_FULL
    from mysql.utilities.exception import UtilError
    from mysql.utilities.command.utilitiesconsole import UtilitiesConsole
    from mysql.utilities.common.options import add_verbosity, check_verbosity
except:
    print("ERROR: MySQL Utilities are either not installed or are not "
          "accessible from this terminal.")
    sys.exit(2)

# Constants
NAME = "MySQL Utilities Client - mysqluc "
DESCRIPTION = "mysqluc - Command line client for running MySQL Utilities"
USAGE = "%prog "
WELCOME_MESSAGE = """
Welcome to the MySQL Utilities Client (mysqluc) version {0}\n{1}
Type 'help' for a list of commands or press TAB twice for list of utilities.
"""
GOODBYE_MESSAGE = "\nThanks for using the MySQL Utilities Client!\n"
PRINT_WIDTH = 75
UTIL_PATH = "/scripts"

if __name__ == '__main__':
    def build_variable_dictionary_list(args):
        """Build a variable dictionary from the arguments

        Returns list - list of variables
        """
        variables = []
        arguments = list(args)
        for arg in arguments[:]:
            if '=' in arg:
                try:
                    name, value = arg.split('=')
                    if not value:
                        raise ValueError
                except ValueError:
                    parser.error("Invalid argument assignment: {0}. Please "
                                 "check your command.".format(arg))
                variables.append({'name': name, 'value': value})
                arguments.remove(arg)

        if len(arguments) > 0:
            parser.error("Unbalanced arguments. Please check your command.")
        for i in range(0, len(arguments), 2):
            variables.append({'name': arguments[i], 'value': arguments[i + 1]})
        return variables

    # Setup the command parser
    program = os.path.basename(sys.argv[0]).replace(".py", "")
    parser = UtilitiesParser(
        version=VERSION_FRM.format(program=program),
        description=DESCRIPTION,
        usage=USAGE,
        add_help_option=False,
        prog=program
    )

    # Default option to provide help information
    parser.add_option("--help", action="help",
                      help="display this help message and exit")

    # Add --License option
    parser.add_option("--license", action='callback',
                      callback=license_callback,
                      help="display program's license and exit")

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
                      type="string",
                      help="execute commands and exit. Multiple commands are "
                           "separated with semi-colons. Note: some platforms "
                           "may require double quotes around command list.",
                      default=None)

    # Add utility extra_utilities option
    parser.add_option("--add-utility", action="append", dest="add_util",
                      help="append an utility in the format mysql<utility_"
                           "name>. The mysql<utility_name>.py must be located "
                           "inside the folder given by the utildir option",
                      default=[])

    # Add utility extra_utilities option
    parser.add_option("--hide-utils", action="store_true",
                      dest="hide_util",
                      help="when this option is given, the default utilities "
                           "will not be available, must be used only along "
                           "of --add-utility option",
                      default=False)

    # Add verbosity mode
    add_verbosity(parser, True)

    # Now we process the rest of the arguments.
    opt, args = parser.parse_args()

    # Check security settings
    check_password_security(opt, args)

    # Warn if quiet and verbosity are both specified
    check_verbosity(opt)

    if opt.verbosity is None:
        verbosity = 0
    else:
        verbosity = opt.verbosity

    quiet = opt.quiet
    if opt.quiet is None:
        quiet = False

    if opt.hide_util and not opt.add_util:
        # TODO: move to common/messages.py
        parser.error("You can only use --hide_utils option along the "
                     "--add-util option.")

    extra_utils_dict = {}
    for utility in opt.add_util:
        extra_utils_dict[utility] = ()

    options = {
        'verbosity': verbosity,
        'quiet': quiet,
        'width': opt.width,
        'utildir': opt.utildir,
        'variables': build_variable_dictionary_list(args),
        'prompt': 'mysqluc> ',
        'welcome': WELCOME_MESSAGE.format(VERSION_STRING, COPYRIGHT_FULL),
        'goodbye': GOODBYE_MESSAGE,
        'commands': opt.commands,
        'custom': True,  # We are using custom commands
        'hide_util': opt.hide_util,
        'add_util': extra_utils_dict
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
