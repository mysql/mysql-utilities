#!/usr/bin/env python
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

"""
This file contains the import operations that will import object metadata or
table data.
"""

import csv
import re
import sys
from itertools import imap
from mysql.utilities.exception import UtilError

# List of database objects for enumeration
_DATA_DECORATE = "DATA FOR TABLE"
_DATABASE, _TABLE, _VIEW, _TRIG, _PROC, _FUNC, _EVENT, _GRANT = "DATABASE", \
    "TABLE", "VIEW", "TRIGGER", "PROCEDURE", "FUNCTION", "EVENT", "GRANT"
_IMPORT_LIST = [_TABLE, _VIEW, _TRIG, _PROC, _FUNC, _EVENT,
                _GRANT, _DATA_DECORATE]
_DEFINITION_LIST = [_TABLE, _VIEW, _TRIG, _PROC, _FUNC, _EVENT, _GRANT]
_BASIC_COMMANDS = ["CREATE", "USE", "GRANT", "DROP"]
_DATA_COMMANDS = ["INSERT", "UPDATE"]
_RPL_COMMANDS = ["START", "STOP", "CHANGE"]
_RPL_PREFIX = "-- "

def _read_row(file, format, skip_comments=False):
    """Read a row of from the file.

    This method reads the file attempting to read and translate the data
    based on the format specified.

    file[in]          Opened file handle
    format[in]        One of SQL,CSV,TAB,GRID,or VERTICAL
    skip_comments[in] If True, do not return lines starting with '#'

    Returns (tuple) - one row of data
    """

    if format == "sql":
        # Easiest - just read a row and return it.
        for row in file.readlines():
            if row[0] != '#' and row[0:2] != "--":
                yield row.strip('\n')
    elif format == "vertical":
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
        for row in file.readlines():
            # Process replication commands
            if row[0:len(_RPL_PREFIX)] == _RPL_PREFIX:
                # find first word
                first_word = row[len(_RPL_PREFIX):row.find(' ')].upper()
                if first_word in _RPL_COMMANDS:
                    yield row
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
                    new_row = []
                    new_row.append(row)
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
                data_row.append(field[1][0:len(field[1])-1].strip())
            elif len(field) == 4: # date field!
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
        if format == "csv":
            separator = ","
        elif format == "tab":
            separator = "\t"
        elif format == "grid":
            separator = "|"
        csv_reader = csv.reader(file, delimiter=separator)
        for row in csv_reader:
            # find first word
            if row[0][0:len(_RPL_PREFIX)] == _RPL_PREFIX:
                rpl = len(_RPL_PREFIX)
                first_word = row[0][rpl:rpl+row[0][rpl:].find(' ')].upper()
            else:
                first_word = ""
            if row[0][0:len(_RPL_PREFIX)] == _RPL_PREFIX and \
                first_word in _RPL_COMMANDS:
                yield row
            elif format == "grid":
                if len(row[0]) > 0:
                    if row[0][0] == '+':
                        continue
                    elif (row[0][0] == '#' or row[0][0:2] == "--") and \
                         not skip_comments:
                        yield row
                else:
                    new_row = []
                    for col in row[1:len(row)-1]:
                        new_row.append(col.strip())
                    yield new_row
            else:
                if (len(row[0]) == 0 or row[0][0] != '#' or \
                    row[0][0:2] != "--") or ((row[0][0] == '#' or \
                    row[0][0:2] == "--") and not skip_comments):
                    yield row


def _check_for_object_list(row, obj_type):
    """Check to see if object is in the list of valid objects.

    row[in]           A row containing an object
    obj_type[in]      Object type to find

    Returns (bool) - True = object is obj_type
                     False = object is not obj_type
    """
    if row[0:len(obj_type)+2].upper() == "# %s" % obj_type:
        if row.find("none found") < 0:
            return True
        else:
            return False
    else:
        return False


