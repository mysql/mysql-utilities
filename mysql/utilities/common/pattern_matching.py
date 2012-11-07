#
# Copyright (c) 2012 Oracle and/or its affiliates. All rights reserved.
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
