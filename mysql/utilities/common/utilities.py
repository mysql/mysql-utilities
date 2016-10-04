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
This module contains classes and functions used to determine what MySQL
utilities are installed, their options, and usage. This module can be
used to allow a client to provide auto type and option completion.
"""

import glob
import os
import sys
import re
import subprocess

from mysql.utilities import AVAILABLE_UTILITIES
from mysql.utilities.common.format import print_dictionary_list
from mysql.utilities.common.tools import check_python_version
from mysql.utilities.exception import UtilError


_MAX_WIDTH = 78

# These utilities should not be used with the console
_EXCLUDE_UTILS = ['mysqluc', ]

RE_USAGE = (
    r"(?P<Version>.*?)"
    r"(?P<Usage>Usage:\s.*?)\w+\s\-\s"  # This match first
    # section <Usage> matching all till find a " - "
    r"(?P<Description>.*?)"  # Description is the text next
    # to " - " and till next match.
    r"(?P<O>\w*):"  # This is beginning of Options section
    r"(?P<Options>.*(?=^Introduction.\-{12})|.*$)"
    # match Options till end or till find Introduction -.
    r"(?:^Introduction.\-{12}){0,1}"  # not catching group
    r"(?P<Introduction>.*(?=^Helpful\sHints.\-{13})|.*$)"
    # captures Introduction (optional)
    # it will match Introduction till end or till Hints -
    r"(?:^Helpful\sHints.\-{13}){0,1}"  # Not catching group
    r"(?P<Helpful_Hints>.*)"
    # captures Helpful Hints (optional)
)

RE_OPTIONS = (
    r"^(?P<Alias>\s\s\-.*?)\s{2,}"  # Option Alias
    # followed by 2 o more spaces is his description
    r"(?P<Desc>.*?)(?=^\s\s\-)"  # description is all
    # text till not found other alias in the form
    # <-|--Alias> at the begin of the line.
)

RE_OPTION = r"\s+\-\-(.*?)\s"  # match Alias of the form <--Alias>

RE_ALIAS = r"\s+\-(\w+)\s*"  # match Alias of the form <-Alias>

WARNING_FAIL_TO_READ_OPTIONS = ("WARNING: {0} failed to read options."
                                " This utility will not be shown in 'help "
                                "utilities' and cannot be accessed from the "
                                "console.")


def get_util_path(default_path=''):
    """Find the path to the MySQL utilities

    This method will attempt to

    default_path[in]   provides known location of utilities
                       if provided, method will search this location first
                       before searching PYTHONPATH

    Returns string - path to utilities or None if not found
    """
    def _search_paths(needles, paths):
        """Search and return normalized path
        """
        for path in paths:
            norm_path = os.path.normpath(path)
            hay_stack = [os.path.join(norm_path, n) for n in needles]
            for needle in hay_stack:
                if os.path.isfile(needle):
                    return norm_path

        return None

    needle_name = 'mysqlreplicate'
    needles = [needle_name + ".py"]
    if os.name == "nt":
        needles.append(needle_name + ".exe")
    else:
        needles.append(needle_name)

    # Try the default by itself
    path_found = _search_paths(needles, [default_path])
    if path_found:
        return path_found

    # Try the pythonpath environment variable
    pythonpath = os.getenv("PYTHONPATH")
    if pythonpath:
        # This is needed on windows without a python setup, cause needs to
        # find the executable scripts.
        path = _search_paths(needles, [os.path.join(n, "../")
                                       for n in pythonpath.split(";", 1)])
        if path:
            return path
        path = _search_paths(needles, pythonpath.split(";", 1))
        if path:
            return path

    # Try the system paths
    path_found = _search_paths(needles, sys.path)
    if path_found:
        return path_found

    return None


class Utilities(object):
    """The utilities class can be used to discover what utilities are installed
    on the system as well as the usage and options for each utility.

    The list of utilities are read at initialization.

    This class is designed to support the following operations:

        get_util_matches()    - find all utilities that match a prefix
        get_option_matches()  - find all options that match a prefix for a
                                given utility
        get_usage()           - return the usage statement for a given utility
        show_utilities()      - display a 2-column list of utilities and their
                                descriptions
        show_options()        - display a 2-column list of the options for a
                                given utility including the name and
                                description of each option
    """

    def __init__(self, options=None):
        """Constructor
        """
        if options is None:
            options = {}
        self.util_list = []
        self.width = options.get('width', _MAX_WIDTH)
        self.util_path = get_util_path(options.get('utildir', ''))
        self.extra_utilities = options.get('add_util', {})
        self.hide_utils = options.get('hide_util', False)

        self.program_usage = re.compile(RE_USAGE, re.S | re.M)
        self.program_options = re.compile(RE_OPTIONS, re.S | re.M)
        self.program_option = re.compile(RE_OPTION)
        self.program_name = re.compile(RE_ALIAS)

        self.util_cmd_dict = {}
        self.posible_utilities = {}
        self.posible_utilities.update(AVAILABLE_UTILITIES)
        if self.extra_utilities and self.hide_utils:
            self.posible_utilities = self.extra_utilities
        else:
            self.posible_utilities.update(self.extra_utilities)
        self.available_utilities = self.posible_utilities
        for util_name, ver_compatibility in self.posible_utilities.iteritems():
            name_utility = "{0} utility".format(util_name)
            if ver_compatibility:
                min_v, max_v = ver_compatibility
                res = check_python_version(min_version=min_v,
                                           max_version=max_v,
                                           name=name_utility,
                                           print_on_fail=False,
                                           exit_on_fail=False,
                                           return_error_msg=True)
            else:
                res = check_python_version(name=name_utility,
                                           print_on_fail=False,
                                           exit_on_fail=False,
                                           return_error_msg=True)
            if isinstance(res, tuple):
                is_compat, error_msg = res
                if not is_compat:
                    self.available_utilities.remove(util_name)
                    print(WARNING_FAIL_TO_READ_OPTIONS.format(util_name))
                    print("ERROR: {0}\n".format(error_msg))
                    continue
            self._find_utility_cmd(util_name)

    @staticmethod
    def find_executable(util_name):
        """Search the system path for an executable matching the utility

        util_name[in]  Name of utility

        Returns string - name of executable (util_name or util_name.exe) or
                         original name if not found on the system path
        """
        paths = os.getenv("PATH").split(os.pathsep)
        for path in paths:
            new_path = os.path.join(path, util_name + "*")
            if os.name == "nt":
                new_path = '"{0}"'.format(new_path)
            found_path = glob.glob(new_path)
            if found_path:
                return os.path.split(found_path[0])[1]
        return util_name

    def _find_utility_cmd(self, utility_name):
        """ Locate the utility scripts

        util_name[in]   utility to find

        This method builds a dict of commands for invoke the utilities.
        """
        util_path = self.find_executable(os.path.join(self.util_path,
                                                      utility_name))
        util_path_parts = os.path.split(util_path)
        parts = os.path.splitext(util_path_parts[len(util_path_parts) - 1])
        # filter extensions
        exts = ['.py', '.exe', '', 'pyc']
        if (parts[0] not in _EXCLUDE_UTILS and
                (len(parts) == 1 or (len(parts) == 2 and parts[1] in exts))):
            util_name = str(parts[0])
            file_ext = parts[1]
            command = "{0}{1}".format(util_name, file_ext)

            util_path = self.util_path
            utility_path = command
            if not os.path.exists(command):
                utility_path = os.path.join(util_path, utility_name)

            # Now try the extensions
            if not os.path.exists(utility_path):
                if file_ext:
                    utility_path = "{0}{1}".format(utility_path, file_ext)
                else:
                    for ext in exts:
                        try_path = "{0}{1}".format(utility_path, ext)
                        if os.path.exists(try_path):
                            utility_path = try_path

            if not os.path.exists(utility_path):
                print("WARNING: Unable to locate utility {0}."
                      "".format(utility_name))
                print(WARNING_FAIL_TO_READ_OPTIONS.format(util_name))
                return

            # Check for running against .exe
            if utility_path.endswith(".exe"):
                cmd = []
            # Not using .exe
            else:
                cmd = [sys.executable]

            cmd.extend([utility_path])
            self.util_cmd_dict[utility_name] = tuple(cmd)

    def find_utilities(self, this_utils=None):
        """ Locate the utility scripts
        this_utils[in]   list of utilities to find, default None to find all.

        This method builds a list of utilities.
        """

        if not this_utils:
            # Not utilities name to find was passed, find help for all those
            # utilities not previously found in a previos call.
            utils = self.available_utilities
            working_utils = [util['name'] for util in self.util_list]
            if len(working_utils) >= len(self.util_list):
                utils = [name for name in utils if name not in working_utils]
            if len(utils) < 1:
                return
        else:
            # utilities name given to find for, find help for all these which
            # was not previously found in a previos call.
            working_utils = [util['name'] for util in self.util_list]
            utils = [util for util in this_utils if util not in working_utils]
            if len(utils) < 1:
                return

        # Execute the utility command using get_util_info()
        # that returns --help partially parsed.
        for util_name in utils:
            if util_name in self.util_cmd_dict:
                cmd = self.util_cmd_dict.pop(util_name)
                util_info = self.get_util_info(list(cmd), util_name)
                if util_info and util_info["usage"]:
                    util_info["cmd"] = tuple(cmd)
                    self.util_list.append(util_info)
                    working_utils.append(util_name)

        self.util_list.sort(key=lambda util_list: util_list['name'])

    def get_util_info(self, cmd, util_name):
        """Get information about utility

        cmd[in]        a list with the elements that conform the command
                       to invoke the utility
        util_name[in]  name of utility to get information

        Returns dictionary - name, description, usage, options
        """
        cmd.extend(["--help"])
        # rmv print('executing ==> {0}'.format(cmd))
        try:
            proc = subprocess.Popen(cmd, shell=False,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)
            stdout_temp, stderr_temp = proc.communicate()
            returncode = proc.returncode
        except OSError:
            # always OS error if not found.
            # No such file or directory
            stdout_temp = ""
            returncode = 0

        # Parse the help output and save the information found
        usage = None
        description = None

        if stderr_temp or returncode:
            print(WARNING_FAIL_TO_READ_OPTIONS.format(util_name))
            if stderr_temp:
                print("The execution of the command returned: {0}"
                      "".format(stderr_temp))
            else:
                print("UNKNOWN. To diagnose, exit mysqluc and attempt the "
                      "command: {0} --help".format(util_name))
            return None

        res = self.program_usage.match(stdout_temp.replace("\r", ""))
        if not res:
            print(WARNING_FAIL_TO_READ_OPTIONS.format(util_name))
            print("An error occurred while trying to parse the options "
                  "from the utility")
            return None
        else:
            usage = res.group("Usage").replace("\n", "")
            desc_clean = res.group("Description").replace("\n", " ").split()
            description = (" ".join(desc_clean)) + " "
            # standardize string.
            Options = res.group("Options") + "\n  -"

        # Create dictionary for the information
        utility_data = {
            'name': util_name,
            'description': description,
            'usage': usage,
            'options': Options
        }
        return utility_data

    def parse_all_options(self, utility):
        """ Parses all options for the given utility.

        utility[inout]   that contains the options info to parse
        """
        options_info = utility['options']
        if isinstance(options_info, list):
            # nothing to do if it is a list.
            return

        options = []
        res = self.program_options.findall(options_info)

        for opt in res:
            option = {}
            name = self.program_option.search(opt[0] + " ")
            if name:
                option['name'] = str(name.group(1))
            alias = self.program_name.search(opt[0] + " ")
            if alias:
                option['alias'] = str(alias.group(1))
            else:
                option['alias'] = None

            desc_clean = opt[1].replace("\n", " ").split()
            option['description'] = " ".join(desc_clean)
            option['long_name'] = option['name']
            parts = option['name'].split('=')
            option['req_value'] = len(parts) == 2
            if option['req_value']:
                option['name'] = parts[0]
            if option:
                options.append(option)

        utility['options'] = options

    def get_util_matches(self, util_prefix):
        """Get list of utilities that match a prefix

        util_prefix[in] prefix for name of utility

        Returns dictionary entry for utility based on matching first n chars
        """
        matches = []
        if not util_prefix.lower().startswith('mysql'):
            util_prefix = 'mysql' + util_prefix
        for util in self.available_utilities:
            if util[0:len(util_prefix)].lower() == util_prefix:
                matches.append(util)
        # make sure the utilities description has been found for the matches.
        self.find_utilities(matches)
        matches = [util for util in self.util_list if util['name'] in matches]
        return matches

    def get_option_matches(self, util_info, option_prefix, find_alias=False):
        """Get list of option dictionary entries for options that match
        the prefix.

        util_info[in]     utility information
        option_prefix[in] prefix for option name
        find_alias[in]    if True, match alias (default = False)

        Returns list of dictionary items that match prefix
        """
        # Check type of util_info
        if util_info is None or util_info == {} or \
                not isinstance(util_info, dict):
            raise UtilError("Empty or invalide utility dictionary.")

        matches = []

        stop = len(option_prefix)
        if isinstance(util_info['options'], str):
            self.parse_all_options(util_info)
        for option in util_info['options']:
            if option is None:
                continue
            name = option.get('name', None)
            if name is None:
                continue
            if find_alias:
                if option.get('alias', '') == option_prefix:
                    matches.append(option)
            else:
                if name[0:stop] == option_prefix:
                    matches.append(option)

        return matches

    def show_utilities(self, print_list=None):
        """Show list of utilities as a 2-column list.

        print_list[in]    list of utilities to print - default is None
                          which means print all utilities
        """

        if print_list is None:
            if len(self.util_list) != len(self.available_utilities):
                self.find_utilities()
            list_of_utilities = self.util_list
        else:
            list_of_utilities = print_list
        print
        if len(list_of_utilities) > 0:
            print_dictionary_list(['Utility', 'Description'],
                                  ['name', 'description'],
                                  list_of_utilities, self.width)
        else:
            print
            print "No utilities match the search term."
        print

    def get_options_dictionary(self, utility_options):
        """Retrieve the options dictionary.

        This method builds a new dictionary that contains the options for the
        utilities read.

        utility_options[in]   list of options for utilities or the utility.

        Return dictionary - list of options for all utilities.
        """
        dictionary_list = []

        if isinstance(utility_options, dict):
            if isinstance(utility_options['options'], str):
                # options had not been parsed yet
                self.parse_all_options(utility_options)
            options = utility_options['options']
        else:
            options = utility_options

        for option in options:
            name = option.get('long_name', '')
            if len(name) == 0:
                continue
            name = '--' + name
            alias = option.get('alias', None)
            if alias is not None:
                name = '-' + alias + ", " + name
            item = {
                'long_name': name,
                'description': option.get('description', '')
            }
            dictionary_list.append(item)

        return dictionary_list

    def show_options(self, options):
        """Show list of options for a utility by name.

        options[in]    structure containing the options

        This method displays a list of the options and their descriptions
        for the given utility.
        """
        if len(options) > 0:
            dictionary_list = self.get_options_dictionary(options)
            print
            print
            print_dictionary_list(['Option', 'Description'],
                                  ['long_name', 'description'],
                                  dictionary_list, self.width)
            print

    @staticmethod
    def get_usage(util_info):
        """Get the usage statement for the utility

        util_info[in]  dictionary entry for utility information

        Returns string usage statement
        """
        # Check type of util_info
        if util_info is None or util_info == {} or \
                not isinstance(util_info, dict):
            return False

        return util_info['usage']


def kill_process(pid, force=False, silent=False):
    """This function tries to kill the given subprocess.

    pid [in]    Process id of the subprocess to kill.
    force [in]  Boolean value, if False try to kill process with SIGTERM
                (Posix only) else kill it forcefully.
    silent[in]  If true, do no print message

    Returns True if operation was successful and False otherwise.
    """
    res = True
    if os.name == "posix":
        if force:
            os.kill(pid, subprocess.signal.SIGABRT)
        else:
            os.kill(pid, subprocess.signal.SIGTERM)
    else:
        with open(os.devnull, 'w') as f_out:
            ret_code = subprocess.call("taskkill /F /T /PID {0}".format(pid),
                                       shell=True, stdout=f_out, stdin=f_out)
            if ret_code not in (0, 128):
                res = False
                if not silent:
                    print("Unable to successfully kill process with PID "
                          "{0}".format(pid))
    return res