def read_next(file, format, no_headers=False):
    """Read properly formatted import file and return the statements.

    This method reads the next object from the file returning a tuple
    containing the type of object - either a definition, SQL statment,
    or the beginning of data rows and the actual data from the file.

    It uses the _read_row() method to read the file returning either
    a list of SQL commands (i.e. from a --format=SQL file) or a list
    of the data from the file (_read_row() converts all non-SQL formatted
    files into lists). This allows the caller to request an object block
    at a time from the file without knowing the format of the file.

    file[in]          Opened file handle
    format[in]        One of SQL,CSV,TAB,GRID,or VERTICAL
    no_headers[in]    If True, file has headers (we skip them)

    Returns (tuple) - ('SQL'|'DATA'|'BEGIN_DATA'|'<object>', <data read>)
    """
    cmd_type = ""
    multiline = False
    if format == "sql":
        sql_cmd = ""
        for row in _read_row(file, "sql", True):
            first_word = row[0:row.find(' ')].upper() # find first word
            # Skip these nonsense rows
            if len(row) == 0 or row[0] == "#"or row[0:2] == "||":
                continue
            # Test for new statement
            elif row[0:len("DELIMITER ;")].upper() == "DELIMITER ;":
                yield (cmd_type, sql_cmd)
                sql_cmd = ""
                multiline = False
            elif multiline: # save multiple line statements
                sql_cmd += "\n%s" % row
            elif row[0:len("DELIMITER ||")].upper() == "DELIMITER ||":
                if len(sql_cmd) > 0:
                    #yield goes here
                    yield (cmd_type, sql_cmd)
                    sql_cmd = ""
                cmd_type = "sql"
                multiline = True
            elif first_word in _BASIC_COMMANDS:
                if len(sql_cmd) > 0:
                    #yield goes here
                    yield (cmd_type, sql_cmd)
                cmd_type = "sql"
                sql_cmd = row
            elif first_word in _RPL_COMMANDS:
                if len(sql_cmd) > 0:
                    #yield goes here
                    yield (cmd_type, sql_cmd)
                cmd_type = "RPL_COMMAND"
                sql_cmd = row
            elif first_word in _DATA_COMMANDS:
                if len(sql_cmd) > 0:
                    #yield goes here
                    yield (cmd_type, sql_cmd)
                cmd_type = "DATA"
                sql_cmd = row
            else:
                sql_cmd += row
        yield (cmd_type, sql_cmd) # need last row.
    else:
        table_rows = []
        found_obj = ""
        for row in _read_row(file, format, False):
            # find first word
            if row[0][0:len(_RPL_PREFIX)] == _RPL_PREFIX:
                rpl = len(_RPL_PREFIX)
                first_word = row[0][rpl:rpl+row[0][rpl:].find(' ')].upper()
            else:
                first_word = ""
            if row[0][0:len(_RPL_PREFIX)] == _RPL_PREFIX and \
                first_word in _RPL_COMMANDS:
                new_row = ", ".join(row)
                yield("RPL_COMMAND", new_row[len(_RPL_PREFIX):])
                continue
            # Check to see if we have a marker for rows of objects or data
            for obj in _IMPORT_LIST:
                if _check_for_object_list(row[0], obj):
                    if obj == _DATA_DECORATE:
                        found_obj = "TABLE_DATA"
                        cmd_type = "DATA"
                        # We have a new table!
                        str = row[0][len(_DATA_DECORATE)+2:len(row[0])]
                        str = str.strip()
                        db_tbl_name = str.strip(":")
                        yield ("BEGIN_DATA", db_tbl_name)
                    else:
                        found_obj = obj
                        cmd_type = obj
                else:
                    found_obj = ""
                if found_obj != "":
                    break
            if found_obj != "":
                continue
            else:
                # We're reading rows here
                if len(row[0]) > 0 and (row[0][0] == "#" or row[0][0:2] == "--"):
                    continue
                else:
                    yield (cmd_type, row)
        if row[0][0] != "#" and row[0][0:2] != "--":
            yield (cmd_type, row)


def _get_db(row):
    """Get the database name from the object.

    row[in]           A row (list) of information from the file

    Returns (string) database name or None if not found
    """
    db_name = None
    if (row[0] in _DEFINITION_LIST or row[0] == "sql"):
        if row[0] == "sql":
            # Need crude parse here for database statement.
            parts = ()
            parts = row[1].split(" ")
            if parts[0] == "DROP":
                db_name = parts[4].strip(";")
            else:
                db_name = parts[1].strip(";")
        else:
            if row[0] == "GRANT":
                db_name = row[1][2]
            else:
                if len(row[1][0]) > 0 and \
                   row[1][0].upper() not in ('NONE', 'DEF'):
                    db_name = row[1][0] # --display=BRIEF
                else:
                    db_name = row[1][1] # --display=FULL
    return db_name


