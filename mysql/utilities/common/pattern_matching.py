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
This file contains auxiliary functions to handle pattern matching.
"""

import re


# Regular expression to match a database object identifier (support backticks)
REGEXP_OBJ_NAME = r'(`(?:[^`]|``)+`|\w+|\w+[\%\*]?|[\%\*])'

# Regular expression to match a database object identifier with ansi quotes
REGEXP_OBJ_NAME_AQ = r'("(?:[^"]|"")+"|\w+|\*)'

# Regular expression to match a qualified object identifier (with multiple
# parts). Example: db.obj, db or obj
REGEXP_QUALIFIED_OBJ_NAME = r'{0}(?:(?:\.){0})?'.format(REGEXP_OBJ_NAME)

# Same as the above but for use with ansi quotes
REGEXP_QUALIFIED_OBJ_NAME_AQ = r'{0}(?:(?:\.){0})?'.format(REGEXP_OBJ_NAME_AQ)


def convertSQL_LIKE2REGEXP(sql_like_pattern):
    """Convert a standard SQL LIKE pattern to a REGEXP pattern.

    Function that transforms a SQL LIKE pattern to a supported python
    regexp. Returns a python regular expression (i.e. regexp).

    sql_like_pattern[in] pattern in the SQL LIKE form to be converted.
    """
    # Replace '_' by equivalent regexp, except when precede by '\'
    # (escape character)
    regexp = re.sub(r'(?<!\\)_', '.', sql_like_pattern)
    # Replace '%' by equivalent regexp, except when precede by '\'
    # (escape character)
    regexp = re.sub(r'(?<!\\)%', '.*', regexp)
    # Set regexp to ignore cases; SQL patterns are case-insensitive by default.
    regexp = "(?i)^(" + regexp + ")$"
    return regexp


def parse_object_name(qualified_name, sql_mode='', wild=False):
    """Parses a qualified object name from the given string.

    qualified_name[in] MySQL object string (e.g. db.table)
    sql_mode[in]       The value of sql_mode from the server.
    wild[in]           Look for wildcards (stating at end of str)

    Returns tuple containing name split
    """
    if "ANSI_QUOTES" in sql_mode:
        regex_pattern = REGEXP_QUALIFIED_OBJ_NAME.replace("`", '"')
    else:
        regex_pattern = REGEXP_QUALIFIED_OBJ_NAME
    if wild:
        regex_pattern = regex_pattern + r'\Z'
    # Split the qualified name considering backtick quotes
    parts = re.match(regex_pattern, qualified_name)
    if parts:
        return parts.groups()
    else:
        return (None, None)
