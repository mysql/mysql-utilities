import MySQLdb
import re
import sys

KILL_QUERY, KILL_CONNECTION, PRINT_PROCESS = range(3)

ID      = "Id"
USER    = "User"
HOST    = "Host"
DB      = "Db"
COMMAND = "Command"
TIME    = "Time"
STATE   = "State"
INFO    = "Info"

def _spec(info):
    """Create a server specification string from an info structure."""
    result = "{user}:*@{host}:{port}".format(**info)
    if "unix_socket" in info:
        result += ":" + info["unix_socket"]
    return result

def _obj2sql(obj):
    """Convert a Python object to an SQL object.

    This function convert Python objects to SQL values using the
    conversion functions in the database connector package."""
    from MySQLdb.converters import conversions
    return conversions[type(obj)](obj, conversions)

_SELECT_PROC_FRM = """
SELECT
  Id, User, Host, Db, Command, Time, State, Info
FROM
  INFORMATION_SCHEMA.PROCESSLIST{condition}"""

def _make_select(matches, use_regexp):
    """Generate a SELECT statement for matching the processes.
    """
    oper = 'REGEXP' if use_regexp else 'LIKE'
    conditions = []
    for field, pattern in matches:
        conditions.append("    {0} {1} {2}".format(field, oper, _obj2sql(pattern)))
    if len(conditions) > 0:
        condition = "\nWHERE\n" + "\n  AND\n".join(conditions)
    else:
        condition = ""
    return _SELECT_PROC_FRM.format(condition=condition)

_KILL_BODY = """
DECLARE kill_done INT;
DECLARE kill_cursor CURSOR FOR
  {select}
OPEN kill_cursor;
BEGIN
   DECLARE id BIGINT;
   DECLARE EXIT HANDLER FOR NOT FOUND SET kill_done = 1;
   kill_loop: LOOP
      FETCH kill_cursor INTO id;
      KILL {kill} id;
   END LOOP kill_loop;
END;
CLOSE kill_cursor;"""

_KILL_PROCEDURE = """
CREATE PROCEDURE {name} ()
BEGIN{body}
END"""

class ProcessGrep(object):
    def __init__(self, matches, actions=[], use_regexp=False):
        self.__select = _make_select(matches, use_regexp).strip()
        self.__actions = actions

    def sql(self, only_body=False):
        params = {
            'select': "\n      ".join(self.__select.split("\n")),
            'kill': 'CONNECTION' if KILL_CONNECTION in self.__actions else 'QUERY',
            }
        if KILL_CONNECTION in self.__actions or KILL_QUERY in self.__actions:
            sql = _KILL_BODY.format(**params)
            if not only_body:
                sql = _KILL_PROCEDURE.format(name="kill_processes",
                                             body="\n   ".join(sql.split("\n")))
            return sql
        else:
            return self.__select

    def execute(self, *connections, **kwrds):
        from ..common.exception import EmptyResultError
        from ..common.options import parse_connection
        from ..common.format import format_tabular_list

        output = kwrds.get('output', sys.stdout)
        connector = kwrds.get('connector', MySQLdb)

        headers = ("Connection", "Id", "User", "Host", "Db",
                   "Command", "Time", "State", "Info")
        entries = []
        # Build SQL statement
        for info in connections:
            if isinstance(info, basestring):
                info = parse_connection(info)
            connection = connector.connect(**info)
            cursor = connection.cursor()
            cursor.execute(self.__select)
            for row in cursor:
                if KILL_QUERY in self.__actions:
                    cursor.execute("KILL {0}".format(row[0]))
                if KILL_CONNECTION in self.__actions:
                    cursor.execute("KILL {0}".format(row[0]))
                if PRINT_PROCESS in self.__actions:
                    entries.append(tuple([_spec(info)] + list(row)))
        
        # If output is None, nothing is printed
        if len(entries) > 0 and output: 
            format_tabular_list(output, headers, entries)
        elif PRINT_PROCESS in self.__actions:
            raise EmptyResultError("No matches found")

