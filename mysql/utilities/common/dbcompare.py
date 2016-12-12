#
# Copyright (c) 2011, 2016, Oracle and/or its affiliates. All rights reserved.
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
This file contains the methods for checking consistency among two databases.
"""

import re
import tempfile
import difflib

from mysql.utilities.exception import UtilError, UtilDBError
from mysql.utilities.common.format import print_list, get_col_widths
from mysql.utilities.common.pattern_matching import (
    parse_object_name,
    REGEXP_QUALIFIED_OBJ_NAME,
    REGEXP_QUALIFIED_OBJ_NAME_AQ)
from mysql.utilities.common.database import Database
from mysql.utilities.common.lock import Lock
from mysql.utilities.common.options import PARSE_ERR_OBJ_NAME_FORMAT
from mysql.utilities.common.server import connect_servers
from mysql.utilities.common.table import Table
from mysql.utilities.common.sql_transform import (is_quoted_with_backticks,
                                                  quote_with_backticks,
                                                  remove_backtick_quoting,
                                                  transform_data,
                                                  SQLTransformer)


# The following are the queries needed to perform table data consistency
# checking.

_COMPARE_TABLE_NAME = 'compare_{tbl}'

_COMPARE_TABLE_DROP = """
    DROP TABLE {db}.{compare_tbl};
"""

# The Length of key for the span index has been increased from 4 to 8 allow
# more accurate hits. This may slow the algorithm for big dbs, for future
# the key length could be calculated by the number of rows.
DEFAULT_SPAN_KEY_SIZE = 8

# Max allowed size for the span_key. Must be smaller or equal than the size of
# the key hash because it is a substring of it. Note: 32 = binary(16).
MAX_SPAN_KEY_SIZE = 32

# Note: Use a composed index (span, pk_hash) instead of only for column "span"
# due to the "ORDER BY pk_hash" in the _COMPARE_DIFF query.
_COMPARE_TABLE = """
    CREATE TEMPORARY TABLE {db}.{compare_tbl} (
        compare_sign binary(16) NOT NULL,
        pk_hash binary(16) NOT NULL,
        {pkdef}
        span binary({span_key_size}) NOT NULL,
        INDEX span_key (span, pk_hash)) ENGINE=MyISAM
"""

_COMPARE_INSERT = """
    INSERT INTO {db}.{compare_tbl}
        (compare_sign, pk_hash, {pkstr}, span)
    SELECT
        UNHEX(MD5(CONCAT_WS('/', {colstr}))),
        UNHEX(MD5(CONCAT_WS('/', {pkstr}))),
        {pkstr},
        UNHEX(LEFT(MD5(CONCAT_WS('/', {pkstr})), {span_key_size}))
    FROM {db}.{table}
"""

_COMPARE_SUM = """
    SELECT HEX(span), COUNT(*) as cnt,
        CONCAT(SUM(CONV(SUBSTRING(HEX(compare_sign),1,8),16,10)),
        SUM(CONV(SUBSTRING(HEX(compare_sign),9,8),16,10)),
        SUM(CONV(SUBSTRING(HEX(compare_sign),17,8),16,10)),
        SUM(CONV(SUBSTRING(HEX(compare_sign),25,8),16,10))) as sig
    FROM {db}.{compare_tbl}
    GROUP BY span
"""

# ORDER BY is used to ensure determinism for the order in which rows are
# returned between compared tables, otherwise rows might be returned in a
# different for server without the binlog enable (--log-bin option) leading to
# incorrect SQL diff statements (UPDATES).
_COMPARE_DIFF = """
    SELECT * FROM {db}.{compare_tbl}
    WHERE span = UNHEX('{span}') ORDER BY pk_hash
"""

_COMPARE_SPAN_QUERY = """
    SELECT * FROM {db}.{table} WHERE {where}
