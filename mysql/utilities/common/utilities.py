#
# Copyright (c) 2011, Oracle and/or its affiliates. All rights reserved.
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

import os
import sys

from mysql.utilities.common.format import print_dictionary_list
from mysql.utilities.exception import UtilError

_MAX_WIDTH = 78

# These utilities should not be used with the console
_EXCLUDE_UTILS = ['mysqluc',]

def get_util_path(default_path=''):
    """Find the path to the MySQL utilities
    
    This method will attempt to 
    
    default_path[in]   provides known location of utilities
                       if provided, method will search this location first
                       before searching PYTHONPATH

    Returns string - path to utilities or None if not found
    """
    needle = 'mysqlreplicate.py'
    
    # Try the default by itself
    if os.path.isfile(os.path.join(default_path, needle)):
        return default_path

    # Try the pythonpath environment variable    
    pythonpath = os.getenv("PYTHONPATH")
    if os.path.isfile(os.path.join(pythonpath+default_path, needle)):
        return pythonpath+default_path

    # Try the system paths
    for path in sys.path:
        if os.path.isfile(os.path.join(path, needle)):
            return path
    
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

    def __init__(self, options={}):
        """Constructor
        """
        
        self.util_list = []
        self.width = options.get('width', _MAX_WIDTH)
        self.util_path = get_util_path(options.get('utildir', ''))
        self.find_utilities()


    def find_utilities(self):
        """ Locate the utility scripts
        
        This method builds a list of utilities.
        """
        files = os.listdir(self.util_path)
        for file in files:
            parts = os.path.splitext(file)
            # Only accept python files - not .pyc and others
            if (len(parts) == 2 and parts[1] == '.py' and \
                parts[0] not in _EXCLUDE_UTILS) or \
               (len(parts) ==1 and parts[0] not in _EXCLUDE_UTILS):
                util_name = parts[0]
                util_info = self._get_util_info(self.util_path, util_name)
                self.util_list.append(util_info)
        self.util_list.sort(key=lambda util_list:util_list['name'])
        

    def _get_util_info(self, util_path, util_name):
        """Get information about utility
        
        util_path[in]  path to utilities
        util_name[in]  name of utility to get information
        
        Returns dictionary - name, description, usage, options
        """
        
        import subprocess
        import tempfile
        
        def _set_option_values(option, line, index, start, stop):
            """Set the option values
            """
            if index == stop or index < 0:
                option['name'] = line[start:].strip(' ').strip('--')
            else:
                option['name'] = line[start:index].strip(' ').strip('--')
                option['description'] = line[index+1:].strip(' ').strip('\r')
            option['long_name'] = option['name']
            parts = option['name'].split('=')
            option['req_value'] = len(parts) == 2
            if option['req_value']:
                option['name'] = parts[0]

        # Get the --help output for the utility
        util_cmd = "python " + os.path.join(util_path,
                                            util_name+'.py') + " --help"
        file = tempfile.TemporaryFile()
        proc = subprocess.Popen(util_cmd, shell=True,
                                stdout=file, stderr=file)
        proc.wait()
        
        # Parse the help output and save the information found
        alias = None
        usage = None
        description = None
        options = []
        option = None
        read_options = False
        file.seek(0)
        for line in file.readlines():
            line = line.strip("\n")
            if os.name == 'nt':
                line = line.strip('\r')
            stop = len(line)
            if line[0:6] == "Usage:":
                usage = line[0:stop]
            elif line[0:len(util_name)] == util_name:
                i = line.find('-')
                description = line[i+1:].strip(' ')
            elif line[0:8] == "Options:":
                read_options = True
                option = {}
            elif read_options:
                line = line.strip(" ")
                # a option without an alias
                if line[0:2] == '--':
                    if not option == {}:
                        options.append(option)
                        option = {}
                    i = line.find(' ', 5)
                    option['alias'] = None
                    _set_option_values(option, line, i, 0, stop)
                # a option with an alias
                elif line[0:1] == '-':
                    if not option == {}:
                        options.append(option)
                        option = {}
                    option['alias'] = line[1:2]
                    # now find option name
                    i = line.find('--')
                    j = line.find(' ', i+1)
                    _set_option_values(option, line, j, i, stop)
                else:  # belongs to last option
                    try:
                        option['description'] += ' ' + line.strip('\r')
                    except:                        
                        option['description'] = line.strip('\r')
            elif description is not None: # add to description
                description += ' ' + line.strip('\n').strip(' ')

        # Get last option
        if not option == {}:
            options.append(option)

        # Create dictionary for the information
        utility_data = {
            'name'        : util_name,
            'description' : description,
            'usage'       : usage,
            'options'     : options
        }
        return utility_data
    
    
    def get_util_matches(self, util_prefix):
        """Get list of utilities that match a prefix
        
        util_prefix[in] prefix for name of utility
        
        Returns dictionary entry for utility based on matching first n chars
        """
        matches = []
        if not util_prefix.lower().startswith('mysql'):
            util_prefix = 'mysql' + util_prefix
        for util in self.util_list:
            if util['name'][0:len(util_prefix)].lower() == util_prefix:
                matches.append(util)
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
           not type(util_info) == type({}):
            raise UtilError("Empty or invalide utility dictionary.")

        matches = []
        
        stop = len(option_prefix)
        for option in util_info['options']:
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
    
    
    def show_utilities(self, list=None):
        """Show list of utilities as a 2-column list.
        
        list[in]       list of utilities to print - default is None
                       which means print all utilities
        """
        
        if list is None:
            list_of_utilities = self.util_list
        else:
            list_of_utilities = list
        print
        if len(list_of_utilities) > 0:
            print_dictionary_list(['Utility', 'Description'],
                                  ['name', 'description'],
                                  list_of_utilities, self.width)        
        else:
            print
            print "No utilities match the search term."
        print

    
    def get_options_dictionary(self, options):
        """Retrieve the options dictionary.
        
        This method builds a new dictionary that contains the options for the
        utilities read.
        
        options[in]        list of options for utilities.
        
        Return dictionary - list of options for all utilities.
        """
        dictionary_list = []
        for option in options:
            name = option.get('long_name', '')
            if len(name) == 0:
                continue
            name = '--' + name
            alias = option.get('alias', None)
            if alias is not None:
                name = '-' + alias + ", " + name
            item = {
                'long_name'   : name,
                'description' : option.get('description', '')
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


    def get_usage(self, util_info):
        """Get the usage statement for the utility
        
        util_info[in]  dictionary entry for utility information
        
        Returns string usage statement
        """
        # Check type of util_info
        if util_info is None or util_info == {} or \
           not type(util_info) == type({}):
            return False

        return util_info['usage']
