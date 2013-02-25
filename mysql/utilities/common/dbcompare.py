#
# Copyright (c) 2011, 2013 Oracle and/or its affiliates. All rights reserved.
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
from mysql.utilities.common.sql_transform import is_quoted_with_backticks
from mysql.utilities.common.sql_transform import quote_with_backticks
from mysql.utilities.common.sql_transform import remove_backtick_quoting

"""
This file contains the methods for checking consistency among two databases.
"""

from mysql.utilities.exception import UtilError, UtilDBError

# The following are the queries needed to perform table data consistency
# checking.

_COMPARE_TABLE_NAME = 'compare_{tbl}'

_COMPARE_TABLE_DROP = """
    DROP TABLE {db}.{compare_tbl};
"""

_COMPARE_TABLE = """
    CREATE TEMPORARY TABLE {db}.{compare_tbl} (
        compare_sign char(32) NOT NULL PRIMARY KEY,
        pk_hash char(32) NOT NULL,
        {pkdef}
        span char(4) NOT NULL,
        KEY span_key (pk_hash(4)));
"""

_COMPARE_INSERT = """
    INSERT INTO {db}.{compare_tbl}
        (compare_sign, pk_hash, {pkstr}, span)
    SELECT
        MD5(CONCAT_WS('/', {colstr})),
        MD5(CONCAT_WS('/', {pkstr})),
        {pkstr},
        LEFT(MD5(CONCAT_WS('/', {pkstr})), 4)
    FROM {db}.{table}
"""

_COMPARE_SUM = """
    SELECT span, COUNT(*) as cnt, 
        CONCAT(SUM(CONV(SUBSTRING(compare_sign,1,8),16,10)),
        SUM(CONV(SUBSTRING(compare_sign,9,8),16,10)),
        SUM(CONV(SUBSTRING(compare_sign,17,8),16,10)),
        SUM(CONV(SUBSTRING(compare_sign,25,8),16,10))) as sig
    FROM {db}.{compare_tbl}
    GROUP BY span
"""

_COMPARE_DIFF = """
    SELECT * FROM {db}.{compare_tbl}
    WHERE span = '{span}'
"""

_COMPARE_SPAN_QUERY = """
    SELECT * FROM {db}.{table} WHERE {where}
"""

def _get_objects(server, database, options):
    """Get all objects from the database (except grants)
    
    server[in]        connected server object
    database[in]      database names
    options[in]       global options
    
    Returns list - objects in database
    """
    from mysql.utilities.common.database import Database

    options["skip_grants"] = True   # Tell db class to skip grants

    db_obj = Database(server, database, options)
    if not db_obj.exists():
        raise UtilDBError("The database does not exist: {0}".format(database))
    db_obj.init()
    db_objects = db_obj.objects
    db_objects.sort()

    return db_objects


def get_create_object(server, object_name, options):
    """Get the object's create statement.
    
    This method retrieves the object create statement from the database.
    
    server[in]        server connection
    object_name[in]   name of object in the form db.objectname
    options[in]       options: verbosity, quiet
    
    Returns string : create statement or raise error if object or db not exist
    """
    from mysql.utilities.common.database import Database

    verbosity = options.get("verbosity", 0)
    quiet = options.get("quiet", False)

    db_name, sep, obj_name = object_name.partition(".")
    object = [db_name]

    db = Database(server, object[0], options)

    # Error if atabase does not exist
    if not db.exists():
        raise UtilDBError("The database does not exist: {0}".format(object[0]))

    if not obj_name:
        object.append(object[0])
        obj_type = "DATABASE"
    else:
        object.append(obj_name)
        obj_type = db.get_object_type(object[1])
        if obj_type is None:
            raise UtilDBError("The object {0} does not exist.".
                              format(object_name))
    create_stmt = db.get_create_statement(object[0], object[1], obj_type)
        
    if verbosity > 0 and not quiet:
        print "\n# Definition for object {0}:".format(object_name)
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
    from mysql.utilities.common.server import connect_servers

    quiet = options.get("quiet", False)
    verbosity = options.get("verbosity", 0)

    conn_options = {
        'quiet'     : quiet,
        'src_name'  : "server1",
        'dest_name' : "server2",
        'version'   : "5.1.30",
    }
    servers = connect_servers(server1_val, server2_val, conn_options)
    server1 = servers[0]
    server2 = servers[1]
    if server2 is None:
        server2 = server1
 
    if server1 == server2 and object1 == object2:
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
    return(list(both), list(s1-both), list(s2-both))


