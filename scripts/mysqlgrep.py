#!/usr/bin/python

import MySQLdb
import optparse
import re

from mysql.utilities.common.options import parse_connection
from mysql.utilities.common.exception import FormatError

# Mapping database object to information schema names and fields. I
# wish that the tables would have had simple names and not qualify the
# names with the kind as well, e.g., not "table.table_name" but rather
# "table.name".
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
}

_SELECT_TYPE_FRM = """
  SELECT
    %(type_field)s AS `Type`,
    %(field_name)s AS `Name`,
    %(schema_field)s AS `Schema`
  FROM
    INFORMATION_SCHEMA.%(table_name)s
  WHERE
    %(field_name)s %(regex)s %(pattern)s%(extra_condition)s
"""

def obj2sql(obj):
    """Convert a Python object to an SQL object.

    This function convert Python objects to SQL values using the
    conversion functions in the database connector package."""
    from MySQLdb.converters import conversions
    return conversions[type(obj)](obj, conversions)

def make_select(objtype, pattern, check_body, use_regex):
    """Generate a SELECT statement for finding an object.
    """
    options = {
        'pattern': obj2sql(pattern),
        'regex': 'REGEXP' if use_regex else 'LIKE',
        'extra_condition': '',
        }
    options.update(_OBJMAP[objtype])
    if check_body and "body_field" in options:
        options["extra_condition"] = " OR %(body_field)s %(regex)s %(pattern)s" % options
    return _SELECT_TYPE_FRM % options

def ptw_max_len(a,b):
    """Used with reduce to compute the maximum lengths of the sequence
    elements in the list.

    >>> ptw_max_len((5,8), ("abrakadabra","boo"))
    (11, 8)
    """
    return tuple(map(max, a, tuple(map(len,b))))

parser = optparse.OptionParser(version="0.1",
                               usage="usage: %prog [options] server ...")

parser.add_option("-b", "--body",
                  dest="check_body", action="store_true", default=False,
                  help="Search the body of routines, triggers, and events as well")

# Add some more advanced parsing here to handle types better.
parser.add_option('--type',
                  dest="types", default="routine,event,trigger,table,database",
                  help="""Types to search: a comma-separated list of 'routine', 'event', 'trigger', 'table', and/or 'database'""")
parser.add_option("-G", "--basic-regexp", "--regexp",
                  dest="use_regex", action="store_true", default=False,
                  help="Use 'REGEXP' operator to match pattern. Default is to use 'LIKE'.")

parser.add_option("-p", "--print-sql", "--sql",
                  dest="print_stmt", action="store_true", default=False,
                  help="Print the statement instead of sending it to the server")
                  
options, args = parser.parse_args()

try:
    _pattern = args.pop(0)
except IndexError:
    parser.error("No pattern supplied")

_types = re.split(r"\s*,\s*", options.types)

entries = []
try:
    stmts = [make_select(t, _pattern, options.check_body, options.use_regex) for t in _types]
    sql = "UNION".join(stmts)
    if options.print_stmt:
        print sql
    else:
        for arg in args:
            info = parse_connection(arg)

            connection = MySQLdb.connect(**info)
            cursor = connection.cursor()
            cursor.execute(sql)
            entries.extend([ tuple([arg] + list(row)) for row in cursor])

        _headers = ("Server", "Type", "Name", "Database")

        # Compute the maximum width for each field. We include the
        # headers in the computation in case the values are narrower
        # than the headers.
        _max = reduce(ptw_max_len, entries, tuple(map(len,_headers)))

        # Build the format string from the maximum of each field and
        # add 2 to the width. All fields are left-adjusted.
        _formats = [ "{%d:<%d}" % (i,w+2) for i, w in zip(range(0, len(_max)), _max) ]
        _format = ''.join(_formats)

        # Printing table in compact docutils table format
        print _format.format(*map(lambda a: "=" * a, _max))
        print _format.format(*_headers)
        print _format.format(*map(lambda a: "=" * a, _max))
        for entry in entries:
            print _format.format(*entry)
        print _format.format(*map(lambda a: "=" * a, _max))

except FormatError as details:
    parser.error(details)
