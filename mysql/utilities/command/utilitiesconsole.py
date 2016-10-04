#
# Copyright (c) 2011, 2016, Oracle and/or its affiliates. All rights reserved.
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
This file contains the utilities console mechanism.
"""

import os
import tempfile
import subprocess

from mysql.utilities.exception import UtilError
from mysql.utilities.common.console import Console
from mysql.utilities.common.format import print_dictionary_list
from mysql.utilities.common.utilities import Utilities, get_util_path


# The following are additional base commands for the console. These comamnds
# are in addition to the supported base commands in the Console class. Thus,
# these are specific to mysqluc.
#
# The list includes a tuple for each command that contains the name of the
# command, alias (if available) and its help text.
_NEW_BASE_COMMANDS = [
    {'name': 'help utilities',
     'alias': '',
     'text': 'Display list of all utilities supported.'},
    {'name': 'help <utility>',
     'alias': '',
     'text': 'Display help for a specific utility.'},
    {'name': 'show errors',
     'alias': '',
     'text': 'Display errors captured during the execution of the utilities.'},
    {'name': 'clear errors',
     'alias': '',
     'text': 'clear captured errors.'},
    {'name': 'show last error',
     'alias': '',
     'text': 'Display the last error captured during the execution of the'
             ' utilities'}
]

_UTILS_MISSING = "MySQL Utilities are either not installed or " + \
                 "are not accessible from this terminal."


class UtilitiesConsole(Console):
    """
    The UtilitiesConsole class creates a console for running MySQL Utilities.

    This class uses the Console class to encapsulate the screen handling and
    key captures for a command line shell. This subclass provides the custom
    commands (the utilities) to the console class for redirecting to the
    methods contained in this class for executing utilities. These include:

    - matching command from the shell to available utilities
    - matching options from the shell to the options for a given utility
    - showing the help for a utility

    """

    def __init__(self, options=None):
        """Constructor

        options[in]        Array of options for controlling what is included
                           and how operations perform (e.g., verbose)
        """
        if options is None:
            options = {}
        Console.__init__(self, _NEW_BASE_COMMANDS, options)
        try:
            self.path = get_util_path(options.get("utildir", ""))
            if self.path is None:
                raise UtilError(_UTILS_MISSING)
        except:
            raise UtilError(_UTILS_MISSING)
        self.utils = Utilities(options)
        self.errors = []
        if self.quiet:
            self.f_out = tempfile.NamedTemporaryFile(delete=False)
            print("Quiet mode, saving output to {0}".format(self.f_out.name))
        else:
            self.f_out = None

    def show_custom_command_help(self, arg):
        """Display the help for a utility

        This method will display a list of the available utilities if the
        command argument is 'utilities' or the help for a specific utility if
        the command argument is the name of a known utility.

        arg[in]            Help command argument
        """
        if self.quiet:
            return
        if arg and arg.lower() == 'utilities':
            self.utils.show_utilities()
        else:
            matches = self.utils.get_util_matches(arg)
            if len(matches) > 1:
                self.utils.show_utilities(matches)
            elif len(matches) == 1:
                self.show_utility_help(matches)
            else:
                print("\n\nCannot find utility '{0}'.\n".format(arg))

    def do_custom_tab(self, prefix):
        """Do custom tab key processing

        This method performs the tab completion for a utility name. It searches
        the available utilties for the prefix of the utility name. If an exact
        match is found, it updates the command else it returns a list of
        matches.

        If the user has pressed TAB twice, it will display a list of all of
        the utilities available.

        prefix[in]        Prefix of the utility name
        """
        new_cmd = ''  # blank string means no matches

        find_cmd = prefix
        if len(prefix) >= 5 and prefix[0:5] != 'mysql':
            find_cmd = 'mysql' + find_cmd
        matches = self.utils.get_util_matches(find_cmd)
        if self.tab_count == 2:
            self.utils.show_utilities(matches)
            self.cmd_line.display_command()
            self.tab_count = 0
        # Do command completion here
        elif len(matches) == 1:
            new_cmd = matches[0]['name'] + ' '
            start = len(prefix)
            if prefix[0:5] != 'mysql':
                start += 5
            self.cmd_line.add(new_cmd[start:])
            self.tab_count = 0

    def do_custom_option_tab(self, command_text):
        """Do custom option tab key processing

        This method performs the tab completion for the options for a utility.
        It splits the command text into the utility name and requests the
        option prefix from the command line.

        If the user presses TAB twice, the method will display all of the
        options for the specified utility.

        command_text[in]   Portion of command from the position of the cursor

        Returns string - '' if not found, the remaining portion of the match
                         of the option if found (for example, we look for
                         '--verb' and find '--verbose' so we return 'ose').
        """
        option_loc = 0
        option = ''
        cmd_len = len(command_text)
        full_command = self.cmd_line.get_command()

        # find utility name
        i = full_command.find(' ')
        if i < 0:
            return  # This may be an error!

        util_name = full_command[0:i]

        # get utility information
        utils = self.utils.get_util_matches(util_name)
        if len(utils) <= 0:
            return ''  # No option found because util does not exist.

        # if double tab with no option specified, show all options
        if cmd_len == 0 and self.tab_count == 2:
            self.utils.show_options(utils[0])
            self.cmd_line.display_command()
            self.tab_count = 0
            return

        find_alias = False
        if len(command_text) == 0:
            option_loc = 0
        # check for - or --
        elif command_text[0:2] == '--':
            option_loc = 2
        elif command_text[0] == '-':
            option_loc = 1
            find_alias = True
        option = command_text[option_loc:]

        matches = self.utils.get_option_matches(utils[0], option, find_alias)
        if self.tab_count == 2:
            if len(matches) > 0:
                self.utils.show_options(matches)
                self.cmd_line.display_command()
            self.tab_count = 0
            return

        # Do option completion here
        if len(matches) == 1:
            if not find_alias:
                opt_name = matches[0]['name']
                # Check for required value
                if matches[0]['req_value']:
                    opt_name += '='
                else:
                    opt_name += ' '
            else:  # using alias
                opt_name = matches[0]['alias'] + ' '

            # Now, replace the old value on the command line.
            start = len(command_text) - option_loc
            self.cmd_line.add(opt_name[start:].strip(' '))
            self.tab_count = 0

    def show_utility_help(self, utils):
        """Display help for a utility.

        utils[in]          The utility name.
        """
        if self.quiet:
            return
        options = self.utils.get_options_dictionary(utils[0])
        print("\n{0}\n".format(utils[0]['usage']))
        print("{0} - {1}\n".format(utils[0]['name'], utils[0]['description']))
        print("Options:")
        print_dictionary_list(['Option', 'Description'],
                              ['long_name', 'description'],
                              options, self.width, False)
        print

    def is_valid_custom_command(self, command_text):  # pylint: disable=W0221
        """Validate the custom command

        If the command_text is the name of a utility supported, return True
        else return False.

        command_text[in]   Command from the user

        Returns bool - True - valid, False - invalid
        """
        parts = command_text.split(' ')
        matches = self.utils.get_util_matches(parts[0])
        return len(matches) >= 1

    def execute_custom_command(self, command, parameters):
        """Execute the utility

        This method executes the utility with the parameters specified by the
        user. All output is displayed and control returns to the console class.

        command[in]        Name of the utility to execute
        parameters[in]     All options and parameters specified by the user
        """
        if not command.lower().startswith('mysql'):
            command = 'mysql' + command
        # look in to the collected utilities
        for util_info in self.utils.util_list:
            if util_info["name"] == command:
                # Get the command used to obtain the help from the utility
                cmd = list(util_info["cmd"])
                cmd.extend(parameters)

                # Add quotes for Windows
                if (os.name == "nt"):
                    # If there is a space in the command, quote it!
                    if (" " in cmd[0]):
                        cmd[0] = '"{0}"'.format(cmd[0])
                    # if cmd is freeze code utility, subprocess just need the
                    # executable part not absolute path using shell=False or
                    # Windows will complain about the path. The base path of
                    # mysqluc is used as location dir base of the subprocess.
                    if '.exe' in cmd[0]:
                        _, ut_cmd = os.path.split(cmd[0])
                        cmd[0] = ut_cmd.replace('"', '')
                    # If the second part has .py in it and spaces, quote it!
                    if len(cmd) > 1 and (" " in cmd[1]) and ('.py' in cmd[0]):
                        cmd[1] = '"{0}"'.format(cmd[1])

                if self.quiet:
                    proc = subprocess.Popen(cmd, shell=False,
                                            stdout=self.f_out,
                                            stderr=self.f_out)
                else:
                    proc = subprocess.Popen(cmd, shell=False,
                                            stderr=subprocess.PIPE)
                    print

                # check the output for errors
                _, stderr_temp = proc.communicate()
                return_code = proc.returncode
                err_msg = ("\nThe console has detected that the utility '{0}' "
                           "ended with an error code.\nYou can get more "
                           "information about the error by running the console"
                           " command 'show last error'.").format(command)
                if not self.quiet and return_code and stderr_temp:
                    print(err_msg)
                    if parameters:
                        msg = ("\nExecution of utility: '{0} {1}' ended with "
                               "return code '{2}' and with the following "
                               "error message:\n"
                               "{3}").format(command, ' '.join(parameters),
                                             return_code, stderr_temp)
                    else:
                        msg = ("\nExecution of utility: '{0}' ended with "
                               "return code '{1}' and with the following "
                               "error message:\n{2}").format(command,
                                                             return_code,
                                                             stderr_temp)
                    self.errors.append(msg)
                elif not self.quiet and return_code:
                    if parameters:
                        msg = ("\nExecution of utility: '{0} {1}' ended with "
                               "return code '{2}' but no error message was "
                               "streamed to the standard error, please review "
                               "the output from its execution."
                               "").format(command, ' '.join(parameters),
                                          return_code)
                    else:
                        msg = ("\nExecution of utility: '{0}' ended with "
                               "return code '{1}' but no error message was "
                               "streamed to the standard error, please review "
                               "the output from its execution."
                               "").format(command, return_code)
                    print(msg)
                return
        # if got here, is because the utility was not found.
        raise UtilError("The utility {0} is not accessible (from the path: "
                        "{1}).".format(command, self.path))

    def show_custom_options(self):
        """Show all of the options for the mysqluc utility.

        This method reads all of the options specified when mysqluc was
        launched and displays them to the user. If none were specified, a
        message is displayed instead.
        """
        if self.quiet:
            return
        if len(self.options) == 0:
            print("\n\nNo options specified.\n")
            return

        # Build a new list that normalizes the options as a dictionary
        dictionary_list = []
        for key in self.options.keys():
            # Skip variables list and messages
            if key not in ['variables', 'welcome', 'goodbye']:
                value = self.options.get(key, '')
                item = {
                    'name': key,
                    'value': value
                }
                dictionary_list.append(item)

        print
        print
        print_dictionary_list(['Option', 'Value'], ['name', 'value'],
                              dictionary_list, self.width)
        print