def get_common_objects(server1, server2, db1, db2,
                       print_list=True, options={}):
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


def _get_diff(list1, list2, object1, object2, difftype):
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
    
    Returns list - differences or []
    """
    import difflib
    
    diff_str = []
    # Generate unified is SQL is specified for use in reporting errors
    if difftype in ['unified', 'sql']:
        for line in difflib.unified_diff(list1, list2,
                                         fromfile=object1, tofile=object2):
            diff_str.append(line.strip('\n').rstrip(' '))
    elif difftype == 'context':
        for line in difflib.context_diff(list1, list2,
                                         fromfile=object1, tofile=object2):
            diff_str.append(line.strip('\n').rstrip(' '))
    else:
        has_diff = False
        for line in difflib.ndiff(list1, list2):
            diff_str.append(line.strip('\n').rstrip(' '))
            if line[0] in ['-', '+', '?']:
                has_diff = True
                
        if not has_diff:
            diff_str = []
    
    return diff_str


def _get_transform(server1, server2, object1, object2, options):
    """Get the transformation SQL statements
    
    This method generates the SQL statements to transform the destination
    object based on direction of the compare.
    
    server1[in]        first server connection
    server2[in]        second server connection
    object1            the first object in the compare in the form: (db.name)
    object2            the second object in the compare in the form: (db.name)
    options[in]        a dictionary containing the options for the operation:
                       (quiet, etc.)

    Returns tuple - (bool - same db name?, list of transformation statements)
    """
    from mysql.utilities.common.database import Database
    from mysql.utilities.common.sql_transform import SQLTransformer

    obj_type = None
    direction = options.get("changes-for", "server1")

    # If there is no dot, we do not have the format 'db_name.obj_name' for
    # object1 and therefore must treat it as a database name.
    if object1.find('.') == -1:
        obj_type = "DATABASE"
        
        # We are working with databases so db and name need to be set
        # to the database name to tell the get_object_definition() method
        # to retrieve the database information.
        db1 = object1
        db2 = object2
        name1 = object1
        name2 = object2
    else:
        try:
            db1, name1 = object1.split('.')
            db2, name2 = object2.split('.')
        except:
            raise UtilError("Invalid object name arguments for _get_transform"
                            "(): %s, %s." % (object1, object2))
            
    db_1 = Database(server1, db1, options)
    db_2 = Database(server2, db2, options)
    
    if obj_type is None:
        obj_type = db_1.get_object_type(name1)

    transform_str = []
    obj1 = db_1.get_object_definition(db1, name1, obj_type)
    obj2 = db_2.get_object_definition(db2, name2, obj_type)
    
    # Get the transformation based on direction.
    transform_str = []
    same_db_name = True
    xform = SQLTransformer(db_1, db_2, obj1[0], obj2[0], obj_type,
                           options.get('verbosity', 0))

    differences = xform.transform_definition()
    if differences is not None and len(differences) > 0:
        transform_str.extend(differences)

    return transform_str


def build_diff_list(diff1, diff2, transform1, transform2,
                     first, second, options):
    """Build the list of differences
    
    This method builds a list of difference statements based on whether
    the lists are the result of an SQL statement generation, object definition
    differences, or data differences.
    
    Note: to specify a non-SQL difference for data, set
          options['data_diff'] = True
    
    diff1[in]              definitiion diff for first server
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


