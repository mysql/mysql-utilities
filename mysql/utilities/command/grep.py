import MySQLdb
import sys

from mysql.utilities.common.options import parse_connection

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
}

_SELECT_TYPE_FRM = """
  SELECT
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
        }
    options.update(_OBJMAP[objtype])
    if check_body and "body_field" in options:
        options["extra_condition"] = " OR %(body_field)s %(regex)s %(pattern)s" % options
    return _SELECT_TYPE_FRM % options

def _ptw_max_len(a,b):
    """Point-wise max length.

    Used with reduce to compute the maximum lengths of a sequence of
    tuples of strings.

    >>> ptw_max_len((5,8), ("abrakadabra","boo"))
    (11, 8)
    """
    return tuple(map(max, a, tuple(map(len,b))))

def _print_result_table(entries, headers, output):
    # Compute the maximum width for each field. We include the
    # headers in the computation in case the values are narrower
    # than the headers.
    widths = reduce(_ptw_max_len, entries, tuple(map(len, headers)))

    # Build the format string from the maximum of each field and
    # add 2 to the width. All fields are left-adjusted.
    formats = [ "{%d:<%d}" % (i,w+2) for i, w in zip(range(0, len(widths)), widths) ]
    frm_str = ''.join(formats)

    print >>output, frm_str.format(*map(lambda a: "=" * a, widths))
    print >>output, frm_str.format(*headers)
    print >>output, frm_str.format(*map(lambda a: "=" * a, widths))
    for entry in entries:
        print >>output, frm_str.format(*entry)
    print >>output, frm_str.format(*map(lambda a: "=" * a, widths))

def _spec(info):
    """Create a server specification string from an info structure."""
    result = "%(user)s:%(passwd)s@%(host)s:%(port)s" % info
    if "unix_socket" in info:
        result += ":" + info["unix_socket"]
    return result

# Here are constants that can be used for the objects.
ROUTINE, EVENT, TRIGGER, TABLE, DATABASE = 'routine', 'event', 'trigger', 'table', 'database'

_TYPES = [ ROUTINE, EVENT, TRIGGER, TABLE, DATABASE ]

class ObjectGrep(object):
    def __init__(self, pattern, types=_TYPES, check_body=False, use_regexp=False):
        stmts = [_make_select(t, pattern, check_body, use_regexp) for t in types]
        self.__sql = "UNION".join(stmts)

    def sql(self):
        """Return SQL code for performing this search.
        """
        return self.__sql;

    def execute(self, connections, output=sys.stdout, connector=MySQLdb):
        entries = []
        for info in connections:
            # If the connection is string-like, we assume it is a
            # server specification and parse it. Otherwise, connection
            # info is expected and we just use it directly.
            if isinstance(info, basestring):
                info = parse_connection(info)
            connection = connector.connect(**info)
            cursor = connection.cursor()
            cursor.execute(self.__sql)
            entries.extend([tuple([_spec(info)] + list(row)) for row in cursor])
        _print_result_table(entries, ("Connection", "Type", "Name", "Database"), output)
