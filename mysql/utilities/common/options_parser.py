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

import codecs
import io
import os
import re
from ConfigParser import SafeConfigParser, MissingSectionHeaderError
from mysql.utilities.common.tools import check_python_version

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

    def __init__(self, files=None, keep_dashes=True):
        """Initialize

        files[in]       The files to parse searching for configuration items.
        keep_dashes[in] If False, dashes in options are replaced with
                        underscores.

        Raises ValueError if defaults is set to True but defaults files
        cannot be found.
        """

        # Regular expression to allow options with no value(For Python v2.6)
        self.OPTCRE = re.compile(           # pylint: disable=C0103
            r'(?P<option>[^:=\s][^:=]*)'
            r'\s*(?:'
            r'(?P<vi>[:=])\s*'
            r'(?P<value>.*))?$'
        )

        self._options_dict = {}

        SafeConfigParser.__init__(self)
        self.default_extension = DEFAULT_EXTENSIONS[os.name]
        self.keep_dashes = keep_dashes

        if not files:
            raise ValueError('files argument should be given')
        if isinstance(files, str):
            self.files = [files]
        else:
            self.files = files

        self._parse_options(list(self.files))
        self._sections = self.get_groups_as_dict()

    def optionxform(self, optionstr):
        """Converts option strings

        optionstr[in] input to be converted.

        Converts option strings to lower case and replaces dashes(-) with
        underscores(_) if keep_dashes variable is set.

        """
        if not self.keep_dashes:
            optionstr = optionstr.replace('-', '_')
        return optionstr.lower()

    def _parse_options(self, files):
        """Parse options from files given as arguments.
         This method checks for !include or !includedir directives and if there
         is any, those files included by these directives are also parsed
         for options.

         files[in]       The files to parse searching for configuration items.

        Raises ValueError if any of the included or file given in arguments
        is not readable.
        """
        index = 0
        err_msg = "Option file '{0}' being included again in file '{1}'"

        for file_ in files:
            try:
                with open(file_, 'r') as op_file:
                    for line in op_file.readlines():
                        if line.startswith('!includedir'):
                            _, dir_path = line.split(None, 1)
                            for entry in os.listdir(dir_path):
                                entry = os.path.join(dir_path, entry)
                                if entry in files:
                                    raise ValueError(err_msg.format(
                                        entry, file_))
                                if (os.path.isfile(entry) and
                                        entry.endswith(
                                            self.default_extension)):
                                    files.insert(index + 1, entry)

                        elif line.startswith('!include'):
                            _, filename = line.split(None, 1)
                            if filename in files:
                                raise ValueError(err_msg.format(
                                    filename, file_))
                            files.insert(index + 1, filename)

                        index += 1

            except (IOError, OSError) as exc:
                raise ValueError("Failed reading file '{0}': {1}".format(
                    file_, str(exc)))

        read_files = self.read(files)
        not_read_files = set(files) - set(read_files)
        if not_read_files:
            raise ValueError("File(s) {0} could not be read.".format(
                ', '.join(not_read_files)))

    def read(self, filenames):
        """Read and parse a filename or a list of filenames.

        Overridden from ConfigParser and modified so as to allow options
        which are not inside any section header

        filenames[in]    The file names to read.

        Return list of successfully read files.
        """
        # Get python version since we must use str() to read strings from
        # the file for older, 2.6 versions of Python
        py26 = check_python_version((2, 6, 0), (2, 6, 99), False,
                                    None, False, False, False)
        if isinstance(filenames, str):
            filenames = [filenames]
        read_ok = []
        for priority, filename in enumerate(filenames):
            try:
                out_file = io.StringIO()
                for line in codecs.open(filename, encoding='utf-8'):
                    line = line.strip()
                    match_obj = self.OPTCRE.match(line)
                    if not self.SECTCRE.match(line) and match_obj:
                        optname, delimiter, optval = match_obj.group('option',
                                                                     'vi',
                                                                     'value')
                        if optname and not optval and not delimiter:
                            out_file.write(line + "=\n")
                        else:
                            out_file.write(line + '\n')
                    else:
                        out_file.write(line + '\n')
                out_file.seek(0)
                self._read(out_file, filename)
            except IOError:
                continue
            try:
                self._read(out_file, filename)
                for group in self._sections.keys():
                    try:
                        self._options_dict[group]
                    except KeyError:
                        self._options_dict[group] = {}
                    for option, value in self._sections[group].items():
                        if py26:
                            self._options_dict[group][option] = (str(value),
                                                                 priority)
                        else:
                            self._options_dict[group][option] = (value,
                                                                 priority)

                self._sections = self._dict()

            except MissingSectionHeaderError:
                self._read(out_file, filename)
            out_file.close()
            read_ok.append(filename)
        return read_ok

    def get_groups(self, *args):
        """Returns options as a dictionary.

        Returns options from all the groups specified as arguments, returns
        the options from all groups if no argument provided. Options are
        overridden when they are found in the next group.

        *args[in]    Each group to be returned can be requested by providing
                     its name as an argument.

        Returns a dictionary
        """
        if len(args) == 0:
            args = self._options_dict.keys()

        options = {}
        for group in args:
            try:
                for option, value in self._options_dict[group].items():
                    if option not in options or options[option][1] <= value[1]:
                        options[option] = value
            except KeyError:
                pass

        for key in options.keys():
            if key == '__name__' or key.startswith('!'):
                del options[key]
            else:
                options[key] = options[key][0]
        return options

    def get_groups_as_dict_with_priority(self, *args):  # pylint: disable=C0103
        """Returns options as dictionary of dictionaries.

        Returns options from all the groups specified as arguments. For each
        group the option are contained in a dictionary. The order in which
        the groups are specified is unimportant. Also options are not
        overridden in between the groups.

        The value is a tuple with two elements, first being the actual value
        and second is the priority of the value which is higher for a value
        read from a higher priority file.

        *args[in]    Each group to be returned can be requested by providing
                     its name as an argument.

        Returns an dictionary of dictionaries
        """
        if len(args) == 0:
            args = self._options_dict.keys()

        options = dict()
        for group in args:
            try:
                options[group] = dict(self._options_dict[group])
            except KeyError:
                pass

        for group in options.keys():
            for key in options[group].keys():
                if key == '__name__' or key.startswith('!'):
                    del options[group][key]
        return options

    def get_groups_as_dict(self, *args):
        """Returns options as dictionary of dictionaries.

        Returns options from all the groups specified as arguments. For each
        group the option are contained in a dictionary. The order in which
        the groups are specified is unimportant. Also options are not
        overridden in between the groups.

        *args[in]    Each group to be returned can be requested by providing
                     its name as an argument.

        Returns an dictionary of dictionaries
        """
        if len(args) == 0:
            args = self._options_dict.keys()

        options = dict()
        for group in args:
            try:
                options[group] = dict(self._options_dict[group])
            except KeyError:
                pass

        for group in options.keys():
            for key in options[group].keys():
                if key == '__name__' or key.startswith('!'):
                    del options[group][key]
                else:
                    options[group][key] = options[group][key][0]
        return options