def diff_objects(server1, server2, object1, object2, options):
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
    object1            the first object in the compare in the form: (db.name)
    object2            the second object in the compare in the form: (db.name)
    options[in]        a dictionary containing the options for the operation:
                       (quiet, verbosity, difftype, width, suppress_sql)

    Returns None = objects are the same, diff[] = objects differ
    """
    import sys
    
    quiet = options.get("quiet", False)
    verbosity = options.get("verbosity", 0)
    difftype = options.get("difftype", "unified")
    width = options.get("width", 75)
    direction = options.get("changes-for", "server1")
    reverse = options.get("reverse", False)

    object1_create = get_create_object(server1, object1, options)
    object2_create = get_create_object(server2, object2, options)
    
    if not quiet:
        msg = "# Comparing {0} to {1} ".format(object1, object2)
        print msg,
        linelen = width - (len(msg) + 10)
        print ' ' * linelen,

    object1_create_list = object1_create.split('\n')
    object2_create_list = object2_create.split('\n')

    diff_list = []    
    diff_server1 = []
    diff_server2 = []
    transform_server1 = []
    transform_server2 = []

    # Get the difference based on direction.
    if direction == 'server1' or reverse:
        diff_server1 = _get_diff(object1_create_list,
                                 object2_create_list,
                                 object1, object2, difftype)
        # If there is a difference. Check for SQL output
        if difftype == 'sql' and len(diff_server1) > 0:
            transform_server1 = _get_transform(server1, server2,
                                               object1, object2, options)

    if direction == 'server2' or reverse:
        diff_server2 = _get_diff(object2_create_list,
                                 object1_create_list,
                                 object2, object1, difftype)
        # If there is a difference. Check for SQL output
        if difftype == 'sql' and len(diff_server2) > 0:
            transform_server2 = _get_transform(server2, server1,
                                               object2, object1, options)


    # Build diff list
    if direction == 'server1':
        diff_list = build_diff_list(diff_server1, diff_server2,
                                    transform_server1, transform_server2,
                                    'server1', 'server2', options)
    else:
        diff_list = build_diff_list(diff_server2, diff_server1,
                                    transform_server2, transform_server1,
                                    'server2', 'server1', options)
    
    # Check for failure to generate SQL statements
    if (difftype == 'sql') and \
       ((direction == 'server1' and transform_server1 == [] \
         and diff_server1 != []) or \
        (direction == 'server2' and transform_server2 == [] \
         and diff_server2 != [])):

        # Here we found no transformations. So either the change is nothing
        # more than the database name or we missed something. Send a
        # warning to the user.

        if not quiet:
            print "[FAIL]"

        for line in diff_list:
            print line
        
        return diff_list

    if len(diff_list) > 0:
        if not quiet:
            print "[FAIL]"
            
        if not quiet or \
           (not options.get("suppress_sql", False) and difftype == 'sql'):
            for line in diff_list:
                print line

        return diff_list
    
    if not quiet:
        print "[PASS]"

    return None


def _drop_compare_object(server, db_name, tbl_name):
    """Drop the compare object table
    
    server[in]             Server instance
    db_name[in]            database name
    tbl_name[in]           table name
    """
    # Quote compare table appropriately with backticks
    q_db_name = db_name if is_quoted_with_backticks(db_name) \
                        else quote_with_backticks(db_name)
    if is_quoted_with_backticks(tbl_name):
        q_tbl_name = remove_backtick_quoting(tbl_name)
    else:
        q_tbl_name = tbl_name
    q_tbl_name = quote_with_backticks(
                                _COMPARE_TABLE_NAME.format(tbl=q_tbl_name))

    try:
        server.exec_query(_COMPARE_TABLE_DROP.format(db=q_db_name,
                                                     compare_tbl=q_tbl_name))
    except:
        pass


def _get_compare_objects(index_cols, table1):
    """Build the compare table and identify the primary index
    
    This method creates the compare table for use in forming the MD5 hash
    of rows and a hash of the primary key. It also forms the primary key
    list of columns.
    
    index_cols[in]    a list of columns that form the primary key in the form
                      (column_name, type)
    table1[in]        a Table instance of the original table
    
    Returns tuple (table create statement, concatenated string of the
                   primary index columns)
    """
    table = None

    # build primary key col definition
    index_str = ''.join("{0}, ".format(quote_with_backticks(col[0])) \
                        for col in index_cols)
    index_defn = ''.join("{0} {1}, ".
                         format(quote_with_backticks(col[0]), col[1]) \
                         for col in index_cols)
    if index_defn == "":
        raise UtilError("Cannot generate index definition")
    else:
        # Quote compare table appropriately with backticks
        q_tbl_name = quote_with_backticks(
                            _COMPARE_TABLE_NAME.format(tbl=table1.tbl_name))

        table = _COMPARE_TABLE.format(db=table1.q_db_name,
                                      compare_tbl=q_tbl_name, pkdef=index_defn)

    return (table, index_str)


def _setup_compare(table1, table2):
    """Create and populate the compare summary tables
    
    This method creates the condensed hash table used to compare groups
    (span) of records. It also creates the Table instance for each table
    and populates values in the table information dictionary for use
    in other methods.
    
    The method also checks to ensure the tables have primary keys and that
    the keys are the same (have the same columns). An error is raised if
    neither of these are met.
    
    table1[in]        table1 Table instance
    table2[in]        table2 Table instance

    Returns tuple - string representations of the primary index columns
    """
    server1 = table1.server
    server2 = table2.server

    # Get the primary key for the tables and make sure they are the same
    table1_idx = table1.get_primary_index()

    table2_idx = table2.get_primary_index()
    if len(table1_idx) != len(table2_idx):
        raise UtilError("Indexes are not the same.")
    elif table1_idx == [] or table2_idx == []:
        raise UtilError("No primary key found.")

    # drop the temporary tables
    _drop_compare_object(server1, table1.db_name, table1.tbl_name)
    _drop_compare_object(server2, table2.db_name, table2.tbl_name)

    # Build the primary key hash if needed
    tbl1_table, pri_idx1 = _get_compare_objects(table1_idx, table1)
    tbl2_table, pri_idx2 = _get_compare_objects(table1_idx, table2)
    
    if tbl1_table is None or tbl2_table is None:
        raise UtilError("Cannot create compare table.")

    # Create the compare tables
    server1.exec_query(tbl1_table)
    server2.exec_query(tbl2_table)

    return (pri_idx1, pri_idx2)


def _make_sum_rows(table, idx_str):
    """Populate the summary table
    
    This method inserts rows into the compare table from the original table
    then forms the summary table by combining a prefix of the primary key
    hash (group by).
    
    table[in]         Table instance
    idx_str[in]       string representation of primary key columns
    
    Returns result from 
    """
    from mysql.utilities.common.lock import Lock

    col_str = ", ".join(table.get_col_names(True))
        
    # Lock table first
    tbl_lock_list = [
        (table.table, 'READ'),
        ("%s.compare_%s" % (table.db_name, table.tbl_name), 'WRITE')
    ]
    my_lock = Lock(table.server, tbl_lock_list)

    # Quote compare table appropriately with backticks
    q_tbl_name = quote_with_backticks(
                            _COMPARE_TABLE_NAME.format(tbl=table.tbl_name))

    table.server.exec_query(
        _COMPARE_INSERT.format(db=table.q_db_name, compare_tbl=q_tbl_name,
                               colstr=col_str.strip(", "),
                               pkstr=idx_str.strip(", "),
                               table=table.q_tbl_name))

    res = table.server.exec_query(
        _COMPARE_SUM.format(db=table.q_db_name, compare_tbl=q_tbl_name))

    # Unlock table
    my_lock.unlock()

    return res


def _get_rows_span(table, span):
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
    # build WHERE clause
    for row in span:
        # Quote compare table appropriately with backticks
        q_tbl_name = quote_with_backticks(
                            _COMPARE_TABLE_NAME.format(tbl=table.tbl_name))

        res1 = server.exec_query(
            _COMPARE_DIFF.format(db=table.q_db_name, compare_tbl=q_tbl_name,
                                 span=row))
        pk = res1[0][2:len(res1[0])-1]
        pkeys = [col[0] for col in table.get_primary_index()]
        where_clause = ' AND '.join("{0} = '{1}'".
                                    format(key, col)
                                    for key, col in zip(pkeys, pk))
        res2 = server.exec_query(
            _COMPARE_SPAN_QUERY.format(db=table.q_db_name,
                                       table=table.q_tbl_name,
                                       where=where_clause))
        rows.append(res2[0])
        
    return rows


def _get_formatted_rows(rows, table, format='GRID'):
    """Get a printable representation of the data rows
    
    This method generates a formatted view of the rows from a table. The output
    format can be in one of GRID, CSV, TAB, or VERTICAL. This output is
    returned as a list of strings for use in storing the output for later
    presentation.
    
    rows[in]          missing rows
    table[in]         a Table instance of the table
    obj1_str[in]      full table name for base table
    obj2_str[in]      full table name for other table
    format[in]        format to print
    
    Returns list of formatted rows
    """
    import os
    import tempfile
    from mysql.utilities.common.format import print_list

    result_rows = []
    outfile = tempfile.TemporaryFile()
    print_list(outfile, format, table.get_col_names(), rows)
    outfile.seek(0)
    for line in outfile.readlines():
        result_rows.append(line.strip('\n'))
    
    return result_rows


def check_consistency(server1, server2, table1_name, table2_name, options={}):
    """Check the data consistency of two tables
    
    This method performs a comparison of the data in two tables.
    
    Algorithm:
    
    This procedure uses a separate compare database containing a table that
    contains an MD5 hash of the concatenated values of a row along with a
    MD5 hash of the concatenation of the primary key, the primary key columns,
    and a grouping column named span.
    
    The process to calculate differences in table data is as follows:
    
    0. If binary log on for the client (sql_log_bin = 1), turn it off.
    
    1. Create the compare database and the compare table for each
       database (db1.table1, db2.table2)

    2. For each table, populate the compare table using an INSERT statement
       that calculates the MD5 hash for the row. 

    3. For each table, a summary result is formed by summing the MD5 hash
       values broken into four parts. The MD5 hash is converted to decimal for
       a numerical sum. This summary query also groups the rows in the compare
       table by the span column which is formed from the first 4 positions of
       the primary key hash.
    
    4. The summary tables are compared using set methods to find rows (spans)
       that appear in both tables, those only in table1, and those only in
       table2. A set operation that does not match the rows means the summed
       hash is different therefore meaning one or more rows in the span have
       either a missing row in the other table or the data is different. If no
       differences found, skip to (8).
       
    5. The span values from the sets that contain rows that are different are
       then compared again using set operations. Those spans that are in both
       sets contain rows that have changed while the set of rows in one but not
       the other (and vice-versa) contain rows that are missing.
       
       Note: it is possible given sufficient density of the table for the
             changed rows span to contain missing rows. This is Ok because the
             output of the difference will still present the data as missing.
             
    6. The output of (5) that contain the same spans (changed rows) is then
       used to form a difference and this is saved for presentation to the
       user.
       
    7. The output of (6) that contain missing spans (missing rows) is then
       used to form a formatted list of the results for presentation to the
       user.
       
    8. The compare databases are destroyed and differences (if any) are
       returned. A return value of None indicates the data is consistent.
       
    9. Turn binary logging on if turned off in step (0).
    
    Exceptions:
    
    server1[in]       first server Server instance
    server2[in]       second server Server instance
    table1_name[in]   name of first table in form 'db.name'
    table2_name[in]   name of second table in form 'db.name'
    options[in]       dictionary of options for the operation containing
                        'format'    : format for output of missing rows
                        'difftype'  : type of difference to show
                        
    Returns None = data is consistent
            list of differences - data is not consistent
    """
    from mysql.utilities.common.sql_transform import transform_data
    from mysql.utilities.common.table import Table
        
    format = options.get('format', 'GRID')
    difftype = options.get('difftype', 'unified')
    
    if options.get('toggle_binlog', 'False'):
        binlog_server1 = server1.binlog_enabled()
        if binlog_server1:
            server1.toggle_binlog("DISABLE")
        binlog_server2 = server2.binlog_enabled()
        if binlog_server2:
            server2.toggle_binlog("DISABLE")
    else:  # set to false to skip after actions to turn binlog back on
        binlog_server1 = False
        binlog_server2 = False
    
    data_diffs = None
    
    table1 = Table(server1, table1_name)
    table2 = Table(server2, table2_name)

    # Setup the comparative tables and calculate the hashes
    pri_idx_str1, pri_idx_str2 = _setup_compare(table1, table2)
    
    # Populate the compare tables and retrieve rows from each table
    tbl1_hash = _make_sum_rows(table1, pri_idx_str1)
    tbl2_hash = _make_sum_rows(table2, pri_idx_str2)

    # Compare results
    in_both, in1_not2, in2_not1 = get_common_lists(tbl1_hash, tbl2_hash)
    
    # If mismatch found, go back to compare table and retrieve grouping.
    if len(in1_not2) != 0 or len(in2_not1) != 0:
        table1_diffs = []
        table2_diffs = []
        data_diffs = []
        
        # Get keys for diffs on table1
        for row in in1_not2:
            table1_diffs.append(row[0])
            
        # Get keys for diffs on table2
        for row in in2_not1:
            table2_diffs.append(row[0])
            
        # Find changed and missing rows
        changed_rows, extra1, extra2 = get_common_lists(table1_diffs,
                                                        table2_diffs)
        
        if len(changed_rows) > 0:
            data_diffs.append("# Data differences found among rows:")
            tbl1_rows = _get_rows_span(table1, changed_rows)
            tbl2_rows = _get_rows_span(table2, changed_rows)
            if difftype == 'sql':
                data_diffs.extend(transform_data(table1, table2, "UPDATE",
                                                 (tbl1_rows, tbl2_rows)))
            else:
                rows1 = _get_formatted_rows(tbl1_rows, table1, format)
                rows2 = _get_formatted_rows(tbl2_rows, table2, format)            
                diff_str = _get_diff(rows1, rows2, table1_name, table2_name,
                                     difftype)
                if len(diff_str) > 0:
                    data_diffs.extend(diff_str)
        
        if len(extra1) > 0:
            rows = _get_rows_span(table1, extra1)
            if difftype == 'sql':
                data_diffs.extend(transform_data(table1, table2,
                                                 "DELETE", rows))
            else:
                data_diffs.append("\n# Rows in {0} not in {1}".format(table1_name,
                                                                table2_name))
                res = _get_formatted_rows(rows, table1, format)
                data_diffs.extend(res)
            

        if len(extra2) > 0:
            rows = _get_rows_span(table2, extra2)
            if difftype == 'sql':
                data_diffs.extend(transform_data(table1, table2,
                                                 "INSERT", rows))
            else:
                data_diffs.append("\n# Rows in {0} not in {1}".format(table2_name,
                                                                    table1_name))
                res = _get_formatted_rows(rows, table2, format)
                data_diffs.extend(res)
            
    if binlog_server1:
        server1.toggle_binlog("ENABLE")
    if binlog_server2:
        server2.toggle_binlog("ENABLE")

    return data_diffs

    
