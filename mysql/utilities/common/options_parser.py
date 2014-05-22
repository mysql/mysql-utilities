#
# Copyright (c) 2014, Oracle and/or its affiliates. All rights reserved.
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
This module contains the MySQLOptionsParser used to read the MySQL
configuration files.

This module belongs to Connector python, and it should be removed once
C/py v2.0.0 is released and in the meanwhile will be used from here.

"""

import os
from ConfigParser import SafeConfigParser, MissingSectionHeaderError
from collections import OrderedDict

DEFAULT_OPTION_FILES = {
    'nt': 'C:\\my.ini',
    'posix': '/etc/mysql/my.cnf'
}

DEFAULT_EXTENSIONS = {
    'nt': ('ini', 'cnf'),
    'posix': 'cnf'
}


class MySQLOptionsParser(SafeConfigParser):
    """This class implements methods to parse MySQL option files"""

    def __init__(self, files=None, defaults=False):
        """If defaults is True, default option files are read first

        files[in]       The files to parse searching for configuration items.
        defaults[in]    Use the defaults to extend the search (default False).

        Raises ValueError if defaults is set to True but defaults files
        cannot be found.
        """
        SafeConfigParser.__init__(self, allow_no_value=True)
        self.default_file = None
        self.default_extension = DEFAULT_EXTENSIONS[os.name]

        if not files and not defaults:
            raise ValueError('Either files argument should be given or/and '
                             'defaults should be set to true')

        if files is None:
            files = []
        if isinstance(files, str):
            self.files = [files]
        else:
            self.files = files

        if defaults:
            self.default_file = DEFAULT_OPTION_FILES[os.name]
            if os.path.isfile(self.default_file):
                self.files.append(self.default_file)
            else:
                raise ValueError("Unable to find default option file at"
                                 "location '{path}'".format(self.default_file))

        self._parse_options(list(self.files))

    def _parse_options(self, files):
        """Parse options from files given as arguments.
        This method checks for !include or !inculdedir directives and if there
        is any, those files included by these directives are also parsed
        for options.

        files[in]       The files to parse searching for configuration items.

        Raises ValueError if any of the included or file given in arguments
        is not readable.
        """
        index = 0

        for file_ in files:
            try:
                with open(file_, 'r') as fp:
                    for line in fp.readlines():
                        if line.startswith('!includedir'):
                            dir_path = line.split()[1]
                            for entry in os.listdir(dir_path):
                                entry = os.path.join(dir_path, entry)
                                if entry in files:
                                    raise ValueError('Same option file '
                                                     'occurring more than '
                                                     'once.')
                                if os.path.isfile(entry) and \
                                   entry.endswith(self.default_extension):
                                    files.insert(index + 1, entry)

                        elif line.startswith('!include'):
                            filename = line.split()[1]
                            if filename not in files:
                                files.insert(index + 1, line.split()[1])
                            else:
                                raise ValueError('Same option file occurring '
                                                 'more than once.')
                        index += 1

            except (IOError, OSError) as exc:
                raise ValueError(exc)

        read_files = self.read(files)
        not_read_files = set(files) - set(read_files)
        if not_read_files:
            raise ValueError("{0} Cannot be read.".format(
                ', '.join(not_read_files)))

    def read(self, filenames):
        """Read and parse a filename or a list of filenames.

        filenames[in]    The file names to read.

        Files that cannot be opened are silently ignored;
        A single filename may also be given.
        Overridden from ConfigParser and modified so as to allow options
        which are not inside any section header

        Return list of successfully read files.
        """
        if isinstance(filenames, str):
            filenames = [filenames]
        read_ok = []
        for filename in filenames:
            try:
                fp = open(filename)
            except IOError:
                continue
            try:
                self._read(fp, filename)
            except MissingSectionHeaderError:
                self._read(fp, filename)
            fp.close()
            read_ok.append(filename)
        return read_ok

    def get_groups(self, *args):
        """Returns options from all the groups specified as arguments, returns
        the options from all groups if no argument provided. Options are
        overridden when they are found in the next group.

        *args[in]    Each group to be returned can be requested by given his
                     name as an argument.

        Returns a dictionary
        """
        if len(args) == 0:
            args = self._sections.keys()

        options = {}
        for group in args:
            try:
                options.update(dict(self._sections[group]))
            except KeyError:
                pass

        for key in options.keys():
            if key == '__name__' or key.startswith('!'):
                del options[key]
        return options

    def get_groups_as_dict(self, *args):
        """Returns options from all the groups specified as arguments. For each
        group the option are contained in a dictionary. The order in which
        the groups are specified is important as the method returns an
        OrderedDict which maintains the order of groups. Options are not
        overridden in between the groups.

        *args[in]    Each group to be returned can be requested by given his
                     name as an argument.

        Returns an OrderedDict of dictionaries
        """
        if len(args) == 0:
            args = self._sections.keys()

        options = OrderedDict()
        for group in args:
            try:
                options[group] = dict(self._sections[group])
            except KeyError:
                pass

        for group in options.keys():
            for key in options[group].keys():
                if key == '__name__' or key.startswith('!'):
                    del options[group][key]
        return options
