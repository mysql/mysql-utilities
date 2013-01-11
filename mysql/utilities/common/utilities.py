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
import re
import subprocess

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
    def _search_paths(needles, paths):
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
        #This is needed on windows without a python setup, cause needs to
        #find the executable scripts.
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
        pattern_usage = ("(?P<Usage>Usage:\s.*?)\w+\s\-\s" #this match first
                         # section <Usage> matching all till find a " - "
                         "(?P<Description>.*?)" # Description is the text next
                         # to " - " and till next match.
                         "(?P<O>\w*):"  # This is beginning of Options section
                         "(?P<Options>.*)" # this match  the utility options
                         )
        self.program_usage = re.compile(pattern_usage, re.S)    

        pattern_options = ("^(?P<Alias>\s\s\-.*?)\s{2,}" # Option Alias
                           # followed by 2 o more spaces is his description
                           "(?P<Desc>.*?)(?=^\s\s\-)" # description is all
                           # text till not found other alias in the form
                           # <-|--Alias> at the begining of the line.
                           )
        self.program_options = re.compile(pattern_options, re.S|re.M)

        pattern_option = "\s+\-\-(.*?)\s" # match Alias of the form <--Alias>
        self.program_option = re.compile(pattern_option)
        pattern_alias = "\s+\-(\w+)\s*" # match Alias of the form <-Alias>
        self.program_name = re.compile(pattern_alias)

        files = os.listdir(self.util_path)

        working_utils = []
        for file_name in files:
            parts = os.path.splitext(file_name)
            # Only accept python files - not .pyc and others
            # Parts returns second as empty if does not have ext, so len is 2
            exts = ['.py', '.exe', '']
            if (parts[0] not in _EXCLUDE_UTILS and
                (len(parts) == 1 or (len(parts) == 2 and parts[1] in exts))):
                util_name = str(parts[0])
                if util_name not in working_utils: 
                    util_info = self._get_util_info(self.util_path, util_name, 
                                                    file_name, parts[1])
                    if util_info and util_info["usage"]:
                        self.util_list.append(util_info)
                        working_utils.append(util_name)

        self.util_list.sort(key=lambda util_list:util_list['name'])
    

    def _get_util_info(self, util_path, util_name, file_name, file_ext):
        """Get information about utility
        
        util_path[in]  path to utilities
        util_name[in]  name of utility to get information
        
        Returns dictionary - name, description, usage, options
        """
        # Get the --help output for the utility
        command = util_name + ".py"
        if not os.path.exists(os.path.join(util_path, command)):
            command = file_name 
        cmd = []
        if not file_ext == '.exe':
            cmd.append('python ')
        
        cmd += ['"', os.path.join(util_path, command), '"', " --help"]

        # Hide errors from stderr output
        out = open(os.devnull, 'w')
        proc = subprocess.Popen("".join(cmd), shell=True,
                                stdout=subprocess.PIPE, stderr=out)

        stdout_temp = proc.communicate()[0]
        # Parse the help output and save the information found
        alias = None
        usage = None
        description = None
        options = []
        option = None

        res = self.program_usage.match(stdout_temp.replace("\r", ""))
        Options = ""
        if not res:
            return None
        else:
            usage = res.group("Usage").replace("\n", "")
            desc_clean = res.group("Description").replace("\n", " ").split()
            description = (" ".join(desc_clean)) + " "
            #standardize string. 
            Options =  res.group("Options") + "\n  -"

        res = self.program_options.findall(Options)

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

            desc_clean = opt[1].replace("\n"," ").split()
            option['description'] = " ".join(desc_clean)
            option['long_name'] = option['name']
            parts = option['name'].split('=')
            option['req_value'] = len(parts) == 2
            if option['req_value']:
                option['name'] = parts[0]
            if option:
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
