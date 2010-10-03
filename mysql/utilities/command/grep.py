#
# Copyright (c) 2010, Oracle and/or its affiliates. All rights reserved.
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
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307 USA
#

"""Module for searching MySQL database servers for objects by name or content.
"""

import MySQLdb
import sys

from ..common.options import parse_connection
from ..common.format import format_tabular_list

# Mapping database object to information schema names and fields. I
# wish that the tables would have had simple names and not qualify the
# names with the kind as well, e.g., not "table.table_name" but rather
# "table.name". If that was the case, these kinds of scripts would be
# a lot easier to develop.
_OBJMAP = {
    'table': {
        'field_name': 'table_name',
        'table_name': 'tables',
        'type_field': "'TABLE'",
        'schema_field': 'table_schema',
        },
    'event': {
        'field_name': 'event_name',
        'table_name': 'events',
        'type_field': "'EVENT'",
        'schema_field': 'event_schema',
        'body_field': 'event_body',
        },
    'routine': {
        'field_name': 'routine_name',
        'table_name': 'routines',
        'type_field': 'routine_type',
        'schema_field': 'routine_schema',
        'body_field': 'routine_body',
        },
    'trigger': {
        'field_name': 'trigger_name',
        'table_name': 'triggers',
        'type_field': "'TRIGGER'",
        'schema_field': 'trigger_schema',
        'body_field': 'action_statement',
        },
    'database': {
        'field_name': 'schema_name',
        'table_name': 'schemata',
        'type_field': "'SCHEMA'",
        'schema_field': 'schema_name',
        },        
    'view': {
        'field_name': 'table_name',
        'table_name': 'views',
        'type_field': "'VIEW'",
        'schema_field': 'table_schema',
        },
    'user': {
        'select_option': 'DISTINCT',
        'field_name': 'grantee',
        'table_name': 'schema_privileges',
        'type_field': "'USER'",
        'schema_field': 'table_schema',
        'body_field': 'privilege_type',
        },
}

_SELECT_TYPE_FRM = """
  SELECT %(select_option)s
    %(type_field)s AS `Type`,
    %(field_name)s AS `Name`,
    %(schema_field)s AS `Schema`
  FROM
    information_schema.%(table_name)s
  WHERE
    %(field_name)s %(regex)s %(pattern)s%(extra_condition)s
"""

def _obj2sql(obj):
    """Convert a Python object to an SQL object.

    This function convert Python objects to SQL values using the
    conversion functions in the database connector package."""
    from MySQLdb.converters import conversions
    return conversions[type(obj)](obj, conversions)

def _make_select(objtype, pattern, check_body, use_regexp):
    """Generate a SELECT statement for finding an object.
    """
    options = {
        'pattern': _obj2sql(pattern),
        'regex': 'REGEXP' if use_regexp else 'LIKE',
        'extra_condition': '',
        'select_option': '',
        }
    options.update(_OBJMAP[objtype])
    if check_body and "body_field" in options:
        options["extra_condition"] = " OR %(body_field)s %(regex)s %(pattern)s" % options
    return _SELECT_TYPE_FRM % options

def _spec(info):
    """Create a server specification string from an info structure."""
    result = "%(user)s:<password>@%(host)s:%(port)s" % info
    if "unix_socket" in info:
        result += ":" + info["unix_socket"]
    return result

def _join_words(words, delimiter=",", conjunction="and"):
    """Join words together for nice printout.

    >>> _join_words(["first", "second", "third"])
    'first, second, and third'
    >>> _join_words(["first", "second"])
    'first and second'
    >>> _join_words(["first"])
    'first'
    """
    if len(words) == 1:
        return words[0]
    elif len(words) == 2:
        return ' {0} '.format(conjunction).join(words)
    else:
        return '{0} '.format(delimiter).join(words[0:-1]) + "%s %s %s" % (delimiter, conjunction, words[-1])

ROUTINE, EVENT, TRIGGER, TABLE, DATABASE, VIEW, USER = 'routine', 'event', 'trigger', 'table', 'database', 'view', 'user'

#: List of all object types that can be searched
OBJECT_TYPES = [ ROUTINE, EVENT, TRIGGER, TABLE, DATABASE, VIEW, USER ]

class ObjectGrep(object):
    """Search for objects on a MySQL server by name or content.

    This command class is used to search one or more MySQL server
    instances for objects where the name (or the contents of routines,
    triggers, or events) match a given pattern.
    """
    def __init__(self, pattern, types=OBJECT_TYPES, check_body=False, use_regexp=False):
        stmts = [_make_select(t, pattern, check_body, use_regexp) for t in types]
        self.__sql = "UNION".join(stmts)

        # Need to save the pattern for informative error messages later
        self.__pattern = pattern 
        self.__types = types

    def sql(self):
        """Return SQL code for performing this search.
        """
        return self.__sql;

    def execute(self, connections, output=sys.stdout, connector=MySQLdb):
        """Perform a search on a list of servers.
        """

        from ..common.exception import FormatError, EmptyResultError

        entries = []
        for info in connections:
            # If the connection is string-like, we assume it is a
            # server specification and parse it. Otherwise, connection
            # info is expected and we just use it directly.
            if isinstance(info, basestring):
                conn = parse_connection(info)
                if not conn:
                    msg = "'%s' is not a valid connection specifier" % (info,)
                    raise FormatError(msg)
                info = conn
            connection = connector.connect(**info)
            cursor = connection.cursor()
            cursor.execute(self.__sql)
            entries.extend([tuple([_spec(info)] + list(row)) for row in cursor])
        if len(entries) > 0:
            format_tabular_list(output, ("Connection", "Type", "Name", "Database"), entries)
        else:
            msg = "Nothing matches '%s' in any %s" % (self.__pattern, _join_words(self.__types, conjunction="or"))
            raise EmptyResultError(msg)
