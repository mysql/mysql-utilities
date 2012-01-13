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
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301 USA
#

import sys

import mysql.connector

from ..common.options import parse_connection
from ..common.format import print_list

# Mapping database object to information schema names and fields. I
# wish that the tables would have had simple names and not qualify the
# names with the kind as well, e.g., not "table.table_name" but rather
# "table.name". If that was the case, these kinds of scripts would be
# a lot easier to develop.
#
# The fields in each entry are:
#
# field_name
#   The name of the column in the table where the field name to match
#   can be found. 
# field_type
#   The name of the type of the field. Usually a string.
# object_name
#   The name of the column where the name of the object being searched
#   can be found.
# object_type
#   The name of the type of the object being searched. Usually a
#   string.
# schema_field
#   The name of the field where the schema name can be found.
# table_name
#   The name of the information schema table to search in.
# [body_field]
#   The name of the field in the table where the body of the object
#   can be found. This is an optional entry since not all objects have
#   bodies.
_OBJMAP = {
    'partition': {
        'field_name': 'partition_name',
        'object_name': 'table_name',
        'object_type': "'TABLE'",
        'schema_field': 'table_schema',
        'table_name': 'partitions',
        },
    'column': {
        'field_name': 'column_name',
        'object_name': 'table_name',
        'table_name': 'columns',
        'object_type': "'TABLE'",
        'schema_field': 'table_schema',
        },
    'table': {
        'field_name': 'table_name',
        'object_name': 'table_name',
        'table_name': 'tables',
        'object_type': "'TABLE'",
        'schema_field': 'table_schema',
        },
    'event': {
        'field_name': 'event_name',
        'object_name': 'event_name',
        'table_name': 'events',
        'object_type': "'EVENT'",
        'schema_field': 'event_schema',
        'body_field': 'event_body',
        },
    'routine': {
        'field_name': 'routine_name',
        'object_name': 'routine_name',
        'table_name': 'routines',
        'object_type': 'routine_type',
        'schema_field': 'routine_schema',
        'body_field': 'routine_body',
        },
    'trigger': {
        'field_name': 'trigger_name',
        'object_name': 'trigger_name',
        'table_name': 'triggers',
        'object_type': "'TRIGGER'",
        'schema_field': 'trigger_schema',
        'body_field': 'action_statement',
        },
    'database': {
        'field_name': 'schema_name',
        'object_name': 'schema_name',
        'table_name': 'schemata',
        'object_type': "'SCHEMA'",
        'schema_field': 'schema_name',
        },        
    'view': {
        'field_name': 'table_name',
        'object_name': 'table_name',
        'table_name': 'views',
        'object_type': "'VIEW'",
        'schema_field': 'table_schema',
        },
    'user': {
        'select_option': 'DISTINCT',
        'field_name': 'grantee',
        'object_name': 'grantee',
        'table_name': 'schema_privileges',
        'object_type': "'USER'",
        'schema_field': 'table_schema',
        'body_field': 'privilege_type',
        },
}

_GROUP_MATCHES_FRM = """
SELECT 
  `Object Type`, `Object Name`, `Database`,
  `Field Type`, GROUP_CONCAT(`Field`) AS `Matches`
FROM ({0}) AS all_results
  GROUP BY `Object Type`, `Database`, `Object Name`, `Field Type`"""

_SELECT_TYPE_FRM = """
  SELECT {select_option}
    {object_type} AS `Object Type`,
    {object_name} AS `Object Name`,
    {schema_field} AS `Database`,
    {field_type} AS `Field Type`,
    {field_name} AS `Field`
  FROM
    information_schema.{table_name}
  WHERE
    {condition}
"""

def _make_select(objtype, pattern, database_pattern, check_body, use_regexp):
    """Generate a SELECT statement for finding an object.
    """
    from mysql.utilities.common.options import obj2sql

    options = {
        'pattern': obj2sql(pattern),
        'regex': 'REGEXP' if use_regexp else 'LIKE',
        'select_option': '',
        'field_type': "'" + objtype.upper() + "'",
        }
    options.update(_OBJMAP[objtype])

    # Build a condition for inclusion in the select
    condition = "{field_name} {regex} {pattern}".format(**options)
    if check_body and "body_field" in options:
        condition += " OR {body_field} {regex} {pattern}".format(**options)
    if database_pattern:
        options['database_pattern'] = obj2sql(database_pattern)
        condition = "({0}) AND {schema_field} {regex} {database_pattern}".format(condition, **options)
    options['condition'] = condition

    return _SELECT_TYPE_FRM.format(**options)

def _spec(info):
    """Create a server specification string from an info structure.
    """
    result = "%(user)s:*@%(host)s:%(port)s" % info
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

ROUTINE =  'routine'
EVENT =  'event'
TRIGGER =  'trigger'
TABLE =  'table'
DATABASE =  'database'
VIEW =  'view'
USER = 'user'
COLUMN = 'column'

OBJECT_TYPES = _OBJMAP.keys()

class ObjectGrep(object):
    """Grep for objects
    """
    
    def __init__(self, pattern, database_pattern=None, types=OBJECT_TYPES,
                 check_body=False, use_regexp=False):
        """Constructor
        
        pattern[in]          pattern to match
        database_pattern[in] database pattern to match (if present)
                             default - None = do not match database
        types[in]            list of object types to search
        check_body[in]       if True, search body of routines
                             default = False
        use_regexp[in]       if True, use regexp for compare
                             default = False
        """
        stmts = [_make_select(t, pattern, database_pattern, check_body, use_regexp) for t in types]
        self.__sql = _GROUP_MATCHES_FRM.format("UNION".join(stmts))

        # Need to save the pattern for informative error messages later
        self.__pattern = pattern 
        self.__types = types

    def sql(self):
        """Get the SQL command
        
        Returns string - SQL statement
        """
        return self.__sql;

    def execute(self, connections, output=sys.stdout, connector=mysql.connector,
                **kwrds):
        """Execute the search for objects
        
        This method searches for objects that match a search criteria for
        one or more servers.
        
        connections[in]    list of connection parameters
        output[in]         file stream to display information
                           default = sys.stdout
        connector[in]      connector to use
                           default = mysql.connector
        kwrds[in]          dictionary of options
          format           format for display
                           default = GRID
        """
        from mysql.utilities.exception import FormatError, EmptyResultError

        format = kwrds.get('format', "grid")
        entries = []
        for info in connections:
            conn = parse_connection(info)
            if not conn:
                msg = "'%s' is not a valid connection specifier" % (info,)
                raise FormatError(msg)
            info = conn
            connection = connector.connect(**info)
            cursor = connection.cursor()
            cursor.execute(self.__sql)
            entries.extend([tuple([_spec(info)] + list(row)) for row in cursor])

        headers = ["Connection"]
        headers.extend(col[0].title() for col in cursor.description)
        if len(entries) > 0 and output:
            print_list(output, format, headers, entries)
        else:
            msg = "Nothing matches '%s' in any %s" % (self.__pattern, _join_words(self.__types, conjunction="or"))
            raise EmptyResultError(msg)