"""

_ERROR_NO_PRI_KEY = ("The table {tb} does not have an usable Index or "
                     "primary key.")

_WARNING_INDEX_NOT_USABLE = ("# Warning: Specified index {idx} for table {tb}"
                             " cannot be used. It contains at least one "
                             "column that accepts null values.")

_RE_EMPTY_ALTER_TABLE = "^ALTER TABLE {0};$"

_RE_DASHES_DIG = re.compile(r"^\-{3}\s\d+")

_RE_ASTERISK_DIG = re.compile(r"^\*{3}\s\d+")

_RE_ASTERISKS = re.compile(r"^\*{15}.{0,2}$")


def _get_objects(server, database, options):
    """Get all objects from the database (except grants)

    server[in]        connected server object
    database[in]      database names
    options[in]       global options

    Returns list - objects in database
    """
    options["skip_grants"] = True   # Tell db class to skip grants

    db_obj = Database(server, database, options)
    if not db_obj.exists():
        raise UtilDBError("The database does not exist: {0}".format(database))
    db_obj.init()
    db_objects = db_obj.objects
    db_objects.sort()

    return db_objects


def get_create_object(server, object_name, options, object_type):
    """Get the object's create statement.

    This method retrieves the object create statement from the database.

    server[in]        server connection
    object_name[in]   name of object in the form db.objectname
    options[in]       options: verbosity, quiet
    object_type[in]   type of the specified object (e.g, TABLE, PROCEDURE,
                      etc.).

    Returns string : create statement or raise error if object or db not exist
    """

    verbosity = options.get("verbosity", 0)
    quiet = options.get("quiet", False)

    # Get the sql_mode set on server
    sql_mode = server.select_variable("SQL_MODE")

    db_name, obj_name = parse_object_name(object_name, sql_mode)
    obj = [db_name]

    if db_name is None:
        raise UtilError(PARSE_ERR_OBJ_NAME_FORMAT.format(
            obj_name=object_name, option=object_type.lower()))
    db = Database(server, obj[0], options)

    # Error if database does not exist
    if not db.exists():
        raise UtilDBError("The database does not exist: {0}".format(obj[0]))

    if not obj_name or object_type == 'DATABASE':
        obj.append(db_name)
    else:
        obj.append(obj_name)

    create_stmt = db.get_create_statement(obj[0], obj[1], object_type)

    if verbosity > 0 and not quiet:
        if obj_name:
            print("\n# Definition for object {0}.{1}:"
                  "".format(remove_backtick_quoting(db_name, sql_mode),
                            remove_backtick_quoting(obj_name, sql_mode)))
        else:
            print("\n# Definition for object {0}:"
                  "".format(remove_backtick_quoting(db_name, sql_mode)))
        print create_stmt

    return create_stmt


def print_missing_list(item_list, first, second):
    """Print the list of items in the list.

    This method is used to display the list of objects that are missing
    from one of the databases in the compare.

    item_list[in]     list of items to print
    first[in]         name of first database
    second[in]        name of second database

    Returns bool True if items in the list, False if list is empty
    """
    if len(item_list) == 0:
        return False
    print "# WARNING: Objects in {0} but not in {1}:".format(first, second)
    for item in item_list:
        print "# {0:>12}: {1}".format(item[0], item[1][0])
    return True


def server_connect(server1_val, server2_val, object1, object2, options):
    """Connect to the servers

    This method connects to the servers and checks to see if the objects
    are different: db1.obj1 != db2.obj2 by name match.

    server1_val[in]    a dictionary containing connection information for the
                       first server including:
                       (user, password, host, port, socket)
    server2_val[in]    a dictionary containing connection information for the
                       second server including:
                       (user, password, host, port, socket)
    object1[in]        the first object in the compare
    object2[in]        the second object in the compare
    options[in]        a dictionary containing the options for the operation:
                       (quiet, verbosity)

    Returns tuple of Server objects (server1, server2)
    """
    quiet = options.get("quiet", False)
    charset = options.get("charset", None)

    conn_options = {
        'quiet': quiet,
        'src_name': "server1",
        'dest_name': "server2",
        'version': "5.1.30",
        'charset': charset,
    }
    servers = connect_servers(server1_val, server2_val, conn_options)
    server1 = servers[0]
    server2 = servers[1]
    if server2 is None:
        server2 = server1

    # Check if the specified objects and servers are the same.
    if object1 == object2 and server1.port == server2.port and \
       server1.is_alias(server2.host):
        raise UtilError("Comparing the same object on the same server.")

    return (server1, server2)


def get_common_lists(list1, list2):
    """Compare the items in two lists

    This method compares the items in two lists returning those items that
    appear in both lists as well as two lists that contain those unique items
    from the original lists.

    For example, given {s,b,c,d,e,f} and {a,b,c,d,e,z}, the lists returned are
        both = {b,c,d,e}
        in list1 not list2 = {s,f}
        in list2 not list1 = {a.z]

    list1[in]         first list
    list2[in]         second list

    Returns three lists
    """
    s1 = set(list1)
    s2 = set(list2)
    both = s1 & s2
    return(list(both), list(s1 - both), list(s2 - both))


def get_common_objects(server1, server2, db1, db2,
                       print_list=True, options=None):
    """Get a list of the common objects among two databases.

    server1[in]        first server connection
    server2[in]        second server connection
    object1[in]        the first object in the compare in the form: (db.name)
    object2[in]        the second object in the compare in the form: (db.name)
    print_list[in]     if True, print list of missing items
    options[in]        global options

    Returns (tuple) lists containing: items in both,
                                      items in db1 and not in db2,
                                      items in db2 not in db1
    """

    if options is None:
        options = {}
    db1_objects = _get_objects(server1, db1, options)
    db2_objects = _get_objects(server2, db2, options)

    in_both, in_db1_not_db2, in_db2_not_db1 = get_common_lists(db1_objects,
                                                               db2_objects)
    if print_list:
        server1_str = "server1." + db1
        if server1 == server2:
            server2_str = "server1." + db2
        else:
            server2_str = "server2." + db2
        print_missing_list(in_db1_not_db2, server1_str, server2_str)
        print_missing_list(in_db2_not_db1, server2_str, server1_str)

    return (in_both, in_db1_not_db2, in_db2_not_db1)


def _get_diff(list1, list2, object1, object2, difftype, compact=False):
    """Get the difference among two lists.

    This method finds the difference of two lists using either unified,
    context, or differ-style output.

    Note: We must strip not only \n but also trailing blanks due to change in
          Python 2.7.1 handling of difflib methods.

    list1[in]         The base list
    list2[in]         The list used for compare
    object1[in]       The 'from' or source
    object2[in]       The 'to' or difference destination
    difftype[in]      Difference type
    compact[in]       IF True, the resulting diff it will not contain all
                      the control lines, resulting in a fewer lines.

    Returns list - differences or []
    """
    diff_str = []

    # Generate unified is SQL is specified for use in reporting errors
    if difftype in ['unified', 'sql']:
        for line in difflib.unified_diff(list1, list2,
                                         fromfile=object1, tofile=object2):
            if compact:
                if not line.startswith("@@ "):
                    diff_str.append(line.strip('\n').rstrip(' '))
            else:
                diff_str.append(line.strip('\n').rstrip(' '))
    elif difftype == 'context':
        for line in difflib.context_diff(list1, list2,
                                         fromfile=object1, tofile=object2):
            if compact:
                if _RE_DASHES_DIG.match(line):
                    diff_str.append("---")
                elif _RE_ASTERISK_DIG.match(line):
                    diff_str.append("***")
                # Asterisks are used as row separators too
                elif not _RE_ASTERISKS.match(line):
                    diff_str.append(line.strip('\n').rstrip(' '))
            else:
                diff_str.append(line.strip('\n').rstrip(' '))
    else:
        has_diff = False
        for line in difflib.ndiff(list1, list2):
            diff_str.append(line.strip('\n').rstrip(' '))
            if line[0] in ['-', '+', '?']:
                has_diff = True

        if not has_diff:
            diff_str = []

    if compact and difftype != 'differ' and difftype != 'context':
        return diff_str[2:]
    # If objects names are the same, avoid print them
    elif (compact and difftype == 'context' and len(diff_str) > 0 and
          diff_str[0].endswith(diff_str[0][3:])):
        return diff_str[2:]

    return diff_str


def _get_transform(server1, server2, object1, object2, options,
                   object_type):
    """Get the transformation SQL statements

    This method generates the SQL statements to transform the destination
    object based on direction of the compare.

    server1[in]        first server connection
    server2[in]        second server connection
    object1            the first object in the compare in the form: (db.name)
    object2            the second object in the compare in the form: (db.name)
    options[in]        a dictionary containing the options for the operation:
                       (quiet, etc.)
    object_type[in]    type of the objects to be compared (e.g., TABLE,
                       PROCEDURE, etc.).

    Returns tuple - (bool - same db name?, list of transformation statements)
    """

    try:
        db1, name1 = parse_object_name(object1,
                                       server1.select_variable("SQL_MODE"))

        db2, name2 = parse_object_name(object2,
                                       server2.select_variable("SQL_MODE"))
    except:
        raise UtilError("Invalid object name arguments for _get_transform"
                        "(): %s, %s." % (object1, object2))
    # If the second part of the object qualified name is None, then the format
    # is not 'db_name.obj_name' for object1 and therefore must treat it as a
    # database name. (supports backticks and the use of '.' (dots) in names.)
    if not name1 or object_type == 'DATABASE':

        # We are working with databases so db and name need to be set
        # to the database name to tell the get_object_definition() method
        # to retrieve the database information.
        name1 = db1
        name2 = db2

    db_1 = Database(server1, db1, options)
    db_2 = Database(server2, db2, options)

    obj1 = db_1.get_object_definition(db1, name1, object_type)
    obj2 = db_2.get_object_definition(db2, name2, object_type)

    # Get the transformation based on direction.
    transform_str = []
    xform = SQLTransformer(db_1, db_2, obj1[0], obj2[0], object_type,
                           options.get('verbosity', 0), options)

    differences = xform.transform_definition()
    if differences and len(differences) > 0:
        transform_str.extend(differences)

    return transform_str


def _check_tables_structure(server1, server2, object1, object2, options,
                            diff_type):
    """Check if the tables have the same structure.

    This method compares the tables structure ignoring the order of the
    columns and retrieves the differences between the table options.

    server1[in]        first server connection.
    server2[in]        second server connection.
    object1            the first object in the compare in the form: (db.name).
    object2            the second object in the compare in the form: (db.name).
    options[in]        a dictionary containing the options for the operation:
                       (quiet, verbosity, difftype, width, suppress_sql).
    diff_type[in]      difference type.

    Returns a tuple (bool, list, bool) - The first tuple value is a boolean
    that indicates if both tables have the same structure (i.e. column
    definitions). The second returns the table options differences. Finally,
    the third is a boolean indicating if the partition options are the same.
    """
    try:
        db1, name1 = parse_object_name(object1,
                                       server1.select_variable("SQL_MODE"))

        db2, name2 = parse_object_name(object2,
                                       server2.select_variable("SQL_MODE"))
    except:
        raise UtilError("Invalid object name arguments for diff_objects(): "
                        "{0}, {1}.".format(object1, object2))

    compact_diff = options.get("compact", False)

    # If the second part of the object qualified name is None, then the format
    # is not 'db_name.obj_name' for object1 and therefore must treat it as a
    # database name.
    if not name1:
        return None, None, None

    db_1 = Database(server1, db1, options)
    db_2 = Database(server2, db2, options)

    # Get tables definitions.
    table_1 = db_1.get_object_definition(db1, name1, 'TABLE')[0]
    table_2 = db_2.get_object_definition(db2, name2, 'TABLE')[0]

    # Check table options.
    table1_opts = db_1.get_table_options(db1, name1)
    table2_opts = db_2.get_table_options(db2, name2)
    diff = _get_diff(table1_opts, table2_opts, object1, object2, diff_type,
                     compact=compact_diff)

    # Check if both tables have the same columns definition.
    # Discard column order.
    table_1_cols = [col[1:] for col in table_1[1]]
    table_2_cols = [col[1:] for col in table_2[1]]
    same_cols_def = set(table_1_cols) == set(table_2_cols)

    # Check if both tables have the same partition options.
    # Discard partition name.
    table_1_part = [part[1:] for part in table_1[2]]
    table_2_part = [part[1:] for part in table_2[2]]
    same_partition_opts = set(table_1_part) == set(table_2_part)

    # Return tables check results.
    return same_cols_def, diff, same_partition_opts


def build_diff_list(diff1, diff2, transform1, transform2,
                    first, second, options):
    """Build the list of differences

    This method builds a list of difference statements based on whether
    the lists are the result of an SQL statement generation, object definition
    differences, or data differences.

    Note: to specify a non-SQL difference for data, set
          options['data_diff'] = True

    diff1[in]              definition diff for first server
    diff2[in]              definition diff for second server
    transform1[in]         transformation for first server
    transform2[in]         transformation for second server
    first[in]              name of first server (e.g. server1)
    second[in]             name of second server (e.g. server2)
    options[in]            options for building the list

    Returns list = list of differences or transformations
    """
    # Don't build the list if there were no differences.
    if len(diff1) == 0:
        return []

    reverse = options.get('reverse', False)
    diff_list = []
    if options.get('difftype') == 'sql':
        if len(transform1) == 0:
            diff_list.append("\n# WARNING: Cannot generate SQL statements "
                             "for these objects.")
            diff_list.append("# Check the difference output for other "
                             "discrepencies.")
            diff_list.extend(diff1)
        else:
            diff_list.append("# Transformation for --changes-for=%s:\n#\n" %
                             first)
            diff_list.extend(transform1)
            diff_list.append("")
            if reverse and len(transform2) > 0:
                diff_list.append("#\n# Transformation for reverse changes "
                                 "(--changes-for=%s):\n#" % second)
                for row in transform2:
                    sub_rows = row.split('\n')
                    for sub_row in sub_rows:
                        diff_list.append("# %s" % sub_row)
                diff_list.append("#\n")
    else:
        # Don't print messages for a data difference (non-SQL)
        if not options.get('data_diff', False):
            diff_list.append("# Object definitions differ. "
                             "(--changes-for=%s)\n#\n" % first)
        diff_list.extend(diff1)
        if reverse and len(diff2) > 0:
            diff_list.append("")
            if not options.get('data_diff', False):
                diff_list.append("#\n# Definition diff for reverse changes "
                                 "(--changes-for=%s):\n#" % second)
            for row in diff2:
                diff_list.append("# %s" % row)
            diff_list.append("#\n")

    return diff_list


def diff_objects(server1, server2, object1, object2, options, object_type):
    """diff the definition (CREATE statement) of two objects

    Produce a diff in the form unified, context, or ndiff of two objects.
    Note: objects must exist else exception is thrown.

    With the transform option, the method will generate the transformation
    SQL statements in addition to the differences found in the CREATE
    statements.

    When the --difftype == 'sql', the method will print the sql statements
    to stdout. To suppress this, use options: quiet=True, suppress_sql=True.

    server1[in]        first server connection
    server2[in]        second server connection
    object1[in]        the first object in the compare in the form: (db.name)
    object2[in]        the second object in the compare in the form: (db.name)
    options[in]        a dictionary containing the options for the operation:
                       (quiet, verbosity, difftype, width, suppress_sql)
    object_type[in]    type of the objects to be compared (e.g., TABLE,
                       PROCEDURE, etc.).

    Returns None = objects are the same, diff[] = objects differ
    """
    quiet = options.get("quiet", False)
    difftype = options.get("difftype", "unified")
    width = options.get("width", 75)
    direction = options.get("changes-for", None)
    reverse = options.get("reverse", False)
    skip_table_opts = options.get("skip_table_opts", False)
    compact_diff = options.get("compact", False)

    # Get object CREATE statement.
    # Note: Table options are discarded if option skip_table_opts=True.
    object1_create = get_create_object(server1, object1, options, object_type)
    object2_create = get_create_object(server2, object2, options, object_type)

    # Only target CREATE DATABASE difference if decorations differ,
    # not just the database names. So we isolate the CREATE statement
    # without the names or +/- and compare. If different, print the
    # difference report otherwise, ignore it.
    if (object_type == "DATABASE") and (object1 != object2):
        quotes = ["'", '"', "`"]
        db1 = object1.translate(None, "".join(quotes))
        db2 = object2.translate(None, "".join(quotes))
        first = object1_create.replace(db1, "")[1::]
        second = object2_create.replace(db2, "")[1::]
        if first == second:
            object1_create = ""
            object2_create = ""

    if not quiet:
        msg = "# Comparing {0} to {1} ".format(object1, object2)
        print msg,
        linelen = width - (len(msg) + 10)
        print ' ' * linelen,

    object1_create_list = object1_create.split('\n')
    object2_create_list = object2_create.split('\n')

    diff_server1 = []
    diff_server2 = []
    transform_server1 = []
    transform_server2 = []

    # Get the difference based on direction.
    if direction == 'server1' or direction is None or reverse:
        diff_server1 = _get_diff(object1_create_list,
                                 object2_create_list,
                                 object1, object2, difftype,
                                 compact=compact_diff)
        # If there is a difference. Check for SQL output
        if difftype == 'sql' and len(diff_server1) > 0:
            transform_server1 = _get_transform(server1, server2,
                                               object1, object2, options,
                                               object_type)

    if direction == 'server2' or reverse:
        diff_server2 = _get_diff(object2_create_list,
                                 object1_create_list,
                                 object2, object1, difftype,
                                 compact=compact_diff)
        # If there is a difference. Check for SQL output
        if difftype == 'sql' and len(diff_server2) > 0:
            transform_server2 = _get_transform(server2, server1,
                                               object2, object1, options,
                                               object_type)

    # Build diff list
    if direction == 'server1' or direction is None:
        diff_list = build_diff_list(diff_server1, diff_server2,
                                    transform_server1, transform_server2,
                                    'server1', 'server2', options)
    else:
        diff_list = build_diff_list(diff_server2, diff_server1,
                                    transform_server2, transform_server1,
                                    'server2', 'server1', options)

    # Note: table structure check ignores columns order.
    same_tbl_def = None
    tbl_opts_diff = None
    same_part_def = None
    if object_type == 'TABLE':
        same_tbl_def, tbl_opts_diff, same_part_def = _check_tables_structure(
            server1, server2, object1, object2, options, difftype
        )

    # Check if ALTER TABLE statement have changes. If not, it is probably
    # because there are differences but they have no influence on the create
    # table, such as different order on indexes.
    if "ANSI_QUOTES" in server1.select_variable("SQL_MODE"):
        regex_pattern = REGEXP_QUALIFIED_OBJ_NAME_AQ
    else:
        regex_pattern = _RE_EMPTY_ALTER_TABLE.format(REGEXP_QUALIFIED_OBJ_NAME)
    if diff_list and same_tbl_def and same_part_def and \
       re.match(regex_pattern, diff_list[1]):
        print("[PASS]")
        return None

    if diff_list and direction is None and same_tbl_def and not tbl_opts_diff:
        if not quiet:
            print("[PASS]")
            print("# WARNING: The tables structure is the same, but the "
                  "columns order is different. Use --change-for to take the "
                  "order into account.")
        return None

    # Check for failure to generate SQL statements
    if (difftype == 'sql') and \
       ((direction == 'server1' and transform_server1 == [] and
         diff_server1 != []) or
        (direction == 'server2' and transform_server2 == [] and
         diff_server2 != [])):

        # Here we found no transformations. So either the change is nothing
        # more than the database name or we missed something. Send a
        # warning to the user.

        if not quiet:
            print "[FAIL]"

        for line in diff_list:
            print line

        print("# WARNING: Could not generate SQL statements for differences "
              "between {0} and {1}. No changes required or not supported "
              "difference.".format(object1, object2))

        return diff_list

    if len(diff_list) > 0:
        if not quiet:
            print "[FAIL]"

        if not quiet or \
           (not options.get("suppress_sql", False) and difftype == 'sql'):
            for line in diff_list:
                print line

            # Full ALTER TABLE for partition difference cannot be generated
            # (not supported). Notify the user.
            if same_part_def is False:
                print("# WARNING: Partition changes were not generated "
                      "(not supported).")

        return diff_list

    if not quiet:
        print("[PASS]")
        if skip_table_opts and tbl_opts_diff:
            print("# WARNING: Table options are ignored and differences were "
                  "found:")
            for diff in tbl_opts_diff:
                print("# {0}".format(diff))

    return None


def _drop_compare_object(server, db_name, tbl_name):
    """Drop the compare object table

    server[in]             Server instance
    db_name[in]            database name
    tbl_name[in]           table name
    """
    # Quote compare table appropriately with backticks
    sql_mode = server.select_variable("SQL_MODE")
    q_db_name = db_name if is_quoted_with_backticks(db_name, sql_mode) \
        else quote_with_backticks(db_name, sql_mode)
    if is_quoted_with_backticks(tbl_name, sql_mode):
        q_tbl_name = remove_backtick_quoting(tbl_name, sql_mode)
    else:
        q_tbl_name = tbl_name
    q_tbl_name = quote_with_backticks(
        _COMPARE_TABLE_NAME.format(tbl=q_tbl_name), sql_mode)

    try:
        # set autocommit=1 if it is 0, because CREATE TEMPORARY TABLE and
        # DROP TEMPORARY TABLE can be executed in a non-transactional context
        # only, and require that AUTOCOMMIT = 1.
        toggle_server = not server.autocommit_set()
        if toggle_server:
            server.toggle_autocommit(enable=True)
        server.exec_query(_COMPARE_TABLE_DROP.format(db=q_db_name,
                                                     compare_tbl=q_tbl_name))
        if toggle_server:
            server.toggle_autocommit(enable=False)
    except:
        pass


def _get_compare_objects(index_cols, table1,
                         span_key_size=DEFAULT_SPAN_KEY_SIZE):
    """Build the compare table and identify the primary index

    This method creates the compare table for use in forming the MD5 hash
    of rows and a hash of the primary key. It also forms the primary key
    list of columns.

    index_cols[in]    a list of columns that form the primary key in the form
                      (column_name, type)
    table1[in]        a Table instance of the original table

    span_key_size[in] the size of key used for the hash.

    Returns tuple (table create statement, concatenated string of the
                   primary index columns)
    """
    table = None

    # build primary key col definition
    index_str = ''.join("{0}, ".format(quote_with_backticks(col[0],
                                                            table1.sql_mode))
                        for col in index_cols)
    index_defn = ''.join("{0} {1}, ".
                         format(quote_with_backticks(col[0], table1.sql_mode),
                                col[1])
                         for col in index_cols)
    if index_defn == "":
        raise UtilError("Cannot generate index definition")
    else:
        # Quote compare table appropriately with backticks
        q_tbl_name = quote_with_backticks(
            _COMPARE_TABLE_NAME.format(tbl=table1.tbl_name), table1.sql_mode)

        table = _COMPARE_TABLE.format(db=table1.q_db_name,
                                      compare_tbl=q_tbl_name,
                                      pkdef=index_defn,
                                      span_key_size=span_key_size / 2)

    return (table, index_str)


def _setup_compare(table1, table2, span_key_size, use_indexes=None):
    """Create and populate the compare summary tables

    This method creates the condensed hash table used to compare groups
    (span) of records. It also creates the Table instance for each table
    and populates values in the table information dictionary for use
    in other methods.

    The method also checks to ensure the tables have primary keys and that
    the keys are the same (have the same columns). An error is raised if
    neither of these are met.

    table1[in]            table1 Table instance
    table2[in]            table2 Table instance
    span_key_size[in]     the size of key used for the hash.
    use_indexes[in]       a tuple of the indexes names that can be used as
                          an unique key, (for_table_1, for_table_2), they will
                          be tested for columns that not accept null.
    diag_msgs[out]       a list of debug and warning messages.

    Returns four-tuple - string representations of the primary index columns,
    the index_columns, the index name used and diagnostic messages.
    """

    def get_column_names_types_for_index(index, table):
        """Useful method to get the columns name and type used by an index
        """
        tb_columns = table.get_col_names_types()
        table_idx = [col_row for column in index.columns
                     for col_row in tb_columns if column[0] == col_row[0]]
        return table_idx

    def find_candidate_indexes(candidate_idexes, no_null_idxes_tb,
                               table_name, diag_msgs):
        """This method search the user's candidate indexes in the given list
        of unique indexes with no null columns. Table name is user to
        create the warning message if the candidate index has a column that
        accepts null values.
        """
        indexs_found = []
        for cte_index in candidate_idexes:
            for no_null_idx in no_null_idxes_tb:
                if no_null_idx.q_name == cte_index:
                    indexs_found.append((no_null_idx.q_name, no_null_idx))
                    break
            else:
                diag_msgs.append(
                    _WARNING_INDEX_NOT_USABLE.format(
                        idx=cte_index, tb=table_name)
                )
        return indexs_found

    diag_msgs = []
    server1 = table1.server
    server2 = table2.server

    # get not nullable indexes for tables
    table1.get_indexes()
    table2.get_indexes()
    no_null_idxes_tb1 = table1.get_not_null_unique_indexes()
    no_null_idxes_tb2 = table2.get_not_null_unique_indexes()

    # if table does not have non nullable unique keys, do not continue.
    if not no_null_idxes_tb1 or not no_null_idxes_tb2:
        raise UtilError(_ERROR_NO_PRI_KEY.format(tb=table1.tbl_name))

    table1_idx = []
    table2_idx = []
    # If user specified indexes with --use-indexes
    if use_indexes:
        # pylint: disable=W0633
        candidate_idxs_tb1, candidate_idxs_tb2 = use_indexes
        # Check if indexes exist,
        for cte_idx in candidate_idxs_tb1:
            if not table1.has_index(cte_idx):
                raise UtilError("The specified index {0} was not found in "
                                "table {1}".format(cte_idx, table1.table))
        for cte_idx in candidate_idxs_tb2:
            if not table2.has_index(cte_idx):
                raise UtilError("The specified index {0} was not found in "
                                "table {1}".format(cte_idx, table2.table))

        # Find the user index specified with --use-indexes
        unique_indexes_tb1 = find_candidate_indexes(
            candidate_idxs_tb1, no_null_idxes_tb1, table1.table, diag_msgs)

        unique_indexes_tb2 = find_candidate_indexes(
            candidate_idxs_tb2, no_null_idxes_tb2, table1.table, diag_msgs)

        if unique_indexes_tb1:
            table1_idx_name = unique_indexes_tb1[0][0]
            table1_idx = get_column_names_types_for_index(
                unique_indexes_tb1[0][1],
                table1
            )
        if unique_indexes_tb2:
            table2_idx = get_column_names_types_for_index(
                unique_indexes_tb2[0][1],
                table2
            )

    # If no user defined index or accepts nulls, use first unique not nullable
    if not table1_idx:
        table1_idx_name = no_null_idxes_tb1[0].name
        table1_idx = get_column_names_types_for_index(no_null_idxes_tb1[0],
                                                      table1)
    if not table2_idx:
        table2_idx = get_column_names_types_for_index(no_null_idxes_tb2[0],
                                                      table2)

    if len(table1_idx) != len(table2_idx):
        raise UtilError("Indexes are not the same.")

    # drop the temporary tables
    _drop_compare_object(server1, table1.db_name, table1.tbl_name)
    _drop_compare_object(server2, table2.db_name, table2.tbl_name)

    # Build the primary key hash if needed
    tbl1_table, pri_idx1 = _get_compare_objects(table1_idx, table1,
                                                span_key_size)
    tbl2_table, pri_idx2 = _get_compare_objects(table2_idx, table2,
                                                span_key_size)

    if tbl1_table is None or tbl2_table is None:
        raise UtilError("Cannot create compare table.")

    # Create the compare tables

    # set autocommit=1 if it is 0, because CREATE TEMPORARY TABLE and DROP
    # TEMPORARY TABLE can be executed in a non-transactional context only, and
    # require that AUTOCOMMIT = 1.

    # Check if server1 and server2 have autocommit=0, and if so set the flag
    #  to 1 and execute the create temporary table query.
    must_toggle_s1 = not server1.autocommit_set()
    if must_toggle_s1:
        server1.toggle_autocommit(enable=True)
    server1.exec_query(tbl1_table)

    must_toggle_s2 = not server2.autocommit_set()
    if must_toggle_s2:
        server2.toggle_autocommit(enable=True)
    server2.exec_query(tbl2_table)

    # if the autocommit flag was toggled, return it to its previous value.
    if must_toggle_s1:
        server1.toggle_autocommit(enable=False)
    if must_toggle_s2:
        server2.toggle_autocommit(enable=False)

    return (pri_idx1, pri_idx2, table1_idx, table1_idx_name, diag_msgs)


def _make_sum_rows(table, idx_str, span_key_size=8):
    """Populate the summary table

    This method inserts rows into the compare table from the original table
    then forms the summary table by combining a prefix of the primary key
    hash (group by).

    table[in]         Table instance
    idx_str[in]       string representation of primary key columns

    Returns result from
    """
    col_str = ", ".join(table.get_col_names(True))

    # Lock table first
    tbl_lock_list = [
        (table.table, 'READ'),
        ("%s.compare_%s" % (table.db_name, table.tbl_name), 'WRITE')
    ]
    my_lock = Lock(table.server, tbl_lock_list)

    # Quote compare table appropriately with backticks
    q_tbl_name = quote_with_backticks(
        _COMPARE_TABLE_NAME.format(tbl=table.tbl_name),
        table.sql_mode
    )

    table.server.exec_query(
        _COMPARE_INSERT.format(db=table.q_db_name, compare_tbl=q_tbl_name,
                               colstr=col_str.strip(", "),
                               pkstr=idx_str.strip(", "),
                               table=table.q_tbl_name,
                               span_key_size=span_key_size))

    res = table.server.exec_query(
        _COMPARE_SUM.format(db=table.q_db_name, compare_tbl=q_tbl_name))

    # Unlock table
    my_lock.unlock()

    return res


def _get_rows_span(table, span, index):
    """Get the rows corresponding to a list of span values

    This method returns the rows from the original table that match the
    span value presented.

    TODO: This may need refactoring to make it more efficient.
          For example, use a WHERE clause such as:
          WHERE some_col IN ('a','b')

    table[in]         Table instance
    span[in]          span value

    Returns rows from original table
    """
    server = table.server
    rows = []
    ukeys = [col[0] for col in index]
    # build WHERE clause
    for row in span:
        # Quote compare table appropriately with backticks
        q_tbl_name = quote_with_backticks(
            _COMPARE_TABLE_NAME.format(tbl=table.tbl_name),
            table.sql_mode
        )

        span_rows = server.exec_query(
            _COMPARE_DIFF.format(db=table.q_db_name, compare_tbl=q_tbl_name,
                                 span=row))
        # Loop through multiple rows with the same span value.
        for res_row in span_rows:
            pk = res_row[2:-1]
            where_clause = ' AND '.join("{0} = '{1}'".
                                        format(key, col)
                                        for key, col in zip(ukeys, pk))
            orig_rows = server.exec_query(
                _COMPARE_SPAN_QUERY.format(db=table.q_db_name,
                                           table=table.q_tbl_name,
                                           where=where_clause))
            rows.append(orig_rows[0])

    return rows


def _get_changed_rows_span(table1, table2, span, index):
    """Get the original changed rows corresponding to a list of span values.

    This method returns the changed rows from the original tables that match
    the given list of span keys. Several rows might be associated to each span,
    including unchanged, changed, missing or extra rows. This method takes all
    these situations into account, ignoring unchanged rows and separating
    changed rows from missing/extra rows for each table when retrieving the
    original data. This separation is required in order to generate the
    appropriate SQL diff statement (UPDATE, INSERT, DELETE) later.

    table1[in]      First table instance.
    table2[in]      Second table instance.
    span[in]        List of span keys.
    index[in]       Used table index (unique key).

    Returns the changed rows from original tables, i.e., a tuple with two
    elements containing the changes for each table. At its turn, the element
    for each table is another tuple where the first element contains the list
    of changed rows and the second the list of extra rows (compared to the
    other table).
    """
    # Get all span rows for table 1.
    server1 = table1.server
    full_span_data_1 = []
    for row in span:
        # Quote compare table appropriately with backticks
        q_tbl_name = quote_with_backticks(
            _COMPARE_TABLE_NAME.format(tbl=table1.tbl_name),
            table1.sql_mode
        )

        span_rows = server1.exec_query(
            _COMPARE_DIFF.format(db=table1.q_db_name, compare_tbl=q_tbl_name,
                                 span=row))
        # Auxiliary set with (compare_sign, pk_hash) tuples for table.
        cmp_signs = set([(row[0], row[1]) for row in span_rows])
        # Keep span rows and auxiliary data for table 1.
        full_span_data_1.append((span_rows, cmp_signs))

    # Get all span rows for table 2.
    server2 = table2.server
    full_span_data_2 = []
    for row in span:
        # Quote compare table appropriately with backticks
        q_tbl_name = quote_with_backticks(
            _COMPARE_TABLE_NAME.format(tbl=table2.tbl_name),
            table2.sql_mode
        )

        span_rows = server2.exec_query(
            _COMPARE_DIFF.format(db=table2.q_db_name, compare_tbl=q_tbl_name,
                                 span=row))
        # Auxiliary set with (compare_sign, pk_hash) tuples for table.
        cmp_signs = set([(row[0], row[1]) for row in span_rows])
        # Keep span rows and auxiliary data for table 1.
        full_span_data_2.append((span_rows, cmp_signs))

    # List of key columns
    ukeys = [col[0] for col in index]

    # Get the original diff rows for tables 1 and 2.
    changed_in1 = []
    extra_in1 = []
    changed_in2 = []
    extra_in2 = []
    for pos, span_data1 in enumerate(full_span_data_1):
        # Also get span data for table 2.
        # Note: specific span data is at the same position for both tables.
        span_data2 = full_span_data_2[pos]

        # Determine different rows for tables 1 and 2 (exclude unchanged rows).
        diff_rows_sign1 = span_data1[1] - span_data2[1]
        diff_rows_sign2 = span_data2[1] - span_data1[1]
        diff_pk_hash1 = set(cmp_sign[1] for cmp_sign in diff_rows_sign1)
        diff_pk_hash2 = set(cmp_sign[1] for cmp_sign in diff_rows_sign2)

        # Get the original diff rows for tables 1.
        for res_row in span_data1[0]:
            # Skip row if not in previously identified changed rows set.
            if (res_row[0], res_row[1]) in diff_rows_sign1:
                # Execute query to get the original row.
                pk = res_row[2:-1]
                where_clause = ' AND '.join("{0} = '{1}'".
                                            format(key, col)
                                            for key, col in zip(ukeys, pk))
                res = server1.exec_query(
                    _COMPARE_SPAN_QUERY.format(db=table1.q_db_name,
                                               table=table1.q_tbl_name,
                                               where=where_clause))

                # Determine if it is a changed or extra row.
                # Check if the same pk_hash is found in table 2.
                if res_row[1] in diff_pk_hash2:
                    # Store original changed row (to UPDATE).
                    changed_in1.append(res[0])
                else:
                    # Store original extra row (to DELETE).
                    extra_in1.append(res[0])

        # Get the original diff rows for table 2.
        for res_row in span_data2[0]:
            # Skip row if not in previously identified changed rows set.
            if (res_row[0], res_row[1]) in diff_rows_sign2:
                # Execute query to get the original row.
                pk = res_row[2:-1]
                where_clause = ' AND '.join("{0} = '{1}'".
                                            format(key, col)
                                            for key, col in zip(ukeys, pk))
                res = server2.exec_query(
                    _COMPARE_SPAN_QUERY.format(db=table2.q_db_name,
                                               table=table2.q_tbl_name,
                                               where=where_clause))

                # Determine if it is a changed or extra row.
                # Check if the same pk_hash is found in table 1.
                if res_row[1] in diff_pk_hash1:
                    # Store original changed row (to UPDATE).
                    changed_in2.append(res[0])
                else:
                    # Store original extra row (to ADD).
                    extra_in2.append(res[0])

    # Return a tuple with a tuple for each table, containing the changed and
    # extra original row for each table.
    return (changed_in1, extra_in1), (changed_in2, extra_in2)


def _get_formatted_rows(rows, table, fmt='GRID', col_widths=None):
    """Get a printable representation of the data rows

    This method generates a formatted view of the rows from a table. The output
    format can be in one of GRID, CSV, TAB, or VERTICAL. This output is
    returned as a list of strings for use in storing the output for later
    presentation.

    rows[in]          missing rows
    table[in]         a Table instance of the table
    obj1_str[in]      full table name for base table
    obj2_str[in]      full table name for other table
    fmt[in]           format to print
    col_widths[in]    column widths to use instead of actual col

    Returns list of formatted rows
    """
    result_rows = []
    if not col_widths:
        col_widths = []
    outfile = tempfile.TemporaryFile()
    to_sql = False
    if fmt.upper() == 'CSV':
        to_sql = True
    print_list(outfile, fmt, table.get_col_names(), rows, to_sql=to_sql,
               col_widths=col_widths)
    outfile.seek(0)
    for line in outfile.readlines():
        result_rows.append(line.strip('\n'))

    return result_rows


def _generate_data_diff_output(diff_data, table1, table2, used_index, options):
    """Generates the data difference output.

    This function generates the output data for the found data differences
    between two tables, according to the provided options (difftype and
    format).

    diff_data[in]   Tuple with three elements containing the data differences
                    between two tables. The first element contains the rows on
                    both tables but with different values, the second contains
                    the rows found in table1 but not in table2, and the third
                    contains the rows found in table2 but not in table1.
    table1[in]      First compared table (source).
    table2[in]      Second compared table (target).
    used_index[in]  Index (key) used to identify rows.
    options[in]     Dictionary of option (format, difftype, compact, etc.).

    Return a list of difference (strings) generated according to the
    specified options.
    """
    difftype = options.get('difftype', 'unified')
    fmt = options.get('format', 'grid')
    compact_diff = options.get("compact", False)
    table1_name = table1.q_table
    table2_name = table2.q_table
    changed_rows, extra1, extra2 = diff_data
    data_diffs = []

    def get_max_cols(tbl1_rows, tbl2_rows):
        """Get maximum columns for each set of rows

        Find maximum column widths for each column for a pair of tables.

        tbl1_rows[in]  first table rows
        tbl2_rows[in]  second table rows

        Return a list of the columns and the max width for each
        """
        # We need to turn the list of tuples to list of lists
        row_list = []
        for r in tbl1_rows:
            for i in r:
                row_list.append(list(i))
        t1_cols = get_col_widths(table1.get_col_names(), row_list)
        row_list = []
        for r in tbl2_rows:
            for i in r:
                row_list.append(list(i))
        t2_cols = get_col_widths(table2.get_col_names(), row_list)

        # Get max of each
        max_cols = []
        for i in range(0, len(t1_cols)):
            if t1_cols[i] > t2_cols[i]:
                max_cols.append(t1_cols[i])
            elif t1_cols[i] <= t2_cols[i]:
                max_cols.append(t2_cols[i])
        return max_cols

    if len(changed_rows) > 0:
        data_diffs.append("# Data differences found among rows:")
        # Get original changed/extra rows for each table within the given
        # span set 'changed_rows' (excluding unchanged rows).
        # Note: each span can refer to multiple rows.
        tbl1_rows, tbl2_rows = _get_changed_rows_span(table1, table2,
                                                      changed_rows,
                                                      used_index)

        if difftype == 'sql':
            # Compute SQL diff for changed rows.
            data_diffs.extend(transform_data(table1, table2, "UPDATE",
                                             (tbl1_rows[0], tbl2_rows[0])))
            # Compute SQL diff for extra rows in table 1.
            if tbl1_rows[1]:
                data_diffs.extend(transform_data(table1, table2,
                                                 "DELETE", tbl1_rows[1]))
            # Compute SQL diff for extra rows in table 2.
            if tbl2_rows[1]:
                data_diffs.extend(transform_data(table1, table2,
                                                 "INSERT", tbl2_rows[1]))
        else:
            # Ok, to make the comparison more uniform, we need to get the
            # max column widths for each table and use the higher of the
            # two to format the rows in the output.
            max_cols = get_max_cols(tbl1_rows, tbl2_rows)

            # Join changed and extra rows for table 1.
            tbl1_rows = tbl1_rows[0] + tbl1_rows[1]
            rows1 = _get_formatted_rows(tbl1_rows, table1, fmt, max_cols)
            # Join changed and extra rows for table 2.
            tbl2_rows = tbl2_rows[0] + tbl2_rows[1]
            rows2 = _get_formatted_rows(tbl2_rows, table2, fmt, max_cols)
            # Compute diff for all changes between table 1 and 2.
            diff_str = _get_diff(rows1, rows2, table1_name, table2_name,
                                 difftype, compact=compact_diff)
            if len(diff_str) > 0:
                data_diffs.extend(diff_str)

    if len(extra1) > 0:
        # Compute diff for extra rows in table 1.
        rows = _get_rows_span(table1, extra1, used_index)
        if difftype == 'sql':
            data_diffs.extend(transform_data(table1, table2,
                                             "DELETE", rows))
        else:
            data_diffs.append("\n# Rows in {0} not in {1}"
                              "".format(table1_name, table2_name))
            res = _get_formatted_rows(rows, table1, fmt)
            data_diffs.extend(res)

    if len(extra2) > 0:
        # Compute diff for extra rows in table 2.
        rows = _get_rows_span(table2, extra2, used_index)
        if difftype == 'sql':
            data_diffs.extend(transform_data(table1, table2,
                                             "INSERT", rows))
        else:
            data_diffs.append("\n# Rows in {0} not in {1}"
                              "".format(table2_name, table1_name))
            res = _get_formatted_rows(rows, table2, fmt)
            data_diffs.extend(res)

    return data_diffs


def check_consistency(server1, server2, table1_name, table2_name,
                      options=None, diag_msgs=None, reporter=None):
    """Check the data consistency of two tables

    This method performs a comparison of the data in two tables.

    Algorithm:

    This procedure uses a separate temporary compare table that
    contains an MD5 hash of the concatenated values of a row along with a
    MD5 hash of the concatenation of the primary key, the primary key columns,
    and a grouping column named span. By default, before executing this
    procedure the result of CHECKSUM TABLE is compared (which is faster when
    no differences are expected). The remaining algorithm to find row
    differences is only executed if this checksum table test fails or if it is
    skipped by the user.

    The process to calculate differences in table data is as follows:

    0. Compare the result of CHECKSUM TABLE for both tables. If the checksums
       match None is returned and the algorithm ends, otherwise the next steps
       to find row differences are executed.

       Note: The following steps are only executed if the table checksums are
             different or if this preliminary step is skipped by the user.

    1. If binary log on for the client (sql_log_bin = 1), turn it off.

    2. Create the temporary compare table for each table to compare
       (db1.table1, db2.table2)

    3. For each table, populate the compare table using an INSERT statement
       that calculates the MD5 hash for the row.

    4. For each table, a summary result is formed by summing the MD5 hash
       values broken into four parts. The MD5 hash is converted to decimal for
       a numerical sum. This summary query also groups the rows in the compare
       table by the span column which is formed from the first 4 positions of
       the primary key hash.

    5. The summary tables are compared using set methods to find rows (spans)
       that appear in both tables, those only in table1, and those only in
       table2. A set operation that does not match the rows means the summed
       hash is different therefore meaning one or more rows in the span have
       either a missing row in the other table or the data is different. If no
       differences found, skip to (9).

    6. The span values from the sets that contain rows that are different are
       then compared again using set operations. Those spans that are in both
       sets contain rows that have changed while the set of rows in one but not
       the other (and vice-versa) contain rows that are missing.

       Note: it is possible given sufficient density of the table for the
             changed rows span to contain missing rows. This is Ok because the
             output of the difference will still present the data as missing.

    7. The output of (6) that contain the same spans (changed rows) is then
       used to form a difference and this is saved for presentation to the
       user.

    8. The output of (7) that contain missing spans (missing rows) is then
       used to form a formatted list of the results for presentation to the
       user.

       Note: The differences output is generated considering the specified
       changes directions (for server1, server2, or both).

    9. The compare databases are destroyed and differences (if any) are
       returned according to the specified change direction in the options.
       A return value of (None, None) indicates the data is consistent.

    10. Turn binary logging on if turned off in step (1).

    Exceptions:

    server1[in]       first server Server instance
    server2[in]       second server Server instance
    table1_name[in]   name of first table in form 'db.name'
    table2_name[in]   name of second table in form 'db.name'
    options[in]       dictionary of options for the operation containing
                        'format'    : format for output of missing rows
                        'difftype'  : type of difference to show
                        'unique_key': column name for pseudo-key
    diag_msgs[out]    a list of diagnostic and warning messages.
    reporter[in]      Instance of the database compare reporter class.

    Returns tuple - string representations of the primary index columns

    Returns a tuple with the list of differences for server1 and/or server2
            according to the specified direction. If the data is consistent
            then the tuple (None, None) is returned.
    """
    if options is None:
        options = {}
    span_key_size = options.get('span_key_size', DEFAULT_SPAN_KEY_SIZE)
    use_indexes = options.get('use_indexes', None)
    direction = options.get('changes-for', 'server1')
    reverse = options.get('reverse', False)

    table1 = Table(server1, table1_name)
    table2 = Table(server2, table2_name)

    # First, check full table checksum if step is not skipped.
    if reporter:
        reporter.report_object("", "- Compare table checksum")
        reporter.report_state("")
        reporter.report_state("")
    if not options['no_checksum_table']:
        checksum1, err1 = server1.checksum_table(table1.q_table)
        checksum2, err2 = server2.checksum_table(table2.q_table)
        if err1 or err2:
            err_data = (server1.host, server1.port, err1) if err1 \
                else (server2.host, server2.port, err2)
            raise UtilError("Error executing CHECKSUM TABLE on '{0}@{1}': "
                            "{2}".format(*err_data))
        if checksum1 == checksum2:
            if reporter:
                reporter.report_state("pass")
            return None, None  # No data diffs (in any direction)
        else:
            if reporter:
                reporter.report_state("FAIL")
    else:
        if reporter:
            reporter.report_state("SKIP")

    # remove quotations to indexes
    unq_use_indexes = []
    if use_indexes:
        for tbl, index in use_indexes:
            unq_use_indexes.append((
                remove_backtick_quoting(tbl, table1.sql_mode),
                remove_backtick_quoting(index, table1.sql_mode)
            ))
            if table1.sql_mode != table2.sql_mode:
                unq_use_indexes.append((
                    remove_backtick_quoting(tbl, table2.sql_mode),
                    remove_backtick_quoting(index, table2.sql_mode)
                ))

    # if given get the unique_key for table_name
    table1_use_indexes = []
    if use_indexes:
        table1_use_indexes.extend(
            [quote_with_backticks(u_key, table1.sql_mode) for tb_name, u_key
             in unq_use_indexes if table1.tbl_name == tb_name]
        )
    table2_use_indexes = []
    if use_indexes:
        table2_use_indexes.extend(
            [quote_with_backticks(u_key, table2.sql_mode) for tb_name, u_key
             in unq_use_indexes if table2.tbl_name == tb_name]
        )

    if options.get('toggle_binlog', 'False'):
        binlog_server1 = server1.binlog_enabled()
        if binlog_server1:
            # Commit to avoid error setting sql_log_bin inside a transaction.
            server1.rollback()
            server1.toggle_binlog("DISABLE")
        binlog_server2 = server2.binlog_enabled()
        if binlog_server2:
            # Commit to avoid error setting sql_log_bin inside a transaction.
            server2.commit()
            server2.toggle_binlog("DISABLE")
    else:  # set to false to skip after actions to turn binlog back on
        binlog_server1 = False
        binlog_server2 = False

    data_diffs1 = None
    data_diffs2 = None

    # Now, execute algorithm to find row differences.
    if reporter:
        reporter.report_object("", "- Find row differences")
        reporter.report_state("")
        reporter.report_state("")
    # Setup the comparative tables and calculate the hashes
    pri_idx_str1, pri_idx_str2, used_index, used_index_name, msgs = (
        _setup_compare(table1, table2,
                       span_key_size,
                       use_indexes=(table1_use_indexes, table2_use_indexes))
    )

    # Add warnings to print them later.
    if diag_msgs is not None and isinstance(diag_msgs, list):
        diag_msgs.extend(msgs)
        diag_msgs.append("# INFO: for table {0} the index {1} is used to "
                         "compare.".format(table1.tbl_name, used_index_name))

    # Populate the compare tables and retrieve rows from each table
    tbl1_hash = _make_sum_rows(table1, pri_idx_str1, span_key_size)
    tbl2_hash = _make_sum_rows(table2, pri_idx_str2, span_key_size)

    # Compare results (between spans).
    _, in1_not2, in2_not1 = get_common_lists(tbl1_hash, tbl2_hash)

    # If mismatch found, go back to compare table and retrieve grouping.
    if len(in1_not2) != 0 or len(in2_not1) != 0:
        table1_diffs = []
        table2_diffs = []

        # Get keys for diffs on table1
        for row in in1_not2:
            table1_diffs.append(row[0])

        # Get keys for diffs on table2
        for row in in2_not1:
            table2_diffs.append(row[0])

        # Find changed and missing rows
        changed_rows, extra1, extra2 = get_common_lists(table1_diffs,
                                                        table2_diffs)

        # Generate data differences output according to direction.
        if direction == 'server1' or reverse:
            data_diffs1 = _generate_data_diff_output(
                (changed_rows, extra1, extra2), table1, table2, used_index,
                options
            )
        if direction == 'server2' or reverse:
            data_diffs2 = _generate_data_diff_output(
                (changed_rows, extra2, extra1), table2, table1, used_index,
                options
            )

    if binlog_server1:
        # Commit to avoid error setting sql_log_bin inside a transaction.
        server1.commit()
        server1.toggle_binlog("ENABLE")
    if binlog_server2:
        # Commit to avoid error setting sql_log_bin inside a transaction.
        server2.commit()
        server2.toggle_binlog("ENABLE")

    if reporter:
        if data_diffs1 or data_diffs2:
            reporter.report_state('FAIL')
        else:
            reporter.report_state('pass')
    return data_diffs1, data_diffs2
