#
# Copyright (c) 2010, 2016, Oracle and/or its affiliates. All rights reserved.
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
This file contains the import operations that will import object metadata or
table data.
"""

import csv
import re
import sys

from collections import defaultdict

from mysql.utilities.exception import UtilError, UtilDBError
from mysql.utilities.common.database import Database
from mysql.utilities.common.options import check_engine_options
from mysql.utilities.common.pattern_matching import parse_object_name
from mysql.utilities.common.table import Table
from mysql.utilities.common.server import connect_servers
from mysql.utilities.common.sql_transform import (quote_with_backticks,
                                                  is_quoted_with_backticks,
                                                  to_sql)


# List of database objects for enumeration
_DATA_DECORATE = "DATA FOR TABLE"
_DATABASE, _TABLE, _VIEW, _TRIG, _PROC, _FUNC, _EVENT, _GRANT = "DATABASE", \
    "TABLE", "VIEW", "TRIGGER", "PROCEDURE", "FUNCTION", "EVENT", "GRANT"
_IMPORT_LIST = [_TABLE, _VIEW, _TRIG, _PROC, _FUNC, _EVENT,
                _GRANT, _DATA_DECORATE]
_DEFINITION_LIST = [_TABLE, _VIEW, _TRIG, _PROC, _FUNC, _EVENT, _GRANT]
_BASIC_COMMANDS = ["CREATE", "USE", "GRANT", "DROP", "SET"]
_DATA_COMMANDS = ["INSERT", "UPDATE"]
_RPL_COMMANDS = ["START", "STOP", "CHANGE"]
_RPL_PREFIX = "-- "
_RPL = len(_RPL_PREFIX)
_SQL_LOG_BIN_CMD = "SET @@SESSION.SQL_LOG_"
_GTID_COMMANDS = ["SET @MYSQLUTILS_TEMP_L", _SQL_LOG_BIN_CMD,
                  "SET @@GLOBAL.GTID_PURG"]
_GTID_PREFIX = 22
_GTID_SKIP_WARNING = ("# WARNING: GTID commands are present in the import "
                      "file but the server does not support GTIDs. Commands "
                      "are ignored.")
_GTID_MISSING_WARNING = ("# WARNING: GTIDs are enabled on this server but the "
                         "import file did not contain any GTID commands.")


def _read_row(file_h, fmt, skip_comments=False):
    """Read a row of from the file.

    This method reads the file attempting to read and translate the data
    based on the format specified.

    file_h[in]        Opened file handle
    fmt[in]           One of SQL,CSV,TAB,GRID,or VERTICAL
    skip_comments[in] If True, do not return lines starting with '#'

    Returns (tuple) - one row of data
    """

    warnings_found = []
    if fmt == "sql":
        # Easiest - just read a row and return it.
        for row in file_h.readlines():
            if row.startswith("# WARNING"):
                warnings_found.append(row)
                continue
            if not (row.startswith('#') or row.startswith('--')):
                # Handle multi-line statements (do not strip).
                # Note: delimiters have to be handled outside this function.
                if len(row.strip()) == 0:
                    yield ''  # empty row
                else:
                    yield row  # do not strip (can be multi-line)
    elif fmt == "vertical":
        # This format is a bit trickier. We need to read a set of rows that
        # encompass the data row. They will appear in this format:
        #   ****** <header> ******
        #      col_a: value_a
        #      col_b: value_b
        #   ...
        #   <next header>
        # Thus, we must read until the next header then return a tuple
        # containing all of the values from the right. We also need to
        # return an initial row with the column names on the left.
        write_header = False
        read_header = False
        header = []
        data_row = []
        for row in file_h.readlines():
            # Show warnings from file
            if row.startswith("# WARNING"):
                warnings_found.append(row)
                continue
            # Process replication commands
            if row[0:_RPL] == _RPL_PREFIX:
                # find first word
                first_word = row[_RPL:row.find(' ', _RPL)].upper()
                if first_word in _RPL_COMMANDS:
                    yield [row.strip('\n')]
                    continue
                # Check for GTID commands
                elif len(row) > _GTID_PREFIX + _RPL and \
                        row[_RPL:_GTID_PREFIX + _RPL] in _GTID_COMMANDS:
                    yield [row.strip('\n')]
                    continue
            # Skip comment rows
            if row[0] == '#':
                if len(header) > 0:
                    yield header
                    header = []
                if len(data_row) > 0:
                    yield data_row
                    data_row = []
                if skip_comments:
                    continue
                else:
                    new_row = [row]
                    yield new_row
                    continue
            # If we find a header, and we've already read data, return the
            # row else this is the first header so we ignore it.
            if row[0] == '*':
                if row.find(" 1. row") > 0:
                    read_header = True
                    continue
                else:
                    write_header = True
                    read_header = False
                if write_header:
                    write_header = False
                    if len(header) > 0:
                        yield header
                        header = []
                if len(data_row) > 0:
                    yield data_row
                data_row = []
                continue
            # Now, split the data into column header and column data
            # Saving column header for first row
            field = row.split(":")
            if len(field) == 2:
                if read_header:
                    header.append(field[0].strip())
                # strip \n from lines
                data_row.append(field[1][0:len(field[1]) - 1].strip())
            elif len(field) == 4:  # date field!
                if read_header:
                    header.append(field[0].strip())
                date_str = "%s:%s:%s" % (field[1], field[2],
                                         field[3].strip())
                data_row.append(date_str)
        if len(data_row) > 0:
            yield data_row
    else:
        separator = ","
        # Use CSV reader to read the row
        if fmt == "csv":
            separator = ","
        elif fmt == "tab":
            separator = "\t"
        elif fmt == "grid":
            separator = "|"
        csv_reader = csv.reader(file_h, delimiter=separator)
        for row in csv_reader:
            # Ignore empty lines
            if not row:
                continue
            if row[0].startswith("# WARNING"):
                warnings_found.append(row[0])
                continue
            # find first word
            if row[0][0:_RPL] == _RPL_PREFIX:
                first_word = \
                    row[0][_RPL:_RPL + row[0][_RPL:].find(' ')].upper()
            else:
                first_word = ""
            # Process replication commands
            if row[0][0:_RPL] == _RPL_PREFIX:
                if first_word in _RPL_COMMANDS:
                    yield row
                # Check for GTID commands
                elif len(row[0]) > _GTID_PREFIX + _RPL and \
                        row[0][_RPL:_GTID_PREFIX + _RPL] in _GTID_COMMANDS:
                    yield row

            elif fmt == "grid":
                if len(row[0]) > 0:
                    if row[0][0] == '+':
                        continue
                    elif (row[0][0] == '#' or row[0][0:2] == "--") and \
                            not skip_comments:
                        yield row
                else:
                    new_row = []
                    for col in row[1:len(row) - 1]:
                        new_row.append(col.strip())
                    yield new_row
            else:
                if (len(row[0]) == 0 or row[0][0] != '#' or
                        row[0][0:2] != "--") or ((row[0][0] == '#' or
                                                  row[0][0:2] == "--") and
                                                 not skip_comments):
                    yield row

    if warnings_found:
        print("CAUTION: The following warning messages were included in "
              "the import file:")
        for row in warnings_found:
            print(row.strip('\n'))


def _check_for_object_list(row, obj_type):
    """Check to see if object is in the list of valid objects.

    row[in]           A row containing an object
    obj_type[in]      Object type to find

    Returns (bool) - True = object is obj_type
                     False = object is not obj_type
    """
    if row[0:len(obj_type) + 2].upper() == "# %s" % obj_type:
        return row.find("none found") < 0
    else:
        return False


def read_next(file_h, fmt):
    """Read properly formatted import file and return the statements.

    This method reads the next object from the file returning a tuple
    containing the type of object - either a definition, SQL statement,
    or the beginning of data rows and the actual data from the file.

    It uses the _read_row() method to read the file returning either
    a list of SQL commands (i.e. from a --format=SQL file) or a list
    of the data from the file (_read_row() converts all non-SQL formatted
    files into lists). This allows the caller to request an object block
    at a time from the file without knowing the format of the file.

    file_h[in]        Opened file handle
    fmt[in]           One of SQL,CSV,TAB,GRID,or VERTICAL

    Returns (tuple) - ('SQL'|'DATA'|'BEGIN_DATA'|'<object>', <data read>)
    """
    cmd_type = ""
    multiline = False
    delimiter = ';'
    skip_next_line = False
    first_occurrence = True
    previous_cmd_type = None
    if fmt == "sql":
        sql_cmd = ""
        for row in _read_row(file_h, "sql", True):
            first_word = row[0:row.find(' ')].upper()  # find first word
            stripped_row = row.strip()  # Avoid repeating strip() operation.
            # Skip these nonsense rows.
            if len(row) == 0 or row[0] == "#"or row[0:2] == "||":
                continue
            # Handle DELIMITER
            elif stripped_row.upper().startswith('DELIMITER'):
                if len(sql_cmd) > 0:
                    # Yield previous SQL command.
                    yield (cmd_type, sql_cmd)
                sql_cmd = ''  # Reset SQL command (i.e. remove DELIMITER).
                # Get delimiter from statement "DELIMITER <delimiter>".
                delimiter = stripped_row[10:]
                cmd_type = "sql"
                # Enable/disable multi-line according to the found delimiter.
                # pylint: disable=R0102
                if delimiter != ';':
                    multiline = True
                else:
                    multiline = False
            elif multiline and stripped_row.endswith(delimiter):
                # Append last line to previous multi-line SQL and retrieve it,
                # removing trailing whitespaces and delimiter.
                sql_cmd = "{0}{1}".format(sql_cmd,
                                          row.rstrip()[0:-len(delimiter)])
                yield (cmd_type, sql_cmd)
                sql_cmd = ''
            elif multiline:  # Save multiple line statements.
                sql_cmd = "{0}{1}".format(sql_cmd, row)
            # Identify specific statements (command types).
            elif (len(row) > _GTID_PREFIX and
                  row[0:_GTID_PREFIX] in _GTID_COMMANDS):
                # Remove trailing whitespaces and delimiter.
                sql_cmd = sql_cmd.rstrip()[0:-len(delimiter)]
                if len(sql_cmd) > 0:
                    # Yield previous SQL command.
                    yield (cmd_type, sql_cmd)
                cmd_type = "GTID_COMMAND"
                sql_cmd = row
            elif first_word in _BASIC_COMMANDS:
                # Remove trailing whitespaces and delimiter.
                sql_cmd = sql_cmd.rstrip()[0:-len(delimiter)]
                if len(sql_cmd) > 0:
                    # Yield previous sql command.
                    yield (cmd_type, sql_cmd)
                cmd_type = "sql"
                sql_cmd = row
            elif first_word in _RPL_COMMANDS:
                # Remove trailing whitespaces and delimiter.
                sql_cmd = sql_cmd.rstrip()[0:-len(delimiter)]
                if len(sql_cmd) > 0:
                    # Yield previous SQL command.
                    yield (cmd_type, sql_cmd)
                cmd_type = "RPL_COMMAND"
                sql_cmd = row
            elif first_word in _DATA_COMMANDS:
                # Remove trailing whitespaces and delimiter.
                sql_cmd = sql_cmd.rstrip()[0:-len(delimiter)]
                if len(sql_cmd) > 0:
                    # Yield previous sql command.
                    yield (cmd_type, sql_cmd)
                cmd_type = "DATA"
                sql_cmd = row
            # If does not match previous conditions but ends with the delimiter
            # then return the current SQL command.
            elif stripped_row.endswith(delimiter):
                # First, yield previous SQL command if it ends with delimiter.
                if sql_cmd.strip().endswith(delimiter):
                    yield (cmd_type, sql_cmd.rstrip()[0:-len(delimiter)])
                    sql_cmd = ''
                # Then, append SQL command to previous and retrieve it.
                sql_cmd = "{0}{1}".format(sql_cmd,
                                          row.rstrip()[0:-len(delimiter)])
                # Yield current SQL command.
                yield (cmd_type, sql_cmd)
                sql_cmd = ''
            # If does not end with the delimiter then append the SQL command.
            else:
                sql_cmd = "{0}{1}".format(sql_cmd, row)
        # Remove trailing whitespaces and delimiter from last line.
        sql_cmd = sql_cmd.rstrip()[0:-len(delimiter)]
        yield (cmd_type, sql_cmd)  # Need last row.
    elif fmt == "raw_csv":
        csv_reader = csv.reader(file_h, delimiter=",")
        for row in csv_reader:
            if row:
                yield row
    else:
        found_obj = ""
        for row in _read_row(file_h, fmt, False):
            # find first word
            if row[0][0:_RPL] == _RPL_PREFIX:
                first_word = \
                    row[0][_RPL:_RPL + row[0][_RPL:].find(' ', _RPL)].upper()
            else:
                first_word = ""
            if row[0][0:_RPL] == _RPL_PREFIX and first_word in _RPL_COMMANDS:
                # join the parts if CSV or TAB
                if fmt in ['csv', 'tab']:
                    # pylint: disable=E1310
                    yield("RPL_COMMAND", ", ".join(row).strip("--"))
                else:
                    yield("RPL_COMMAND", row[0][_RPL:])
                continue
            if row[0][0:_RPL] == _RPL_PREFIX and \
               len(row[0]) > _GTID_PREFIX + _RPL and \
               row[0][_RPL:_GTID_PREFIX + _RPL] in _GTID_COMMANDS:
                yield("GTID_COMMAND", row[0][_RPL:])
                continue
            # Check for basic command
            if (first_word == "" and
                    row[0][0:row[0].find(' ')].upper() in _BASIC_COMMANDS):
                yield("BASIC_COMMAND", row[0])
                continue
            # Check to see if we have a marker for rows of objects or data
            for obj in _IMPORT_LIST:
                if _check_for_object_list(row[0], obj):
                    if obj == _DATA_DECORATE:
                        found_obj = "TABLE_DATA"
                        cmd_type = "DATA"
                        # We have a new table!
                        name = row[0][len(_DATA_DECORATE) + 2:len(row[0])]
                        name = name.strip()
                        db_tbl_name = name.strip(":")
                        yield ("BEGIN_DATA", db_tbl_name)
                    else:
                        found_obj = obj
                        cmd_type = obj
                else:
                    found_obj = ""
                if found_obj != "":
                    break
            if found_obj != "":
                # For files with multiple databases, metadata about the
                # cmd_types appears more than once. Each time we are at a new
                # cmd_type we keep the first occurrence of such metadata and
                # ignore the rest of the occurrences.

                # reset the first_occurrence flag each time we change cmd_type
                if previous_cmd_type is None or previous_cmd_type != cmd_type:
                    first_occurrence = True
                    previous_cmd_type = cmd_type
                if first_occurrence:
                    first_occurrence = False
                else:
                    skip_next_line = True
                continue
            else:
                # We're reading rows here
                if (len(row[0]) > 0 and
                        (row[0][0] == "#" or row[0][0:2] == "--")):
                    continue
                else:
                    # skip column_names only if we're not dealing with DATA
                    if skip_next_line and cmd_type != 'DATA':
                        skip_next_line = False
                        continue
                    else:
                        yield (cmd_type, row)


def _get_db(row):
    """Get the database name from the object.

    row[in]           A row (list) of information from the file

    Returns (string) database name or None if not found
    """
    db_name = None
    if row[0] in _DEFINITION_LIST or row[0] == "sql":
        if row[0] == "sql":
            # Need crude parse here for database statement.
            parts = row[1].split()
            # Identify the database name in statements:
            # DROP {DATABASE | SCHEMA} [IF EXISTS] db_name
            # CREATE {DATABASE | SCHEMA} [IF NOT EXISTS] db_name
            if (parts[0] in ('DROP', 'CREATE') and
                    parts[1] in ('DATABASE', 'SCHEMA')):
                db_name = parts[len(parts) - 1].rstrip().strip(";")
            # USE db_name
            elif parts[0] == 'USE':
                db_name = parts[1].rstrip().strip(";")
        else:
            if row[0] == "GRANT":
                db_name = row[1][2]
            else:
                if len(row[1][0]) > 0 and \
                   row[1][0].upper() not in ('NONE', 'DEF'):
                    db_name = row[1][0]  # --display=BRIEF
                else:
                    db_name = row[1][1]  # --display=FULL
    return db_name


def _build_create_table(db_name, tbl_name, engine, columns, col_ref=None,
                        sql_mode=''):
    """Build the CREATE TABLE command for a table.

    This method uses the data from the _read_next() method to build a
    table from its parts as read from a non-SQL formatted file.

    db_name[in]       Database name for the object
    tbl_name[in]      Name of the table
    engine[in]        Storage engine name for the table
    columns[in]       A list of the column definitions for the table
    col_ref[in]       A dictionary of column names/indexes
    sql_mode[in]      The sql_mode set in the server

    Returns (string) the CREATE TABLE statement.
    """
    if col_ref is None:
        col_ref = {}
    # Quote db_name and tbl_name with backticks if needed
    if not is_quoted_with_backticks(db_name, sql_mode):
        db_name = quote_with_backticks(db_name, sql_mode)
    if not is_quoted_with_backticks(tbl_name, sql_mode):
        tbl_name = quote_with_backticks(tbl_name, sql_mode)

    create_str = "CREATE TABLE %s.%s (\n" % (db_name, tbl_name)
    stop = len(columns)
    pri_keys = set()
    keys = set()
    key_constraints = defaultdict(set)
    col_name_index = col_ref.get("COLUMN_NAME", 0)
    col_type_index = col_ref.get("COLUMN_TYPE", 1)
    is_null_index = col_ref.get("IS_NULLABLE", 2)
    def_index = col_ref.get("COLUMN_DEFAULT", 3)
    col_key_index = col_ref.get("COLUMN_KEY", 4)
    const_name_index = col_ref.get("KEY_CONSTRAINT_NAME", 12)
    ref_tbl_index = col_ref.get("REFERENCED_TABLE_NAME", 8)
    ref_schema_index = col_ref.get("REFERENCED_TABLE_SCHEMA", 14)
    ref_col_index = col_ref.get("COL_NAME", 13)
    ref_col_ref = col_ref.get("REFERENCED_COLUMN_NAME", 15)
    ref_const_name = col_ref.get("CONSTRAINT_NAME", 7)
    update_rule = col_ref.get("UPDATE_RULE", 10)
    delete_rule = col_ref.get("DELETE_RULE", 11)
    used_columns = set()
    for column in range(0, stop):
        cur_col = columns[column]
        # Quote column name with backticks if needed
        col_name = cur_col[col_name_index]
        if not is_quoted_with_backticks(col_name, sql_mode):
            col_name = quote_with_backticks(col_name, sql_mode)
        if col_name not in used_columns:
            # Only add the column definitions to the CREATE string once.
            change_line = ",\n" if column > 0 else ""
            create_str = "{0}{1}  {2} {3}".format(create_str, change_line,
                                                  col_name,
                                                  cur_col[col_type_index])
            if cur_col[is_null_index].upper() != "YES":
                create_str += " NOT NULL"
            if len(cur_col[def_index]) > 0 and \
                    cur_col[def_index].upper() != "NONE":
                create_str += " DEFAULT %s" % cur_col[def_index]
            elif cur_col[is_null_index].upper == "YES":
                create_str += " DEFAULT NULL"
            # Add column to set of columns already used for the CREATE string.
            used_columns.add(col_name)

        if len(cur_col[col_key_index]) > 0:
            if cur_col[col_key_index] == "PRI":
                if cur_col[const_name_index] in ('`PRIMARY`', 'PRIMARY'):
                    pri_keys.add(cur_col[ref_col_index])
            else:
                if cur_col[const_name_index] not in ('`PRIMARY`', 'PRIMARY'):
                    keys.add(
                        (col_name, cur_col[col_key_index])
                    )
                    if cur_col[ref_col_index].startswith(col_name) and \
                        (not cur_col[ref_const_name] or
                         cur_col[ref_const_name] == cur_col[const_name_index]):
                        key_constraints[col_name].add(
                            (cur_col[const_name_index],
                             cur_col[ref_schema_index], cur_col[ref_tbl_index],
                             cur_col[ref_col_index], cur_col[ref_col_ref],
                             cur_col[update_rule], cur_col[delete_rule])
                        )

    key_strs = []
    const_strs = []
    # Create primary key definition string.
    if len(pri_keys) > 0:
        key_list = []
        for key in pri_keys:
            # Quote keys with backticks if needed
            if not is_quoted_with_backticks(key, sql_mode):
                # Handle multiple columns separated by a comma (,)
                cols = key.split(',')
                key = ','.join([quote_with_backticks(col, sql_mode) for col
                                in cols])
            key_list.append(key)
        key_str = "PRIMARY KEY({0})".format(",".join(key_list))
        key_strs.append(key_str)

    for key, column_type in keys:
        key_type = 'UNIQUE ' if column_type == 'UNI' else ''
        if not key_constraints[key]:
            # Handle simple keys
            # Quote column key with backticks if needed
            if not is_quoted_with_backticks(key, sql_mode):
                # Handle multiple columns separated by a comma (,)
                cols = key.split(',')
                key = ','.join([quote_with_backticks(col, sql_mode) for col
                                in cols])
            key_str = "{key_type}KEY ({column})".format(key_type=key_type,
                                                        column=key)
            key_strs.append(key_str)
        else:
            # Handle key with constraints
            for const_def in key_constraints[key]:
                # Keys for constraints or with specific name
                key_name = ''
                if const_def[0] and const_def[0] != const_def[3]:
                    # Quote key name with backticks if needed
                    if not is_quoted_with_backticks(const_def[0], sql_mode):
                        key_name = '{0} '.format(
                            quote_with_backticks(const_def[0], sql_mode))
                    else:
                        key_name = '{0} '.format(const_def[0])
                # Use constraint columns as key if available.
                if const_def[3]:
                    key = const_def[3]
                # Quote column key with backticks if needed
                if not is_quoted_with_backticks(key, sql_mode):
                    # Handle multiple columns separated by a comma (,)
                    cols = key.split(',')
                    key = ','.join([quote_with_backticks(col, sql_mode)
                                    for col in cols])
                key_str = "{key_type}KEY {key_name}({column})".format(
                    key_type=key_type, key_name=key_name, column=key
                )
                key_strs.append(key_str)
                if const_def[2]:
                    # Handle constraint (referenced_table_name found)
                    const_name = const_def[0]
                    # Quote constraint name with backticks if needed
                    if const_name and not is_quoted_with_backticks(const_name,
                                                                   sql_mode):
                        const_name = quote_with_backticks(const_name,
                                                          sql_mode)
                    fkey = const_def[3]
                    # Quote fkey columns with backticks if needed
                    if not is_quoted_with_backticks(fkey, sql_mode):
                        # Handle multiple columns separated by a comma (,)
                        cols = fkey.split(',')
                        fkey = ','.join(
                            [quote_with_backticks(col, sql_mode) for col
                             in cols])
                    ref_key = const_def[4]
                    # Quote reference key columns with backticks if needed
                    if not is_quoted_with_backticks(ref_key, sql_mode):
                        # Handle multiple columns separated by a comma (,)
                        cols = ref_key.split(',')
                        ref_key = ','.join(
                            [quote_with_backticks(col, sql_mode) for col
                             in cols])
                    ref_rules = ''
                    if const_def[6] and const_def[6] == 'CASCADE':
                        ref_rules = ' ON DELETE CASCADE'
                    if const_def[5] and const_def[5] == 'CASCADE':
                        ref_rules = '{0} ON UPDATE CASCADE'.format(ref_rules)
                    key_str = (
                        " CONSTRAINT {cstr} FOREIGN KEY ({fk}) REFERENCES "
                        "{ref_schema}.{ref_table} ({ref_column}){ref_rules}"
                    ).format(cstr=const_name, fk=fkey, ref_schema=const_def[1],
                             ref_table=const_def[2], ref_column=ref_key,
                             ref_rules=ref_rules)
                    const_strs.append(key_str)

    # Build remaining CREATE TABLE string
    key_strs.extend(const_strs)
    keys_str = ',\n '.join(key_strs)
    if keys_str:
        create_str = "{0},\n  {1}\n)".format(create_str, keys_str)
    else:
        create_str = "{0}\n)".format(create_str)
    if engine and len(engine) > 0:
        create_str = "{0} ENGINE={1}".format(create_str, engine)
    create_str = "{0};".format(create_str)

    return create_str


def _build_column_ref(row):
    """Build a dictionary of column references

    row[in]           The header with column names.

    Returns (dictionary) where dict[col_name] = index position
    """
    indexes = {}
    i = 0
    for col in row:
        indexes[col.upper()] = i
        i += 1
    return indexes


def _build_create_objects(obj_type, db, definitions, sql_mode=''):
    """Build the CREATE and GRANT SQL statements for object definitions.

    This method takes the object information read from the file using the
    _read_next() method and constructs SQL definition statements for each
    object. It receives a block of objects and creates a statement for
    each object.

    obj_type[in]      The object type
    db[in]            The database
    definitions[in]   The list of object definition data from the file
    sql_mode[in]      The sql_mode set in the server

    Returns (string[]) - a list of SQL statements for the objects
    """
    create_strings = []
    skip_header = True
    obj_db = ""
    obj_name = ""
    col_list = []
    stop = len(definitions)
    col_ref = {}
    engine = None
    # Now the tricky part.
    for i in range(0, stop):
        if skip_header:
            skip_header = False
            col_ref = _build_column_ref(definitions[i])
            continue
        defn = definitions[i]
        # Read engine from first row and save old value.
        old_engine = engine
        engine = defn[col_ref.get("ENGINE", 2)]
        create_str = ""
        if obj_type == "TABLE":
            if obj_db == "" and obj_name == "":
                obj_db = defn[col_ref.get("TABLE_SCHEMA", 0)]
                obj_name = defn[col_ref.get("TABLE_NAME", 1)]
            if (obj_db == defn[col_ref.get("TABLE_SCHEMA", 0)] and
                    obj_name == defn[col_ref.get("TABLE_NAME", 1)]):
                col_list.append(defn)
            else:
                create_str = _build_create_table(obj_db, obj_name,
                                                 old_engine,
                                                 col_list, col_ref, sql_mode)
                create_strings.append(create_str)
                obj_db = defn[col_ref.get("TABLE_SCHEMA", 0)]
                obj_name = defn[col_ref.get("TABLE_NAME", 1)]
                col_list = [defn]
            # check for end.
            if i + 1 == stop:
                create_str = _build_create_table(obj_db, obj_name, engine,
                                                 col_list, col_ref, sql_mode)
                create_strings.append(create_str)
        elif obj_type == "VIEW":
            # Quote table schema and name with backticks if needed
            if not is_quoted_with_backticks(defn[col_ref.get("TABLE_SCHEMA",
                                                             0)], sql_mode):
                obj_db = quote_with_backticks(defn[col_ref.get("TABLE_SCHEMA",
                                                               0)], sql_mode)
            else:
                obj_db = defn[col_ref.get("TABLE_SCHEMA", 0)]
            if not is_quoted_with_backticks(defn[col_ref.get("TABLE_NAME",
                                                             1)], sql_mode):
                obj_name = quote_with_backticks(defn[col_ref.get("TABLE_NAME",
                                                                 1)], sql_mode)
            else:
                obj_name = defn[col_ref.get("TABLE_NAME", 1)]
            # Create VIEW statement
            create_str = (
                "CREATE ALGORITHM=UNDEFINED DEFINER={defr} "
                "SQL SECURITY {sec} VIEW {scma}.{tbl} AS {defv}; "
            ).format(defr=defn[col_ref.get("DEFINER", 2)],
                     sec=defn[col_ref.get("SECURITY_TYPE", 3)],
                     scma=obj_db, tbl=obj_name,
                     defv=defn[col_ref.get("VIEW_DEFINITION", 4)])
            create_strings.append(create_str)
        elif obj_type == "TRIGGER":
            # Quote required identifiers with backticks
            obj_db = quote_with_backticks(db, sql_mode) \
                if not is_quoted_with_backticks(db, sql_mode) else db

            if not is_quoted_with_backticks(defn[col_ref.get("TRIGGER_NAME",
                                                             0)], sql_mode):
                obj_name = quote_with_backticks(
                    defn[col_ref.get("TRIGGER_NAME", 0)],
                    sql_mode
                )
            else:
                obj_name = defn[col_ref.get("TRIGGER_NAME", 0)]

            if not is_quoted_with_backticks(
                    defn[col_ref.get("EVENT_OBJECT_SCHEMA", 3)], sql_mode):
                evt_scma = quote_with_backticks(
                    defn[col_ref.get("EVENT_OBJECT_SCHEMA", 3)],
                    sql_mode
                )
            else:
                evt_scma = defn[col_ref.get("EVENT_OBJECT_SCHEMA", 3)]

            if not is_quoted_with_backticks(
                    defn[col_ref.get("EVENT_OBJECT_TABLE", 4)], sql_mode):
                evt_tbl = quote_with_backticks(
                    defn[col_ref.get("EVENT_OBJECT_TABLE", 4)],
                    sql_mode
                )
            else:
                evt_tbl = defn[col_ref.get("EVENT_OBJECT_TABLE", 4)]

            # Create TRIGGER statement
            # Important Note: There is a bug in the server when backticks are
            # used in the trigger statement, i.e. the ACTION_STATEMENT value in
            # INFORMATION_SCHEMA.TRIGGERS is incorrect (see BUG##16291011).
            create_str = (
                "CREATE DEFINER={defr} "
                "TRIGGER {scma}.{trg} {act_t} {evt_m} "
                "ON {evt_s}.{evt_t} FOR EACH {act_o} {act_s};"
            ).format(defr=defn[col_ref.get("DEFINER", 1)],
                     scma=obj_db, trg=obj_name,
                     act_t=defn[col_ref.get("ACTION_TIMING", 6)],
                     evt_m=defn[col_ref.get("EVENT_MANIPULATION", 2)],
                     evt_s=evt_scma, evt_t=evt_tbl,
                     act_o=defn[col_ref.get("ACTION_ORIENTATION", 5)],
                     act_s=defn[col_ref.get("ACTION_STATEMENT", 7)])
            create_strings.append(create_str)
        elif obj_type in ("PROCEDURE", "FUNCTION"):
            # Quote required identifiers with backticks
            obj_db = quote_with_backticks(db, sql_mode) \
                if not is_quoted_with_backticks(db, sql_mode) else db

            if not is_quoted_with_backticks(defn[col_ref.get("NAME", 0)],
                                            sql_mode):
                obj_name = quote_with_backticks(defn[col_ref.get("NAME", 0)],
                                                sql_mode)
            else:
                obj_name = defn[col_ref.get("NAME", 0)]

            # Create PROCEDURE or FUNCTION statement
            if obj_type == "FUNCTION":
                func_str = " RETURNS %s" % defn[col_ref.get("RETURNS", 7)]
                if defn[col_ref.get("IS_DETERMINISTI", 3)] == 'YES':
                    func_str = "%s DETERMINISTIC" % func_str
            else:
                func_str = ""
            create_str = (
                "CREATE DEFINER={defr}"
                " {type} {scma}.{name}({par_lst})"
                "{func_ret} {body};"
            ).format(defr=defn[col_ref.get("DEFINER", 5)],
                     type=obj_type, scma=obj_db, name=obj_name,
                     par_lst=defn[col_ref.get("PARAM_LIST", 6)],
                     func_ret=func_str,
                     body=defn[col_ref.get("BODY", 8)])
            create_strings.append(create_str)
        elif obj_type == "EVENT":
            # Quote required identifiers with backticks
            obj_db = quote_with_backticks(db, sql_mode) \
                if not is_quoted_with_backticks(db, sql_mode) else db

            if not is_quoted_with_backticks(defn[col_ref.get("NAME", 0)],
                                            sql_mode):
                obj_name = quote_with_backticks(defn[col_ref.get("NAME", 0)],
                                                sql_mode)
            else:
                obj_name = defn[col_ref.get("NAME", 0)]

            # Create EVENT statement
            create_str = (
                "CREATE EVENT {scma}.{name} "
                "ON SCHEDULE EVERY {int_v} {int_f} "
                "STARTS '{starts}' "
            ).format(scma=obj_db, name=obj_name,
                     int_v=defn[col_ref.get("INTERVAL_VALUE", 5)],
                     int_f=defn[col_ref.get("INTERVAL_FIELD", 6)],
                     starts=defn[col_ref.get("STARTS", 8)])

            ends_index = col_ref.get("ENDS", 9)
            if len(defn[ends_index]) > 0 and \
               defn[ends_index].upper() != "NONE":
                create_str = "%s ENDS '%s' " % (create_str, defn[ends_index])
            if defn[col_ref.get("ON_COMPLETION", 11)] == "DROP":
                create_str = "%s ON COMPLETION NOT PRESERVE " % create_str
            if defn[col_ref.get("STATUS", 10)] == "DISABLED":
                create_str = "%s DISABLE " % create_str
            create_str = "%s DO %s;" % (create_str,
                                        defn[col_ref.get("BODY", 2)])
            create_strings.append(create_str)
        elif obj_type == "GRANT":
            try:
                user, priv, db, tbl = defn[0:4]
            except:
                raise UtilError("Object data invalid: %s : %s" %
                                (obj_type, defn))
            if not tbl:
                tbl = "*"
            elif tbl.upper() == "NONE":
                tbl = "*"

            # Quote required identifiers with backticks
            obj_db = quote_with_backticks(db, sql_mode) \
                if not is_quoted_with_backticks(db, sql_mode) else db
            obj_tbl = quote_with_backticks(tbl, sql_mode) \
                if (tbl != '*' and
                    not is_quoted_with_backticks(tbl, sql_mode)) else tbl

            # Create GRANT statement
            create_str = "GRANT %s ON %s.%s TO %s" % (priv, obj_db, obj_tbl,
                                                      user)
            create_strings.append(create_str)
        elif obj_type in ["RPL_COMMAND", "GTID_COMMAND"]:
            create_strings.append([defn])
        else:
            raise UtilError("Unknown object type discovered: %s" % obj_type)
    return create_strings


def _build_col_metadata(obj_type, definitions):
    """Build a list of column metadata for a table.

    This method takes the object information read from the file using the
    _read_next() method and constructs a list of columns for any tables
    found.

    obj_type[in]      The object type
    definitions[in]   The list of object definition data from the file

    Returns (column_list[(table_name, [(field_name, definition)])])
    """
    skip_header = True
    obj_db = ""
    obj_name = ""
    col_list = []
    table_col_list = []
    stop = len(definitions)
    # Now the tricky part.
    for i in range(0, stop):
        if skip_header:
            skip_header = False
            continue
        defn = definitions[i]
        if obj_type == "TABLE":
            if obj_db == "" and obj_name == "":
                obj_db = defn[0]
                obj_name = defn[1]
            if obj_db == defn[0] and obj_name == defn[1]:
                col_list.append((defn[4], defn[5]))
            else:
                table_col_list.append((obj_name, col_list))
                obj_db = defn[0]
                obj_name = defn[1]
                col_list = [(defn[4], defn[5])]
            # check for end.
            if i + 1 == stop:
                table_col_list.append((obj_name, col_list))
    return table_col_list


def _build_insert_data(col_names, tbl_name, data):
    """Build simple INSERT statements for data.

    col_names[in]     A list of column names for the data
    tbl_name[in]      Table name
    data[in]          The data values

    Returns (string) the INSERT statement.
    """
    # Handle NULL (and None) values, i.e. do not quote them as a string.
    quoted_data = [
        'NULL' if val in ('NULL', None) else to_sql(val) for val in data
    ]
    return "INSERT INTO %s (" % tbl_name + ",".join(col_names) + \
           ") VALUES (" + ','.join(quoted_data) + ");"


def _skip_sql(sql, options):
    """Check to see if we skip this SQL statement

    sql[in]           SQL statement to evaluate
    options[in]       Option dictionary containing the --skip_* options

    Returns (bool) True - skip the statement, False - do not skip
    """

    prefix = sql[0:100].upper().strip()
    if prefix[0:len("CREATE")] == "CREATE":
        # need to test for tables, views, events, triggers, proc, func, db
        index = sql.find(" TABLE ")
        if index > 0:
            return options.get("skip_tables", False)
        index = sql.find(" VIEW ")
        if index > 0:
            return options.get("skip_views", False)
        index = sql.find(" TRIGGER ")
        if index > 0:
            return options.get("skip_triggers", False)
        index = sql.find(" PROCEDURE ")
        if index > 0:
            return options.get("skip_procs", False)
        index = sql.find(" FUNCTION ")
        if index > 0:
            return options.get("skip_funcs", False)
        index = sql.find(" EVENT ")
        if index > 0:
            return options.get("skip_events", False)
        index = sql.find(" DATABASE ")
        if index > 0:
            return options.get("skip_create", False)
        return False
    # If we skip create_db, need to skip the drop too
    elif prefix[0:len("DROP")] == "DROP":
        return options.get("skip_create", False)
    elif prefix[0:len("GRANT")] == "GRANT":
        return options.get("skip_grants", False)
    elif prefix[0:len("INSERT")] == "INSERT":
        return options.get("skip_data", False)
    elif prefix[0:len("UPDATE")] == "UPDATE":
        return options.get("skip_blobs", False)
    elif prefix[0:len("USE")] == "USE":
        return options.get("skip_create", False)
    return False


def _skip_object(obj_type, options):
    """Check to see if we skip this object type

    obj_type[in]      Type of object for the --skip_* option
                      (e.g. "tables", "data", "views", etc.)
    options[in]       Option dictionary containing the --skip_* options

    Returns (bool) True - skip the object, False - do not skip
    """
    obj = obj_type.upper()
    if obj == "TABLE":
        return options.get("skip_tables", False)
    elif obj == "VIEW":
        return options.get("skip_views", False)
    elif obj == "TRIGGER":
        return options.get("skip_triggers", False)
    elif obj == "PROCEDURE":
        return options.get("skip_procs", False)
    elif obj == "FUNCTION":
        return options.get("skip_funcs", False)
    elif obj == "EVENT":
        return options.get("skip_events", False)
    elif obj == "GRANT":
        return options.get("skip_grants", False)
    elif obj == "CREATE_DB":
        return options.get("skip_create", False)
    elif obj == "DATA":
        return options.get("skip_data", False)
    elif obj == "BLOB":
        return options.get("skip_blobs", False)
    else:
        return False


def _exec_statements(statements, destination, fmt, options, dryrun=False):
    """Execute a list of SQL statements.

    Execute SQL statements from the provided list in the destination server,
    according to the provided options. This method also manage autocommit and
    bulk insert options in order to optimize the performance of the statements
    execution.

    statements[in]    A list of SQL statements to execute
    destination[in]   A connection to the destination server
    fmt[in]           Format of import file
    options[in]       Option dictionary containing the --skip_* options
    dryrun[in]        If True, print the SQL statements and do not execute

    Returns (bool) - True if all execute, raises error if one fails
    """
    new_engine = options.get("new_engine", None)
    def_engine = options.get("def_engine", None)
    quiet = options.get("quiet", False)
    autocommit = options.get('autocommit', False)
    bulk_insert = not options.get('single', True)

    # Set autocommit and query options adequately.
    if autocommit and not destination.autocommit_set():
        destination.toggle_autocommit(enable=1)
    elif not autocommit and destination.autocommit_set():
        destination.toggle_autocommit(enable=0)
    query_opts = {'fetch': False, 'columns': False, 'commit': False}

    if bulk_insert:
        max_inserts = options.get('max_bulk_insert', 30000)
        count = 0
        bulk_insert_start = None
        bulk_values = []
        # Compile regexp to split INSERT values here, in order to reuse it
        # and improve performance of _parse_insert_statement().
        re_value_split = re.compile("VALUES?", re.IGNORECASE)

    exec_commit = False

    # Process all statements.
    # pylint: disable=R0101
    for statement in statements:
        # Each statement can be either a string or a list of strings (BLOB
        # statements).
        if (isinstance(statement, str) and
                (new_engine is not None or def_engine is not None) and
                statement[0:12].upper() == "CREATE TABLE"):
            # Add statements to substitute engine.
            i = statement.find(' ', 13)
            tbl_name = statement[13:i]
            st_list = destination.substitute_engine(tbl_name, statement,
                                                    new_engine, def_engine,
                                                    quiet)
        elif bulk_insert:
            # Bulk insert (if possible) to execute as a single statement.
            # Need to guard against lists of BLOB statements.
            if (isinstance(statement, str) and
                    statement[0:6].upper().startswith('INSERT')):
                # Parse INSERT statement.
                insert_start, values = _parse_insert_statement(statement,
                                                               re_value_split)
                if values is None:
                    # Cannot bulk insert.
                    if bulk_values:
                        # Existing bulk insert to process.
                        st_list = [",".join(bulk_values)]
                        bulk_values = []
                        count = 0
                    else:
                        st_list = []
                    st_list.append(statement)
                elif not bulk_values:
                    # Start creating a new bulk insert.
                    bulk_insert_start = insert_start
                    bulk_values.append(
                        "{0} VALUES {1}".format(bulk_insert_start, values)
                    )
                    count += 1
                    st_list = []
                elif insert_start != bulk_insert_start:
                    # Different INSERT found (table, options or syntax),
                    # generate bulk insert statement to execute and initiate a
                    # new bulk insert.
                    st_list = [",".join(bulk_values)]
                    bulk_values = []
                    count = 0
                    bulk_insert_start = insert_start
                    bulk_values.append(
                        "{0} VALUES {1}".format(bulk_insert_start, values)
                    )
                    count += 1
                elif count >= max_inserts:
                    # Maximum bulk insert size reached (to avoid broken pipe
                    # error), generate bulk to execute and initiate new one.
                    st_list = [",".join(bulk_values)]
                    bulk_values = []
                    count = 0
                    bulk_values.append(
                        "{0} VALUES {1}".format(bulk_insert_start, values)
                    )
                else:
                    bulk_values.append(values)
                    count += 1
                    st_list = []
            else:
                # Can be a regular statement or a list of BLOB statements
                # that must not be bundled together.
                if bulk_values:
                    # Existing bulk insert to process.
                    st_list = [",".join(bulk_values)]
                    bulk_values = []
                    count = 0
                else:
                    st_list = []
                if isinstance(statement, list):
                    # list of BLOB data statements, either updates or inserts.
                    st_list.extend(statement)
                else:  # Other statements.
                    st_list.append(statement)
        else:
            # Common statement, just add it to be executed.
            st_list = [statement]

        # Execute statements list.
        for st in st_list:
            # Execute query.
            try:
                if dryrun and not _skip_sql(st, options):
                    print(st)
                elif fmt != "sql" or not _skip_sql(st, options):
                    # Check query type to determine if a COMMIT is needed, in
                    # order to avoid Error 1694 (Cannot modify SQL_LOG_BIN
                    # inside transaction).
                    if not autocommit:
                        if st[0:_GTID_PREFIX].upper() == _SQL_LOG_BIN_CMD:
                            # SET SQL_LOG_BIN command found.
                            destination.commit()
                            exec_commit = True
                    destination.exec_query(st, options=query_opts)
                    if exec_commit:
                        # For safety, COMMIT after SET SQL_LOG_BIN command.
                        destination.commit()
                        exec_commit = False
            # It is not a good practice to catch the base Exception class,
            # instead all errors should be caught in a Util/Connector error.
            # Exception is only caught for safety (unanticipated errors).
            except UtilError as err:
                raise UtilError("Invalid statement:\n{0}"
                                "\nERROR: {1}".format(st, err.errmsg))
            except Exception as err:
                raise UtilError("Unexpected error:\n{0}".format(err))

    if bulk_insert and bulk_values:
        # Make sure last bulk insert is executed.
        st = ",".join(bulk_values)
        try:
            if dryrun and not _skip_sql(st, options):
                print(st)
            elif fmt != "sql" or not _skip_sql(st, options):
                destination.exec_query(st, options=query_opts)
        except UtilError as err:
            raise UtilError("Invalid statement:\n{0}"
                            "\nERROR: {1}".format(st, err.errmsg))
        except Exception as err:
            # Exception is only caught for safety (unanticipated errors).
            raise UtilError("Unexpected error:\n{0}".format(err))

    # Commit at the end (if autocommit is disabled).
    if not autocommit:
        destination.commit()
    return True


def _parse_insert_statement(insert_stmt, regexp_split_values=None):
    """Parse an INSERT statement to build bulk insert.

    This method parses INSERT statements, separating the VALUES tuple from the
    beginning of the query (in order to build bulk insert). The method also
    verify if the statement is already a bulk insert or use unsupported
    options/syntax, an in this case the initial statement is returned without
    any separated values.

    insert_stmt[in]             INSERT statement to be parsed.
    regexp_split_values[in]     Compiled regular expression to split the
                                VALUES|VALUE of the INSERT statement. This
                                parameter can be used for performance reason,
                                avoiding compiling the regexp at each call if
                                not specified.

    Returns a tuple with the start of the INSERT statement (without values)
    and the values, or the full statement and none if the INSERT syntax or
    query options are not supported or it is already a bulk insert.
    """
    if not regexp_split_values:
        # Split statement by VALUES|VALUE.
        regexp_split_values = re.compile("VALUES?", re.IGNORECASE)
    insert_values = regexp_split_values.split(insert_stmt)
    try:
        values = insert_values[1]
    except IndexError:
        # INSERT statement does not contain 'VALUES'.
        # The following syntax are not supported to build bulk inserts:
        # - INSERT INTO tbl_name SET col_name= expr, ...
        # - INSERT INTO tbl_name SELECT ...
        return insert_stmt, None
    values = values.strip(' ;')

    # Check if already a bulk insert (if it has more than one tuple of values),
    # or if other options are used at the end (e.g., ON DUPLICATE KEY UPDATE).
    # In those cases, the original statement is returned (no bulk insert).
    prev_char = ''
    found = 0
    skip_in_str = False
    # Find first closing bracket ')', end of first VALUES tuple.
    # Note: need to ignore ')' in strings.
    for idx, char in enumerate(values[1:]):
        if char == "'" and prev_char != '\\':
            skip_in_str = not skip_in_str
        elif char == ')' and not skip_in_str:
            found = idx + 2  # 1 + 1 (skip first char + need to check next).
            break
        prev_char = char
    # Check if there are more values/options after the first closing bracket.
    if len(values[found:]) > 1:
        return insert_stmt, None  # Return original statement (not supported).

    return insert_values[0].strip(), values


def _get_column_metadata(tbl_class, table_col_list):
    """Get the column metadata from the list of columns.

    tbl_class[in]      Class instance for table
    table_col_list[in] List of table columns for all tables
    """

    for tbl_col_def in table_col_list:
        if tbl_col_def[0] == tbl_class.q_tbl_name:
            tbl_class.get_column_metadata(tbl_col_def[1])
            return True
    return False


def multiprocess_file_import_task(import_file_task):
    """Multiprocess import file method.

    This method wraps the import_file method to allow its concurrent
    execution by a pool of processes.

    import_file_task[in]    dictionary of values required by a process to
                            perform the file import task, namely:
                            {'srv_con': <dict with server connections values>,
                             'file_name': <file to import>,
                             'options': <dict of options>,
                            }
    """
    # Get input values to execute task.
    srv_con_values = import_file_task.get('srv_con')
    file_name = import_file_task.get('file_name')
    options = import_file_task.get('options')
    # Execute import file task.
    # NOTE: Must handle any exception here, because worker processes will not
    # propagate them to the main process.
    try:
        import_file(srv_con_values, file_name, options)
    except UtilError:
        _, err, _ = sys.exc_info()
        print("ERROR: {0}".format(err.errmsg))


def import_file(dest_val, file_name, options):
    """Import a file

    This method reads a file and, if needed, transforms the file into
    discrete SQL statements for execution on the destination server.

    It accepts any of the formal structured files produced by the
    mysqlexport utility including formats SQL, CSV, TAB, GRID, and
    VERTICAL.

    It will read these files and skip or include the definitions or data
    as specified in the options. An error is raised for any conversion
    errors or errors while executing the statements.

    Users are highly encouraged to use the --dryrun option which will
    print the SQL statements without executing them.

    dest_val[in]       a dictionary containing connection information for the
                       destination including:
                       (user, password, host, port, socket)
    file_name[in]      name (and path) of the file to import
    options[in]        a dictionary containing the options for the import:
                       (skip_tables, skip_views, skip_triggers, skip_procs,
                       skip_funcs, skip_events, skip_grants, skip_create,
                       skip_data, no_header, display, format, and debug)

    Returns bool True = success, False = error
    """
    def _process_definitions(statements, table_col_list, db_name, sql_mode):
        """Helper method to dig through the definitions for create statements
        """
        # First, get the SQL strings
        sql_strs = _build_create_objects(obj_type, db_name, definitions,
                                         sql_mode)
        statements.extend(sql_strs)
        # Now, save the column list
        col_list = _build_col_metadata(obj_type, definitions)
        if len(col_list) > 0:
            table_col_list.extend(col_list)

    def _process_data(tbl_name, statements, columns, table_col_list,
                      table_rows, skip_blobs, use_columns_names=False):
        """Process data: If there is data here, build bulk inserts
        First, create table reference, then call insert_rows()
        """
        tbl = Table(destination, tbl_name)
        # Need to check to see if table exists!
        if tbl.exists():
            columns_defn = None
            if use_columns_names:
                # Get columns definitions
                res = tbl.server.exec_query("explain {0}".format(tbl_name))
                # Only add selected columns
                columns_defn = [row for row in res if row[0] in columns]
                # Sort by selected columns definitions
                columns_defn.sort(key=lambda item: columns.index(item[0]))
            tbl.get_column_metadata(columns_defn)
            col_meta = True
        elif len(table_col_list) > 0:
            col_meta = _get_column_metadata(tbl, table_col_list)
        else:
            fix_cols = [(tbl.tbl_name, columns)]
            col_meta = _get_column_metadata(tbl, fix_cols)
        if not col_meta:
            raise UtilError("Cannot build bulk insert statements without "
                            "the table definition.")
        columns_names = columns[:] if use_columns_names else None
        ins_strs = tbl.make_bulk_insert(table_rows, tbl.q_db_name,
                                        columns_names, skip_blobs=skip_blobs)
        if len(ins_strs[0]) > 0:
            statements.extend(ins_strs[0])
        # If we have BLOB statements, lets put them in a list together, to
        # distinguish them from normal statements and prevent them from being
        # bundled together later in the _exec_statements function.
        if len(ins_strs[1]) > 0 and not skip_blobs:
            statements.extend([ins_strs[1]])

    # Gather options
    fmt = options.get("format", "sql")
    no_headers = options.get("no_headers", False)
    quiet = options.get("quiet", False)
    import_type = options.get("import_type", "definitions")
    single = options.get("single", True)
    dryrun = options.get("dryrun", False)
    do_drop = options.get("do_drop", False)
    skip_blobs = options.get("skip_blobs", False)
    skip_gtid = options.get("skip_gtid", False)

    # Attempt to connect to the destination server
    conn_options = {
        'quiet': quiet,
        'version': "5.1.30",
    }
    servers = connect_servers(dest_val, None, conn_options)

    destination = servers[0]

    # Check storage engines
    check_engine_options(destination,
                         options.get("new_engine", None),
                         options.get("def_engine", None),
                         False, options.get("quiet", False))

    if not quiet:
        if import_type == "both":
            text = "definitions and data"
        else:
            text = import_type
        print("# Importing {0} from {1}.".format(text, file_name))

    # Setup variables we will need
    skip_header = not no_headers
    if fmt == "sql":
        skip_header = False
    get_db = True
    check_privileges = True
    db_name = None
    file_h = open(file_name)
    columns = []
    read_columns = False
    has_data = False
    use_columns_names = False
    table_rows = []
    obj_type = ""
    definitions = []
    statements = []
    table_col_list = []
    tbl_name = ""
    skip_rpl = options.get("skip_rpl", False)
    gtid_command_found = False
    supports_gtid = servers[0].supports_gtid() == 'ON'
    skip_gtid_warning_printed = False
    gtid_version_checked = False
    sql_mode = destination.select_variable("SQL_MODE")

    if fmt == "raw_csv":
        # Use the first row as columns
        read_columns = True

        # Use columns names in INSERT statement
        use_columns_names = True

        table = options.get("table", None)
        (db_name_part, tbl_name_part) = parse_object_name(table, sql_mode)

        # Work with quoted objects
        db_name = (db_name_part if is_quoted_with_backticks(db_name_part,
                                                            sql_mode)
                   else quote_with_backticks(db_name_part, sql_mode))
        tbl_name = (tbl_name_part if is_quoted_with_backticks(tbl_name_part,
                                                              sql_mode)
                    else quote_with_backticks(tbl_name_part, sql_mode))
        tbl_name = ".".join([db_name, tbl_name])

        # Check database existence and permissions
        dest_db = Database(destination, db_name)
        if not dest_db.exists():
            raise UtilDBError(
                "The database does not exist: {0}".format(db_name)
            )

        # Check user permissions for write
        dest_db.check_write_access(dest_val['user'], dest_val['host'], options)
        check_privileges = False  # No need to check privileges again.

        # Check table existence
        tbl = Table(destination, tbl_name)
        if not tbl.exists():
            raise UtilDBError("The table does not exist: {0}".format(table))

    # Read the file one object/definition group at a time
    databases = []
    # pylint: disable=R0101
    for row in read_next(file_h, fmt):
        # Check if --format=raw_csv
        if fmt == "raw_csv":
            if read_columns:
                # Use the first row as columns names
                columns = row[:]
                read_columns = False
                continue
            if single:
                statements.append(_build_insert_data(columns, tbl_name, row))
            else:
                table_rows.append(row)
            has_data = True
            continue
        # Check for replication command
        if row[0] == "RPL_COMMAND":
            if not skip_rpl:
                statements.append(row[1])
            continue
        if row[0] == "GTID_COMMAND":
            gtid_command_found = True
            if not supports_gtid:
                # only display warning once
                if not skip_gtid_warning_printed:
                    print _GTID_SKIP_WARNING
                    skip_gtid_warning_printed = True
            elif not skip_gtid:
                if not gtid_version_checked:
                    gtid_version_checked = True
                    # Check GTID version for complete feature support
                    servers[0].check_gtid_version()
                    # Check the gtid_purged value too
                    servers[0].check_gtid_executed("import")
                statements.append(row[1])
            continue
        # Check for basic command
        if row[0] == "BASIC_COMMAND":
            if import_type != "data" or "FOREIGN_KEY_CHECKS" in row[1].upper():
                # Process existing data rows to keep execution order.
                if len(table_rows) > 0:
                    _process_data(tbl_name, statements, columns,
                                  table_col_list, table_rows, skip_blobs,
                                  use_columns_names)
                    table_rows = []
                # Now, add command to to the statements list.
                statements.append(row[1])
            continue
        # In the first pass, try to get the database name from the file
        if row[0] == "TABLE":
            db = _get_db(row)
            if db not in ["TABLE_SCHEMA", "TABLE_CATALOG"] and \
                    db not in databases:
                databases.append(db)
                get_db = True
        if get_db:
            if skip_header:
                skip_header = False
            else:
                db_name = _get_db(row)
                # quote db_name with backticks if needed
                if db_name and not is_quoted_with_backticks(db_name, sql_mode):
                    db_name = quote_with_backticks(db_name, sql_mode)
                # No need to get the db_name when found.
                get_db = False if db_name else get_db
                if do_drop and import_type != "data":
                    statements.append("DROP DATABASE IF EXISTS %s;" % db_name)
                if import_type != "data":
                    # If has a CREATE DATABASE statement and the database
                    # exists and the --drop-first option is not provided,
                    # issue an error message
                    if db_name and not do_drop and row[0] == "sql":
                        dest_db = Database(destination, db_name)
                        if dest_db.exists() and \
                                row[1].upper().startswith("CREATE DATABASE"):
                            raise UtilDBError("The database {0} exists. "
                                              "Use --drop-first to drop the "
                                              "database before importing."
                                              "".format(db_name))
                    if not _skip_object("CREATE_DB", options) and \
                       fmt != 'sql':
                        statements.append("CREATE DATABASE %s;" % db_name)

        # This is the first time through the loop so we must
        # check user permissions on source for all databases
        if check_privileges and db_name:
            dest_db = Database(destination, db_name)

            # Make a dictionary of the options
            access_options = options.copy()

            dest_db.check_write_access(dest_val['user'], dest_val['host'],
                                       access_options)
            check_privileges = False  # No need to check privileges again.

        # Now check to see if we want definitions, data, or both:
        if row[0] == "sql" or row[0] in _DEFINITION_LIST:
            if fmt != "sql" and len(row[1]) == 1:
                raise UtilError("Cannot read an import file generated with "
                                "--display=NAMES")

            if import_type in ("definitions", "both"):
                if fmt == "sql":
                    statements.append(row[1])
                else:
                    if obj_type == "":
                        obj_type = row[0]
                    if obj_type != row[0]:
                        if len(definitions) > 0:
                            _process_definitions(statements, table_col_list,
                                                 db_name, sql_mode)
                        obj_type = row[0]
                        definitions = []
                    if not _skip_object(row[0], options):
                        definitions.append(row[1])
        else:
            # see if there are any definitions to process
            if len(definitions) > 0:
                _process_definitions(statements, table_col_list, db_name,
                                     sql_mode)
                definitions = []

            if import_type in ("data", "both"):
                if _skip_object("DATA", options):
                    continue  # skip data
                elif fmt == "sql":
                    statements.append(row[1])
                    has_data = True
                else:
                    if row[0] == "BEGIN_DATA":
                        # Start of table so first row is columns.
                        if len(table_rows) > 0:
                            _process_data(tbl_name, statements, columns,
                                          table_col_list, table_rows,
                                          skip_blobs)
                            table_rows = []
                        read_columns = True
                        tbl_name = row[1]
                        if not is_quoted_with_backticks(tbl_name, sql_mode):
                            db, _, tbl = tbl_name.partition('.')
                            q_db = quote_with_backticks(db, sql_mode)
                            q_tbl = quote_with_backticks(tbl, sql_mode)
                            tbl_name = ".".join([q_db, q_tbl])
                    else:
                        if read_columns:
                            columns = row[1]
                            read_columns = False
                        else:
                            if not single:
                                # Convert 'NULL' to None to be correctly
                                # handled internally
                                data = [None if val == 'NULL' else val
                                        for val in row[1]]
                                table_rows.append(data)
                                has_data = True
                            else:
                                text = _build_insert_data(columns, tbl_name,
                                                          row[1])
                                statements.append(text)

                                has_data = True
    # Process remaining definitions
    if len(definitions) > 0:
        _process_definitions(statements, table_col_list, db_name, sql_mode)
        definitions = []

    # Process remaining data rows
    if len(table_rows) > 0:
        _process_data(tbl_name, statements, columns, table_col_list,
                      table_rows, skip_blobs, use_columns_names)
    elif import_type == "data" and not has_data:
        print("# WARNING: No data was found.")

    # Now process the statements
    _exec_statements(statements, destination, fmt, options, dryrun)

    file_h.close()

    # Check gtid process
    if supports_gtid and not gtid_command_found:
        print(_GTID_MISSING_WARNING)

    if not quiet:
        if options['multiprocess'] > 1:
            # Indicate processed file for multiprocessing.
            print("#...done. ({0})".format(file_name))
        else:
            print("#...done.")
    return True
