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
This module contains classes and functions used to manage a user-defined
variables.
"""

import re
from mysql.utilities.common.format import print_dictionary_list

class Variables(dict):
    """
    The Variables class contains user-defined variables for replacement
    in custom commands. 
    """

    def __init__(self, options={}, data={}):
        """Constructor
        
        options[in]        Width
        data[in]           Data to initialize class
        """
        self.options = options
        self.width = options.get('width', 80)
        super(Variables, self).__init__(data)


    def find_variable(self, name):
        """Find a variable
        
        This method searches for a variable in the list and returns it
        if found.
        
        name[in]           Name of variable
        
        Returns dict - variable if found, None if not found.
        """
        if name in self:
            return { name: self[name] }
        return None
    

    def add_variable(self, name, value):
        """Add variable to the list
        
        name[in]           Name of variable
        value[in]          Value to store
        """
        self[name] = value
    

    def get_matches(self, prefix):
        """Get a list of variables that match a prefix
        
        This method returns a list of the variables that match the first N
        characters specified by var_prefix.
        
        var_prefix[in]     Prefix for search
        
        Returns list - matches or [] for no matches
        """
        result = []
        for key, value in self.iteritems():
            if key.startswith(prefix):
                result.append({ key: value })
        return result

    
    def show_variables(self, variables={}):
        """Display variables
        
        This method displays the variables included in the list passed or all
        variables is list passed is empty.
        
        variables[in]      List of variables
        """
        if self.options.get("quiet", False):
            return
        
        var_list = [ { 'name': key, 'value': value }
                     for key, value in self.iteritems() ]
        
        print "\n"
        if not self:
            print "There are no variables defined.\n"
            return
        
        print_dictionary_list(['Variable', 'Value'], ['name', 'value'],
                              var_list, self.width)
        print

    
    def replace_variables(self, cmd_string):
        """Replace all instances of variables with their values.
        
        This method will search a string for all variables designated by the
        '$' prefix and replace it with values from the list.
        
        cmd_string[in]     String to search
        
        Returns string - string with variables replaced
        """
        misses = []
        new_cmd = cmd_string
        finds = re.findall(r'\$(\w+)', cmd_string)
        for variable in finds:
            try:
                new_cmd = new_cmd.replace('$' + variable, str(self[variable]))
            except KeyError:
                # something useful when variable was not found?
                pass
        return new_cmd


    def search_by_key(self, pattern):
        """Find value by key pattern
        
        pattern[in]    regex pattern
        
        Returns tuple - key, value
        """
        regex = re.compile(pattern)
        
        for key, value in self.iteritems():
            if regex.match(key):
                yield key, value