def _build_create_table(db_name, tbl_name, engine, columns, col_ref={}):
    """Build the CREATE TABLE command for a table.

    This method uses the data from the _read_next() method to build a
    table from its parts as read from a non-SQL formatted file.

    db_name[in]       Database name for the object
    tbl_name[in]      Name of the table
    engine[in]        Storage engine name for the table
    columns[in]       A list of the column definitions for the table
    col_ref[in]       A dictionary of column names/indexes

    Returns (string) the CREATE TABLE statement.
    """
    create_str = "CREATE TABLE `%s`.`%s` (\n" % (db_name, tbl_name)
    stop = len(columns)
    pri_keys = []
    keys = []
    key_str = ""
    col_name_index = col_ref.get("COLUMN_NAME", 0)
    col_type_index = col_ref.get("COLUMN_TYPE", 1)
    is_null_index = col_ref.get("IS_NULLABLE", 2)
    def_index = col_ref.get("COLUMN_DEFAULT", 3)
    col_key_index = col_ref.get("COLUMN_KEY", 4)
    const_name_index = col_ref.get("CONSTRAINT_NAME", 7)
    ref_tbl_index = col_ref.get("REFERENCED_TABLE_NAME", 8)
    ref_col_index = col_ref.get("COL_NAME", 13)
    ref_col_ref = col_ref.get("REFERENCED_COLUMN_NAME", 15)
    constraints = []
    for column in range(0,stop):
        cur_col = columns[column]
        create_str += "  `%s` %s" % (cur_col[col_name_index],
                                     cur_col[col_type_index])
        if cur_col[is_null_index].upper() != "YES":
            create_str += " NOT NULL"
        if len(cur_col[def_index]) > 0 and cur_col[def_index].upper() != "NONE":
            create_str += " DEFAULT %s" % cur_col[def_index]
        elif cur_col[is_null_index].upper == "YES":
            create_str += " DEFAULT NULL"
        if len(cur_col[col_key_index]) > 0:
            if cur_col[col_key_index] == "PRI":
                pri_keys.append(cur_col[col_name_index])
            else:
                keys.append(cur_col[col_name_index])
        if column+1 < stop:
            create_str += ",\n"
    if len(pri_keys) > 0:
        key_list = pri_keys
        key_str = ",\n  PRIMARY KEY("
    elif len(keys) > 0:
        key_list = keys
        key_str = ",\n  KEY `%s` (" % cur_col[const_name_index]
        constraints.append((cur_col[const_name_index], cur_col[ref_tbl_index],
                            cur_col[ref_col_index], cur_col[ref_col_ref]))
    if len(key_str) > 0:
        stop = len(key_list)
        for key in range(0,stop):
            key_str += "`%s`" % key_list[key]
            if key+1 < stop-1:
                key_str += ", "
        key_str += ")"
        create_str += key_str
    if len(constraints) > 0:
        for constraint in constraints:
            constraint_str = "  CONSTRAINT `%s` " % constraint[0]
            constraint_str += "FOREIGN KEY (`%s`) " % constraint[2]
            constraint_str += "REFERENCES `%s` (`%s`)" % \
                              (constraint[1], constraint[3])
            create_str += ",\n" + constraint_str
    create_str += "\n)"
    if engine is not None and len(engine) > 0:
        create_str += " ENGINE=%s" % engine
    create_str += ";"
    return create_str


def _build_column_ref(row):
    """Build a dictionary of column references

    row[in]           The header with column names.

    Returns (dictionary) where dict[col_name] = index position
    """
    indexes = { }
    i = 0
    for col in row:
        indexes[col.upper()] = i
        i += 1
    return indexes


