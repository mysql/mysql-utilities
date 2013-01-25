#
# Copyright (c) 2013 Oracle and/or its affiliates. All rights reserved.
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
This module provides features to read MySQL configuration files, wrapping the
tool my_print_defaults.
"""

import optparse
import os.path
import re
import subprocess
import tempfile

from mysql.utilities.common.tools import get_tool_path
from mysql.utilities.exception import UtilError


_MY_PRINT_DEFAULTS_TOOL = "my_print_defaults"
_MYLOGIN_FILE = ".mylogin.cnf"


def my_login_config_path():
    """Return the default path of the mylogin file (.mylogin.cnf).
    """
    if os.name == 'posix':
        # File located in $HOME for non-Windows systems
        return os.path.expanduser('~')
    else:
        # File located in %APPDATA%\MySQL for Windows systems
        return os.environ['APPDATA'] + '\MySQL'


def my_login_config_exists():
    """Check if the mylogin file (.mylogin.cnf) exists.
    """

    my_login_fullpath = os.path.normpath(my_login_config_path() + "/"
                                         + _MYLOGIN_FILE)
    return os.path.isfile(my_login_fullpath)


class MyDefaultsReader(object):
    """The MyDefaultsReader class is used to read the data stored from a MySQL
    configuration file. This class provide methods to read the options data
    stored in configurations files, using the my_print_defaults tool. To learn
    more about my_print_defaults see:
    http://dev.mysql.com/doc/en/my-print-defaults.html
    """

    def __init__(self, options={}, find_my_print_defaults_tool=True):
        """Constructor

        options[in]                 dictionary of options (e.g. basedir). Note,
                                    allows options values from optparse to be
                                    passed directly to this parameter.
        find_my_print_defaults[in]  boolean value indicating if the tool
                                    my_print_defaults should be located upon
                                    initialization of the object.
        """
        # _config_data is a dictionary of option groups containing a dictionary
        # of the options data read from the configuration file.
        self._config_data = {}

        # Options values from optparse can be directly passed, check if it is
        # the case and handle them correctly.
        if isinstance(options, optparse.Values):
            try:
                self._basedir = options.basedir
            except AttributeError:
                # if the attribute is not found, then set it to None (default).
                self._basedir = None
            try:
                # if the attribute is not found, then set it to 0 (default).
                self._verbosity = options.verbosity
            except AttributeError:
                self._verbosity = 0
        else:
            self._basedir = options.get("basedir", None)
            self._verbosity = options.get("verbosity", 0)

        if find_my_print_defaults_tool:
            self.search_my_print_defaults_tool()
        else:
            self._tool_path = None

    @property
    def tool_path(self):
        return self._tool_path

    def search_my_print_defaults_tool(self, search_paths=[]):
        """Search for the tool my_print_defaults.
        """
        # Set the default search paths (i.e., default location of the
        # .mylogin.cnf file).
        default_paths = [my_login_config_path()]

        # Extend the list of path to search with the ones specified.
        if search_paths:
            default_paths.extend(search_paths)

        # Search for the tool my_print_defaults.
        try:
            self._tool_path = get_tool_path(self._basedir,
                                            _MY_PRINT_DEFAULTS_TOOL,
                                            defaults_paths=default_paths,
                                            search_PATH=True)
        except UtilError as err:
            raise UtilError("Unable to locate MySQL Client tools. "
                            "Please confirm that the path to the MySQL client "
                            "tools are included in the PATH. Error: %s"
                            % err.errmsg)

    def check_tool_version(self, major_version, minor_version):
        """Check the version of the my_print_defaults tool.

        Returns True if the version of the tool is equal or above the one that
        is specified, otherwise False.
        """
        # The path to the tool must have been previously found.
        assert self._tool_path, ("First, the required MySQL tool must be "
                                 "found. E.g., use method "
                                 "search_my_print_defaults_tool.")

        # Create a temporary file to redirect stdout
        out_file = tempfile.TemporaryFile()
        if self._verbosity > 0:
            subprocess.call([self._tool_path, "--version"], stdout=out_file)
        else:
            # Redirect stderr to null
            null_file = open(os.devnull, "w+b")
            subprocess.call([self._tool_path, "--version"], stdout=out_file,
                            stderr=null_file)
        # Read --version output
        out_file.seek(0)
        line = out_file.readline()
        out_file.close()

        # Parse the version value
        match = re.search(r'(?:Ver )(\d)\.(\d)', line)
        if match:
            major, minor = match.groups()
            if (major_version < int(major)) or \
               (major_version == int(major) and minor_version <= int(minor)):
                return True
            else:
                return False
        else:
            raise UtilError("Unable to determine tool version - %s" %
                            self._tool_path)

    def check_login_path_support(self):
        """Checks if the used my_print_defaults tool supports login-paths.
        """
        # The path to the tool must have been previously found.
        assert self._tool_path, ("First, the required MySQL tool must be "
                                 "found. E.g., use method "
                                 "search_my_print_defaults_tool.")

        # Create a temporary file to redirect stdout
        out_file = tempfile.TemporaryFile()
        if self._verbosity > 0:
            subprocess.call([self._tool_path, "--help"], stdout=out_file)
        else:
            # Redirect stderr to null
            null_file = open(os.devnull, "w+b")
            subprocess.call([self._tool_path, "--help"], stdout=out_file,
                            stderr=null_file)
        # Read --help output
        out_file.seek(0)
        help_output = out_file.read()
        out_file.close()

        # Check the existence of a "login-path" option
        if 'login-path' in help_output:
            return True
        else:
            return False

    def _read_group_data(self, group):
        """Read group options data using my_print_defaults tool.
        """
        # The path to the tool must have been previously found.
        assert self._tool_path, ("First, the required MySQL tool must be "
                                 "found. E.g., use method "
                                 "search_my_print_defaults_tool.")

        # Group not found; use my_print_defaults to get group data.
        out_file = tempfile.TemporaryFile()
        if self._verbosity > 0:
            subprocess.call([self._tool_path, group], stdout=out_file)
        else:
            # Redirect stderr to null
            null_file = open(os.devnull, "w+b")
            subprocess.call([self._tool_path, group], stdout=out_file,
                            stderr=null_file)

        # Read and parse group options values.
        out_file.seek(0)
        results = []
        for line in out_file:
            # Parse option value; ignore starting "--"
            key_value = line[2:].split("=", 1)
            if len(key_value) == 2:
                # Handle option format: --key=value and --key=
                results.append((key_value[0], key_value[1].strip()))
            elif len(key_value) == 1:
                # Handle option format: --key
                results.append((key_value[0], True))
            else:
                raise UtilError("Invalid option value format for "
                                "group %s: %s" % (group, line))
        out_file.close()

        if len(results):
            self._config_data[group] = dict(results)
        else:
            self._config_data[group] = None

        return self._config_data[group]

    def get_group_data(self, group):
        """Retrieve the data associated to the given group.
        """
        # Returns group's data locally stored, if available.
        try:
            return self._config_data[group]
        except KeyError:
            # Otherwise, get it using my_print_defaults.
            return self._read_group_data(group)

    def get_option_value(self, group, opt_name):
        """Retrieve the value associated to the given opt_name in the group.
        """
        # Get option value, if group's data is available.
        grp_options = self.get_group_data(group)
        if grp_options:
            return grp_options.get(opt_name, None)
        else:
            return None
