#
# Copyright (c) 2013, Oracle and/or its affiliates. All rights reserved.
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
This module contains the charset_info class designed to read character set
and collation information from /share/charsets/index.xml.
"""

import sys

from mysql.utilities.common.format import print_list

_CHARSET_INDEXES = ID, CHARACTER_SET_NAME, COLLATION_NAME, MAXLEN, IS_DEFAULT \
    = range(0, 5)

_CHARSET_QUERY = """
SELECT CL.ID,CL.CHARACTER_SET_NAME,CL.COLLATION_NAME,CS.MAXLEN, CL.IS_DEFAULT
FROM INFORMATION_SCHEMA.CHARACTER_SETS CS, INFORMATION_SCHEMA.COLLATIONS CL
WHERE CS.CHARACTER_SET_NAME=CL.CHARACTER_SET_NAME ORDER BY CHARACTER_SET_NAME
"""


class CharsetInfo(object):
    """
    Read character set information for lookup. Methods include:

      - get_charset_name(id) : get the name for a characterset id
      - get_default_collation(name) : get default collation name
      - get_name_by_collation(name) : given collation, find charset name
      - print_charsets() : print the character set map

    """

    def __init__(self, options=None):
        """Constructor

        options[in]        array of general options
        """
        if options is None:
            options = {}
        self.verbosity = options.get("verbosity", 0)
        self.format = options.get("format", "grid")
        self.server = options.get("server", None)

        self.charset_map = None

        if self.server:
            self.charset_map = self.server.exec_query(_CHARSET_QUERY)

    def print_charsets(self):
        """Print the character set list
        """
        print_list(sys.stdout, self.format,
                   ["id", "character_set_name", "collation_name",
                    "maxlen", "is_default"],
                   self.charset_map)
        print len(self.charset_map), "rows in set."

    def get_name(self, chr_id):
        """Get the character set name for the given id

        chr_id[in]     id for character set (as read from .frm file)

        Returns string - character set name or None if not found.
        """
        for cs in self.charset_map:
            if int(chr_id) == int(cs[ID]):
                return cs[CHARACTER_SET_NAME]
        return None

    def get_collation(self, col_id):
        """Get the collation name for the given id

        col_id[in]     id for collation (as read from .frm file)

        Returns string - collation name or None if not found.
        """
        for cs in self.charset_map:
            if int(col_id) == int(cs[ID]):
                return cs[COLLATION_NAME]
        return None

    def get_name_by_collation(self, colname):
        """Get the character set name for the given collation

        colname[in]    collation name

        Returns string - character set name or None if not found.
        """
        for cs in self.charset_map:
            if cs[COLLATION_NAME] == colname:
                return cs[CHARACTER_SET_NAME]
        return None

    def get_default_collation(self, col_id):
        """Get the default collation for the character set

        col_id[in]     id for collation (as read from .frm file)

        Returns tuple - (default collation id, name) or None if not found.
        """
        # Exception for utf8
        if col_id == 83:
            return "utf8_bin"
        for cs in self.charset_map:
            if int(cs[ID]) == int(col_id) and cs[IS_DEFAULT].upper() == "YES":
                return cs[COLLATION_NAME]
        return None

    def get_maxlen(self, col_id):
        """Get the maximum length for the character set

        col_id[in]     id for collation (as read from .frm file)

        Returns int - max length or 1 if not found.
        """
        for cs in self.charset_map:
            if int(cs[ID]) == int(col_id):
                return int(cs[MAXLEN])
        return int(1)