def _build_create_objects(obj_type, db, definitions):
    """Build the CREATE and GRANT SQL statments for object definitions.

    This method takes the object information read from the file using the
    _read_next() method and constructs SQL definition statements for each
    object. It receives a block of objects and creates a statement for
    each object.

    obj_type[in]      The object type
    db[in]            The database
    definitions[in]   The list of object definition data from the file

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
    for i in range(0,stop):
        if skip_header:
            skip_header = False
            col_ref = _build_column_ref(definitions[i])
            continue
        defn = definitions[i]
        # Read engine from first row and save old value.
        old_engine = engine
        engine = defn[col_ref.get("ENGINE",2)]
        create_str = ""
        if obj_type == "TABLE":
            if (obj_db == "" and obj_name == ""):
                obj_db = defn[col_ref.get("TABLE_SCHEMA",0)]
                obj_name = defn[col_ref.get("TABLE_NAME",1)]
            if (obj_db == defn[col_ref.get("TABLE_SCHEMA",0)] and \
                obj_name == defn[col_ref.get("TABLE_NAME",1)]):
                col_list.append(defn)
            else:
                create_str = _build_create_table(obj_db, obj_name,
                                                 old_engine,
                                                 col_list, col_ref)
                create_strings.append(create_str)
                obj_db = defn[col_ref.get("TABLE_SCHEMA",0)]
                obj_name = defn[col_ref.get("TABLE_NAME",1)]
                col_list = []
                col_list.append(defn)
            # check for end.
            if i+1 == stop:
                create_str = _build_create_table(obj_db, obj_name,
                                                 engine,
                                                 col_list, col_ref)
                create_strings.append(create_str)
        elif obj_type == "VIEW":
            create_str = "CREATE ALGORITHM=UNDEFINED DEFINER=%s " % \
                         defn[col_ref.get("DEFINER",2)]
            create_str += "SQL SECURITY %s " % \
                          defn[col_ref.get("SECURITY_TYPE",3)]
            create_str += "VIEW `%s`.`%s` AS " % \
                          (defn[col_ref.get("TABLE_SCHEMA",0)],
                           defn[col_ref.get("TABLE_NAME",1)])
            create_str += "%s; " % defn[col_ref.get("VIEW_DEFINITION",4)]
            create_strings.append(create_str)
        elif obj_type == "TRIGGER":
            create_str = "CREATE DEFINER=%s " % \
                         defn[col_ref.get("DEFINER",1)]
            create_str += "TRIGGER `%s`.`%s` %s %s " % \
                          (db, defn[col_ref.get("TRIGGER_NAME",0)],
                           defn[col_ref.get("ACTION_TIMING",6)],
                           defn[col_ref.get("EVENT_MANIPULATION",2)])
            create_str += "ON `%s`.`%s` " % \
                          (defn[col_ref.get("EVENT_OBJECT_SCHEMA",3)],
                           defn[col_ref.get("EVENT_OBJECT_TABLE",4)])
            create_str += "FOR EACH %s %s;" % \
                          (defn[col_ref.get("ACTION_ORIENTATION",5)],
                           defn[col_ref.get("ACTION_STATEMENT",7)])
            create_strings.append(create_str)
        elif obj_type in ("PROCEDURE", "FUNCTION"):
            create_str = "CREATE DEFINER=%s" % defn[col_ref.get("DEFINER",5)]
            create_str += " %s `%s`.`%s`(%s)" % \
                          (obj_type, db,
                           defn[col_ref.get("NAME",0)],
                           defn[col_ref.get("PARAM_LIST",6)])
            if obj_type == "FUNCTION":
                create_str += " RETURNS %s" % defn[col_ref.get("RETURNS",7)]
            create_str += " %s;" % defn[col_ref.get("BODY",8)]
            create_strings.append(create_str)
        elif obj_type == "EVENT":
            create_str = "CREATE EVENT `%s`.`%s` " % \
                         (db, defn[col_ref.get("NAME",0)])
            create_str += "ON SCHEDULE EVERY %s %s " % \
                          (defn[col_ref.get("INTERVAL_VALUE",5)],
                           defn[col_ref.get("INTERVAL_FIELD",6)])
            create_str += "STARTS '%s' " % defn[col_ref.get("STARTS",8)]
            ends_index = col_ref.get("ENDS",9)
            if len(defn[ends_index]) > 0 and \
               defn[ends_index].upper() != "NONE":
                create_str += "ENDS '%s' " % defn[ends_index]
            if defn[col_ref.get("ON_COMPLETION",11)] == "DROP":
                create_str += "ON COMPLETION NOT PRESERVE "
            if defn[col_ref.get("STATUS",10)] == "DISABLED":
                create_str += "DISABLE "
            create_str += "DO %s;" % defn[col_ref.get("BODY",2)]
            create_strings.append(create_str)
        elif obj_type == "GRANT":
            try:
                user, priv, db, tbl = defn[0:4]
            except:
                raise UtilError("Object data invalid: %s : %s" % \
                                     (obj_type, defn))
            if not tbl:
                tbl = "*"
            elif tbl.upper() == "NONE":
                tbl = "*"
            create_str = "GRANT %s ON %s.%s TO %s" % (priv, db, tbl, user)
            create_strings.append(create_str)
        elif obj_type == "RPL_COMMAND":
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
    create_strings = []
    skip_header = True
    obj_db = ""
    obj_name = ""
    col_list = []
    table_col_list = []
    stop = len(definitions)
    # Now the tricky part.
    for i in range(0,stop):
        if skip_header:
            skip_header = False
            continue
        defn = definitions[i]
        if obj_type == "TABLE":
            if (obj_db == "" and obj_name == ""):
                obj_db = defn[0]
                obj_name = defn[1]
            if (obj_db == defn[0] and obj_name == defn[1]):
                col_list.append((defn[4], defn[5]))
            else:
                table_col_list.append((obj_name, col_list))
                obj_db = defn[0]
                obj_name = defn[1]
                col_list = []
                col_list.append((defn[4], defn[5]))
                # check for end.
                if i+1 == stop-1:
                    table_col_list.append((obj_name, col_list))
    return table_col_list


def _build_insert_data(col_names, tbl_name, data):
    """Build simple INSERT statements for data.

    col_names[in]     A list of column names for the data
    tbl_name[in]      Table name
    data[in]          The data values

    Returns (string) the INSERT statement.
    """
    from mysql.utilities.common.sql_transform import to_sql
    
    return "INSERT INTO %s (" % tbl_name + ",".join(col_names) + \
           ") VALUES (" + ','.join(imap(to_sql, data))  + ");"


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
    object = obj_type.upper()
    if object == "TABLE":
        return options.get("skip_tables", False)
    elif object == "VIEW":
        return options.get("skip_views", False)
    elif object == "TRIGGER":
        return options.get("skip_triggers", False)
    elif object == "PROCEDURE":
        return options.get("skip_procs", False)
    elif object == "FUNCTION":
        return options.get("skip_funcs", False)
    elif object == "EVENT":
        return options.get("skip_events", False)
    elif object == "GRANT":
        return options.get("skip_grants", False)
    elif object == "CREATE_DB":
        return options.get("skip_create", False)
    elif object == "DATA":
        return options.get("skip_data", False)
    elif object == "BLOB":
        return options.get("skip_blobs", False)
    else:
        return False


def _exec_statements(statements, destination, format, options, dryrun=False):
    """Execute a list of SQL statements

    statements[in]    A list of SQL statements to execute
    destination[in]   A connection to the destination server
    format[in]        Format of import file
    options[in]       Option dictionary containing the --skip_* options
    dryrun[in]        If True, print the SQL statements and do not execute

    Returns (bool) - True if all execute, raises error if one fails
    """
    new_engine = options.get("new_engine", None)
    def_engine = options.get("def_engine", None)
    quiet = options.get("quiet", False)
    for statement in statements:
        if (new_engine is not None or def_engine is not None) and \
           statement.upper()[0:12] == "CREATE TABLE":
            i = statement.find(' ', 13)
            tbl_name = statement[13:i]
            statement = destination.substitute_engine(tbl_name, statement,
                                                      new_engine, def_engine,
                                                      quiet)
        try:
            if dryrun:
                print statement
            elif format != "sql" or not _skip_sql(statement, options):
                destination.exec_query(statement)
        # Here we capture any exception and raise UtilError to communicate to
        # the script/user. Since all util errors (exceptions) derive from
        # Exception, this is safe.
        except Exception, e:
            raise UtilError("Invalid statement:\n%s" % statement)
    return True


def _get_column_metadata(tbl_class, table_col_list):
    """Get the column metadata from the list of columns.

    tbl_class[in]      Class instance for table
    table_col_list[in] List of table columns for all tables
    """

    for tbl_col_def in table_col_list:
        if tbl_col_def[0] == tbl_class.tbl_name:
            tbl_class.get_column_metadata(tbl_col_def[1])
            return True
    return False


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

    from mysql.utilities.common.database import Database
    from mysql.utilities.common.options import check_engine_options
    from mysql.utilities.common.table import Table
    from mysql.utilities.common.server import connect_servers

    # Helper method to dig through the definitions for create statements
    def _process_definitions(statements, table_col_list, db_name):
        # First, get the SQL strings
        sql_strs = _build_create_objects(obj_type, db_name, definitions)
        statements.extend(sql_strs)
        # Now, save the column list
        col_list = _build_col_metadata(obj_type, definitions)
        if len(col_list) > 0:
            table_col_list.extend(col_list)

    def _process_data(tbl_name, statements, columns,
                      table_col_list, table_rows, skip_blobs):
        # if there is data here, build bulk inserts
        # First, create table reference, then call insert_rows()
        tbl = Table(destination, tbl_name)
        # Need to check to see if table exists!
        if tbl.exists():
            tbl.get_column_metadata()
            col_meta = True
        elif len(table_col_list) > 0:
            col_meta = _get_column_metadata(tbl, table_col_list)
        else:
            fix_cols = []
            fix_cols.append((tbl.tbl_name, columns))
            col_meta = _get_column_metadata(tbl, fix_cols)
        if not col_meta:
            raise UtilError("Cannot build bulk insert statements without "
                                 "the table definition.")
        ins_strs = tbl.make_bulk_insert(table_rows, tbl.db_name)
        if len(ins_strs[0]) > 0:
            statements.extend(ins_strs[0])
        if len(ins_strs[1]) > 0 and not skip_blobs:
            for update in ins_strs[1]:
                statements.append(update)

    # Gather options
    format = options.get("format", "sql")
    no_headers = options.get("no_headers", False)
    quiet = options.get("quiet", False)
    import_type = options.get("import_type", "definitions")
    single = options.get("single", True)
    dryrun = options.get("dryrun", False)
    do_drop = options.get("do_drop", False)
    skip_blobs = options.get("skip_blobs", False)

    # Attempt to connect to the destination server
    conn_options = {
        'quiet'     : quiet,
        'version'   : "5.1.30",
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
            str = "definitions and data"
        else:
            str = import_type
        print "# Importing %s from %s." % (str, file_name)

    # Setup variables we will need
    skip_header = not no_headers
    if format == "sql":
        skip_header = False
    get_db = True
    check_privileges = False
    db_name = None
    file = open(file_name)
    columns = []
    read_columns = False
    table_rows = []
    obj_type = ""
    definitions = []
    statements = []
    table_col_list = []
    tbl_name = ""
    skip_rpl = options.get("skip_rpl", False)

    # Read the file one object/definition group at a time
    for row in read_next(file, format):
        # Check for replication command
        if row[0] == "RPL_COMMAND":
            if not skip_rpl:
                statements.append(row[1])
            continue
        # If this is the first pass, get the database name from the file
        if get_db:
            if skip_header:
                skip_header = False
            else:
                db_name = _get_db(row)
                get_db = False
                if do_drop and import_type != "data":
                    statements.append("DROP DATABASE IF EXISTS `%s`;" % \
                                      db_name)
                if import_type != "data":
                    if not _skip_object("CREATE_DB", options):
                        statements.append("CREATE DATABASE `%s`;" % db_name)

        # This is the first time through the loop so we must
        # check user permissions on source for all databases
        if db_name is not None:
            dest_db = Database(destination, db_name)

            # Make a dictionary of the options
            access_options = options.copy()

            dest_db.check_write_access(dest_val['user'], dest_val['host'],
                                       access_options)
            
        # Now check to see if we want definitions, data, or both:
        if row[0] == "sql" or row[0] in _DEFINITION_LIST:
            if format != "sql" and len(row[1]) == 1:
                raise UtilError("Cannot read an import file generated with "
                                "--display=NAMES")

            if import_type in ("definitions", "both"):
                if format == "sql":
                    statements.append(row[1])
                else:
                    if obj_type == "":
                        obj_type = row[0]
                    if obj_type != row[0]:
                        if len(definitions) > 0:
                            _process_definitions(statements, table_col_list,
                                                 db_name)
                        obj_type = row[0]
                        definitions = []
                    if not _skip_object(row[0], options):
                        definitions.append(row[1])
        else:
            # see if there are any definitions to process
            if len(definitions) > 0:
                _process_definitions(statements, table_col_list, db_name)
                definitions = []

            if import_type in ("data", "both"):
                if _skip_object("DATA", options):
                    continue  # skip data
                elif format == "sql":
                    statements.append(row[1])
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
                    else:
                        if read_columns:
                            columns = row[1]
                            read_columns = False
                        else:
                            if not single:
                                table_rows.append(row[1])
                            else:
                                str = _build_insert_data(columns, tbl_name,
                                                         row[1])
                                statements.append(str)

    # Process remaining definitions                                 
    if len(definitions) > 0:
        _process_definitions(statements, table_col_list, db_name)
        definitions = []

    # Process remaining data rows
    if len(table_rows) > 0:
        _process_data(tbl_name, statements, columns,
                      table_col_list, table_rows, skip_blobs)
        table_rows = []

    # Now process the statements
    _exec_statements(statements, destination, format, options, dryrun)

    file.close()

    if not quiet:
        print "#...done."
    return True
