#!/usr/bin/env python
#
# Copyright (c) 2011, Oracle and/or its affiliates. All rights reserved.
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

"""
This file contains the methods for building SQL statements for definition
differences.
"""

from mysql.utilities.exception import UtilError, UtilDBError

_IGNORE_COLUMN = -1  # Ignore column in comparisons and transformations
_FORCE_COLUMN = -2   # Force column to be included in build phase

# Define column control symbols
_DROP_COL, _ADD_COL, _CHANGE_COL_TYPE, _CHANGE_COL_ORDER = range(0,4)

# List of database objects for enumeration
_DATABASE, _TABLE, _VIEW, _TRIG, _PROC, _FUNC, _EVENT, _GRANT = "DATABASE", \
    "TABLE", "VIEW", "TRIGGER", "PROCEDURE", "FUNCTION", "EVENT", "GRANT"

# Define database INFORMATION_SCHEMA column numbers
_DB_NAME, _DB_CHARSET, _DB_COLLATION, _DB_SQL_PATH = range(0,4)

# Define table INFORMATION_SCHEMA column numbers and index values
_COLUMN_ORDINAL_POSITION, _COLUMN_NAME, _COLUMN_TYPE, _COLUMN_IS_NULLABLE, \
    _COLUMN_DEFAULT, _COLUMN_EXTRA, _COLUMN_COMMENT, _COLUMN_KEY = range(0,8)

_TABLE_DEF, _COLUMN_DEF, _PART_DEF = range(0,3)
_TABLE_DB, _TABLE_NAME, _TABLE_ENGINE, _TABLE_AUTO_INCREMENT, \
    _TABLE_AVG_ROW_LENGTH, _TABLE_CHECKSUM, _TABLE_COLLATION, _TABLE_COMMENT, \
    _TABLE_ROW_FORMAT, _TABLE_CREATE_OPTIONS = range(0,10)

# Define view INFORMATION_SCHEMA column numbers
_VIEW_DB, _VIEW_NAME, _VIEW_BODY, _VIEW_CHECK, _VIEW_DEFINER, \
    _VIEW_SECURITY = range(0,6)

# Define trigger INFORMATION_SCHEMA column numbers
_TRIGGER_DB, _TRIGGER_NAME, _TRIGGER_EVENT, _TRIGGER_TABLE, _TRIGGER_BODY, \
    _TRIGGER_TIME,  _TRIGGER_DEFINER = range(0,7)

# Define routine INFORMATION_SCHEMA column numbers
_ROUTINE_DB, _ROUTINE_NAME, _ROUTINE_BODY, _ROUTINE_SQL_DATA_ACCESS, \
    _ROUTINE_SECURITY_TYPE, _ROUTINE_COMMENT, _ROUTINE_DEFINER, \
    _ROUTINE_PARAMS, _ROUTINE_RETURNS, _ROUTINE_IS_DETERMINISTIC = range(0,10)

# Define event INFORMATION_SCHEMA column numbers
_EVENT_DB, _EVENT_NAME, _EVENT_DEFINER, _EVENT_BODY, _EVENT_TYPE, \
    _EVENT_INTERVAL_FIELD, _EVENT_INTERVAL_VALUE, _EVENT_STATUS, \
    _EVENT_ON_COMPLETION, _EVENT_STARTS, _EVENT_ENDS = range(0,11)

# Get the constraints but ignore primary keys
_CONSTRAINT_QUERY = """
  SELECT CONSTRAINT_NAME, CONSTRAINT_TYPE
  FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS
  WHERE TABLE_SCHEMA = '%(db)s' AND TABLE_NAME = '%(name)s'
        and CONSTRAINT_TYPE != 'PRIMARY KEY'
        and CONSTRAINT_TYPE != 'UNIQUE'
"""

def to_sql(obj):
    """Convert a value to a suitable SQL value placing quotes where needed.

    obj[in]           object (value) to convert

    Returns (string) converted value
    """
    from mysql.connector.conversion import MySQLConverter
    return MySQLConverter().quote(obj)


def build_pkey_where_clause(table, row):
    """Build the WHERE clause based on the primary keys
    
    table[in]              instance of Table class for table
    row[in]                row of data
    
    Returns string - WHERE clause or "" if no keys
    """
    where_str = ""
    pkeys = table.get_primary_index()
    if len(pkeys) > 0:
        col_names = table.get_col_names()
        where_str += "WHERE "
        for pkey in pkeys:
            key_col = pkey[0]                         # get the column name
            col_data = row[col_names.index(key_col)]  # get column value
            where_str += "%s = %s" % (key_col, to_sql(col_data))
    
    return where_str


def build_set_clauses(table, table_cols, dest_row, src_row):
    """Build the SET clauses for an UPDATE statement
   
    table[in]              instance of Table class for table
    dest_row[in]           row of data for destination (to be changed)
    src_row[in]            row of data for source (to be changed to)
    
    Returns string - WHERE clause or "" if no keys
    """
    col_metadata = table.get_column_metadata()
    # do SETs
    set_str = ""
    do_comma = False
    for col_idx in range(0,len(table_cols)):
        if dest_row[col_idx] != src_row[col_idx]:
            # do comma
            if do_comma:
                set_str += ", "
            else:
                set_str = "SET "
                do_comma = True
            # Check for NULL for non-text fields that have no value in new row
            if len(src_row[col_idx]) == 0 \
               and not col_metadata[col_idx]['is_text']:
                set_str += "%s = %s" % (table_cols[col_idx], "NULL")
            else:
                set_str += "%s = %s" % (table_cols[col_idx],
                                       to_sql(src_row[col_idx]))

    return set_str


def transform_data(destination, source, operation, rows):
    """Transform data for tables.
    
    This method will generate INSERT, UPDATE, and DELETE statements for
    transforming data found to differ among tables.
    
    destination[in]    Table class instance of the destination
    source[in]         Table class instance of the source
    operation[in]      specify if INSERT, UPDATE, or DELETE
    rows[in]           rows for transformation as follows:
                       UPDATE - tuple (old, new)
                       DELETE - list to delete
                       INSERT - list to insert
    
    Returns list - SQL statement(s) for transforming the data or a warning
                   if the columns differ between the tables
    """
    statements = []
    dest_cols = destination.get_col_names()
    src_cols = source.get_col_names()
    
    # We cannot do the data changes if the columns are different in the
    # destination and source!
    if dest_cols != src_cols:
        return ["WARNING: Cannot generate SQL UPDATE commands for " \
                "tables whose definitions are different. Check the " \
                "table definitions for changes."]
    data_op = operation.upper()
    if data_op == "INSERT":
        for row in rows:
            formatted_row = []
            for col in row:
                formatted_row.append(to_sql(col))
            statements.append("INSERT INTO %s (%s) VALUES(%s);" %
                              (destination.table, ', '.join(dest_cols),
                               ', '.join(formatted_row)))
    elif data_op == "UPDATE":
        for i in range(0,len(rows[0])):
            row1 = rows[0][i]
            row2 = rows[1][i]
            sql_str = "UPDATE %s" % destination.table
            sql_str += " %s" % build_set_clauses(source, src_cols, row1, row2)
            sql_str += " %s" % build_pkey_where_clause(source, row2)
            statements.append("%s;" % sql_str)                
    elif data_op == "DELETE":
        for row in rows:
            sql_str = "DELETE FROM %s " % destination.table
            sql_str += build_pkey_where_clause(source, row)
            statements.append("%s;" % sql_str)
    else:
        raise UtilError("Unknown data transformation option: %s." % data_op)
    
    return statements


class SQLTransformer(object):
    """
    The SQLTransformer class provides a mechanism for generating SQL statments
    for conforming an object to another for a specific database. For example,
    it will generate the ALTER statement(s) for transforming a table definition
    as well as the UPDATE statement(s) for transforming a row in the table.
    
    Note: This class is designed to work with the output of the Database class
          method get_db_objects with full INFORMATION_SCHEMA columns for the
          object definition.
          
    This class contains transformation methods for the objects supported.
    Each object's ALTER statement is generated using the following steps.
    Note: tables are a bit different due to their many parts but still follow
    the general layout.
    
    - a list of dictionaries structure is built to contain the parts of the
      statement where each dictionary has fields for format ('fmt') that
      contains the string format for building the value, column ('col') for
      containing the column number for the value, and value ('val') which
      is for holding the value.
    - any special formatting, conditionals, etc. concerning the fields is
      processed. In some cases this means filling the 'val' for the field.
    - the structure values are filled
    - the statement is build by concatenating those fields where 'val' is
      not empty.
      
    You can tell the fill values phase to ignore filling the value by using
    _IGNORE_COLUMN as the column number. 
      
    You can tell the build phase to include the field (say after special
    processing has filled the value) by using _FORCE_COLUMN as the column
    number.
    """

    def __init__(self, destination_db, source_db, destination,
                 source, obj_type, verbosity):
        """Constructor
        
        destination_db[in] destination Database instance
        source_db[in]      source Database instance
        destination[in]    the original object definition or data
        source[in]         the source object definition or data
        obj_type[in]       type of object
        verbosity[in]      verbosity level
        
        """
        self.destination_db = destination_db
        self.source_db = source_db
        self.destination = destination
        self.source = source
        self.obj_type = obj_type.upper()
        self.verbosity = verbosity


    def transform_definition(self):
        """Transform an object definition

        This method will transform an object definition to match the source
        configuration. It returns the appropriate SQL statement(s) to
        transform the object or None if no transformation is needed.
        
        Note: the method will throw an exception if the transformation cannot
              be completed or there is another error during processing

        Returns list - SQL statement(s) for transforming the object
        """
        trans_method = {
            _DATABASE : self._transform_database,
            _TABLE    : self._transform_table,
            _VIEW     : self._transform_view,
            _TRIG     : self._transform_trigger,
            _PROC     : self._transform_routine,
            _FUNC     : self._transform_routine,
            _EVENT    : self._transform_event,
        }
        try:
            return trans_method[self.obj_type]()
        except IndexError:
            raise UtilDBError("Unknown object type '%s' for transformation." %
                              self.obj_type)


    def _transform_database(self):
        """Transform a database definition

        This method will transform a database definition to match the source
        configuration. It returns the ALTER DATABASE SQL statement to
        transform the object or None if no transformation is needed.
        
        Returns list - ALTER DATABASE statement for transforming the database
        """
        statements = []

        # build a list of the parts
        statement_parts = [
            # preamble
            { 'fmt' : "%s", 'col' : _IGNORE_COLUMN, 'val' : "ALTER DATABASE" },
            # object name
            { 'fmt' : " %s", 'col' : _IGNORE_COLUMN,
              'val' : self.destination[_DB_NAME] },
            # charset
            { 'fmt' : " CHARACTER SET %s", 'col' : _DB_CHARSET, 'val' : "" },
            # collation
            { 'fmt' : " COLLATE = %s", 'col' : _DB_COLLATION, 'val' : "" },
        ]
            
        # if no changes, return None
        if not self._fill_values(statement_parts, False):
            return None
        
        sql_stmt = "%s;" % self._build_statement(statement_parts)
        statements.append(sql_stmt)
        
        return statements
    

    def _convert_option_values(self, option_values):
        """Convert a list of option=value to a list of names and name, value
        pairs.
        
        This method takes a list like the following where each element is a
        name=value string:
        
        (a=1, b=3, c=5, d=4)
        
        turning into a tuple containing a list of names and a list of
        name,value pairs as follows:
        
        ((a,b,c,d), ((a,1),(b,3),(c,5),(d,4)))
        
        Value pairs that do not have a value are ignored. For example,
        'a=3, b, c=2' will ignore 'b' but return a and c.
        
        option_values[in]  list of name=value strings 
    
        Returns tuple - (list of names, list of (name, value))
        """
        names = []
        name_values = []
        for value_pair in option_values:
            name_value = value_pair.split('=')
            # Ignore any value pairs that do not have a value
            if len(name_value[0]) > 0:
                names.append(name_value[0].upper())
                name_values.append(name_value)
        return (names, name_values)
    
    
    def _find_value(self, name, name_values):
        """Find a value for a name in a list of tuple (name, value)
        
        name[in]           name of pair
        name_values[in]    list of tuples
        
        Returns string - value at index of match or None
        """
        name = name.upper()
        for item in name_values:
            if item[0].upper() == name:
                try:
                    return item[1]
                except IndexError:
                    return None
                
        return None

    
    def _parse_table_options(self, destination, source):
        """Parse the table options into a list and compare.
        
        This method returns a comma-separated list of table options that
        differ from the destination to the source.

        destination[in]    the original object definition or data
        source[in]         the source object definition or data

        Returns string - comma-separated values for table options that differ
                         or None if options are found in the destination that
                         are not in the source. These, we do not know how
                         to remove or turn off without extensive, specialized
                         code.
        """
        from mysql.utilities.common.dbcompare import get_common_lists
        
        # Here we have a comma-separated list of options in the form
        # name=value. To determine the inclusion/exclusion lists, we
        # must compare on names only so we make a list for each of only
        # the names.
        dest_opts_names = []
        dest_opts = [item.strip() for item in destination.split(',')]
        dest_opts_names, dest_opts_val = self._convert_option_values(dest_opts)
        dest_opts_names.sort()
        src_opts = [item.strip() for item in source.split(',')]
        src_opts_names, src_opts_val = self._convert_option_values(src_opts)
        src_opts_names.sort()
        in_both, in_dest_not_src, in_src_not_dest = \
                    get_common_lists(dest_opts_names, src_opts_names)
                
        # Whoops! There are things set in the destination that aren't in the
        # source so we don't know if these are Ok or if we need to do
        # something special.
        if len(in_dest_not_src) > 0:
            return None
        
        changes = []
        # Now check for changes for both
        for name in in_both:
            dest_val = self._find_value(name, dest_opts_val)
            src_val = self._find_value(name, src_opts_val)
            if dest_val is not None and dest_val != src_val:
                changes.append("%s=%s" % (name.upper(), src_val))
               
        # Get values for those not in destination
        for item in in_src_not_dest:
            val = self._find_value(item, src_opts_val)
            if val is not None:
                changes.append("%s=%s" % (item.upper(), val))
        
        return ', '.join(changes)
    

    def _get_table_defns(self, destination, source):
        """Get the transform fpr the general options for a table
        
        This method creates an ALTER TABLE statement for table definitions
        that differ. The items covered include only those options described
        in the reference manual as table_options and include the following:
        
            engine, auto_increment, avg_row_count, checksum, collation,
            comment, and create options
        
        destination[in]    the original object definition or data
        source[in]         the source object definition or data

        Returns string - ALTER TABLE clause or None if no transform needed
        """
        changes = self._check_columns([_TABLE_COMMENT], destination, source)
        
        # build a list of the parts
        statement_parts = [
            # rename
            { 'fmt' : "RENAME TO %s.%s \n", 'col' : _IGNORE_COLUMN, 'val' : "" },
            # engine
            { 'fmt' : "ENGINE=%s", 'col' : _TABLE_ENGINE, 'val' : "" },
            # auto increment
            { 'fmt' : "AUTO_INCREMENT=%s", 'col' : _TABLE_AUTO_INCREMENT,
              'val' : "" },
            # collation
            { 'fmt' : "COLLATE=%s", 'col' : _TABLE_COLLATION, 'val' : "" },
            # comment - always include to ensure comments can be removed
            { 'fmt' : "COMMENT='%s'", 'col' : _IGNORE_COLUMN,
              'val' : source[_TABLE_COMMENT] }, 
            # create options - will be completed later
            { 'fmt' : "%s", 'col' : _IGNORE_COLUMN, 'val' : "" },
        ]
            
        dest_create = destination[_TABLE_CREATE_OPTIONS]
        src_create = source[_TABLE_CREATE_OPTIONS]
        if dest_create != src_create:
            create = statement_parts[5]
            opt_val = self._parse_table_options(dest_create, src_create)
            if opt_val is None:
                return "# WARNING: the destination table contains options that " + \
                       "are not in the source.\n# Cannot generate ALTER " + \
                       "statement."
            else:
                create['val'] = "%s" % opt_val
                changes = True
                
        # if no changes, return None
        if not changes and not self._fill_values(statement_parts, False,
                                                 destination, source):
            return None
        
        # We need to check the comment again and include it if source == ''
        if self._check_columns([_TABLE_COMMENT], destination, source) and \
           source[_TABLE_COMMENT] == '':
            statement_parts[4]['col'] = _FORCE_COLUMN

        # Check for rename
        if destination[_TABLE_NAME] != source[_TABLE_NAME]:
            statement_parts[0]['val'] = (source[_DB_NAME], source[_TABLE_NAME])

        # check and set commas
        do_comma = False
        for part in statement_parts:
            if do_comma:
                part['fmt'] = ', ' + part['fmt']
            elif part['col'] == _FORCE_COLUMN or part['val'] != '':
                do_comma = True
                
        return self._build_statement(statement_parts)


    def _get_column_format(self, col_data):
        """Build the column data type format string
        
        col_data[in]       the row containing the column definition
        
        Retuns string - column data type format
        """
        if col_data is None:
            return ""
        col_fmt = "%(type)s%(null)s%(default)s%(extra)s%(comment)s"
        values = {
            'type'    : col_data[_COLUMN_TYPE],
            'null'    : "",
            'default' : "",
            'extra'   : "",
            'comment' : "",
        }
        if col_data[_COLUMN_IS_NULLABLE].upper() == "NO":
            values['null'] = " NOT NULL"
        else:
            values['null'] = " NULL"
        if col_data[_COLUMN_DEFAULT] is not None and \
           len(col_data[_COLUMN_DEFAULT]) > 0:
            def_val = col_data[_COLUMN_DEFAULT]
            # add quotes if needed
            if def_val.upper() != "CURRENT_TIMESTAMP":
                def_val = to_sql(def_val)
            values['default'] = " DEFAULT %s" % def_val
        if len(col_data[_COLUMN_EXTRA]) > 0:
            if col_data[_COLUMN_EXTRA].upper() != "AUTO_INCREMENT":
                values['extra'] = " %s" % col_data[_COLUMN_EXTRA]
        if len(col_data[_COLUMN_COMMENT]) > 0:
            values['comment'] = " COMMENT '%s'" % col_data[_COLUMN_COMMENT]
        return col_fmt % values


    def _get_column_position(self, destination_def, source_def,
                             destination, source, drop_cols, add_cols):
        """Get the column position in the list
        
        destination_def[in] destination column definition
        source_def[in]      source column definition
        destination[in]     destination column definitions
        source[in]          source column definitions
        drop_cols[in]       list of columns to be dropped - used to
                            calculate position of existing columns by
                            eliminating those cols in destination that will be
                            dropped
        add_cols[in]        list of columns to be added - used to
                            calculate position of existing columns by
                            eliminating those cols in destination that will be
                            dropped
       
        Returns string - 'BEFORE' or 'AFTER' for column position or "" if
                         position cannot be determined (add or drop column)
        """        

        # Converting ordinal position to index positions: 
        #
        #    - ordinal positions start counting at 1
        #    - list indexes start at 0
        #        
        # So if you want to find the column that is one less than the ordinal
        # position of the current column, you must subtract 1 then subtract 1
        # again to convert it to the list index.

        dest_loc_idx = None
        src_loc_idx = int(source_def[_COLUMN_ORDINAL_POSITION]) - 1
        if destination_def is not None:
            dest_loc_idx = int(destination_def[_COLUMN_ORDINAL_POSITION]) - 1
            
        # Check to see if previous column has been dropped. If it has,
        # don't include the BEFORE|AFTER - it will be ordered correctly.
        if dest_loc_idx is not None and dest_loc_idx-1 >= 0 and \
           destination[dest_loc_idx-1][_COLUMN_NAME] in drop_cols:
            return ""
        
        # Check to see if previous column has been added. If it has,
        # don't include the BEFORE|AFTER - it will be ordered correctly.
        if src_loc_idx-1 >= 0 and source[src_loc_idx-1][_COLUMN_NAME] in add_cols:
            return ""

        # compare ordinal position - if not the same find where it goes
        if dest_loc_idx is None or dest_loc_idx != src_loc_idx:
            if src_loc_idx == 0:
                return " FIRST"
            for col in source:
                if src_loc_idx == int(col[_COLUMN_ORDINAL_POSITION]):
                    return " AFTER %s" % col[_COLUMN_NAME]
        return ""


    def _find_column(self, name, columns):
        """Find a column in a list by name
        
        name[in]           name of the column
        columns[in]        list of column definitions
                           
        Returns - column definition or None if column not found
        """
        for col_def in columns:
            if name == col_def[_COLUMN_NAME]:
                return col_def                
        return None


    def _get_column_change(self, column, destination, source,
                           drop_cols, add_cols):
        """Identify if column differs and return the changes
        
        column[in]         column name and operation type
        destination[in]    column definitions for destination
        source[in]         column definitions for source
        drop_cols[in]      list of columns to be dropped - used to
                           calculate position of existing columns
        add_cols[in]       list of columns to be added - used to
                           calculate position of existing columns
        
        Returns string - new changes for column or ""
        """
        operation = column[1]
        
        # Get column from the origins
        destination_def = self._find_column(column[0], destination)
        source_def = self._find_column(column[0], source)

        # Here we look for columns that are set for checking the order but
        # the extra data (null, etc.) is different. So we change it to
        # a type change instead. Exclude key column in compare.
        if operation == _CHANGE_COL_ORDER and \
           destination_def[:_COLUMN_KEY] != source_def[:_COLUMN_KEY]:
            operation = _CHANGE_COL_TYPE

        # Check for drop column 
        if operation == _DROP_COL:
            colstr = "  DROP COLUMN %s" % destination_def[_COLUMN_NAME]
        else:
            # Determine position and get the type format string
            col_pos = self._get_column_position(destination_def, source_def,
                                                destination, source,
                                                drop_cols, add_cols)
            col_fmt = self._get_column_format(source_def)

            # Check for order changes
            if operation == _CHANGE_COL_ORDER:
                if len(col_pos) > 0:
                    colstr = "  CHANGE COLUMN %s %s %s%s" % \
                             (source_def[_COLUMN_NAME],
                              source_def[_COLUMN_NAME],
                              col_fmt, col_pos)
                else:
                    colstr = ""  # No change needed here
            # Add or change column
            elif operation == _ADD_COL:
                colstr = "  ADD COLUMN %s %s%s" % (source_def[_COLUMN_NAME],
                                                   col_fmt, col_pos)
            else: # must be change
                colstr = "  CHANGE COLUMN %s %s " % \
                         (destination_def[_COLUMN_NAME],
                          destination_def[_COLUMN_NAME])
                colstr += "%s%s" % (col_fmt, col_pos)
                
        return colstr


    def _get_columns(self, destination, source):
        """Get the column definition changes
        
        This method loops through the columns and if different builds ALTER
        statments for transforming the columns of the destination table to the
        source table.
        
        destination[in]    the original object definition or data
        source[in]         the source object definition or data
        
        Returns string - ALTER statement or None if no column differences.
        """
        from mysql.utilities.common.dbcompare import get_common_lists
        
        drop_clauses = []
        add_clauses = []

        # Build lists with minimal matching data (column name and type) for
        # destination and source. Then do the compare. Result is as follows:
        #
        #   - those in both (name, type) will need to be checked for order
        #     of cols to generate CHANGE COLUMN x x <type> BEFORE|AFTER x
        #   - those in destination but not source will be dropped unless the
        #     name appears in source but not destination to generate
        #     DROP COULMN x
        #   - those in destination but not source where the name does appear in
        #     source is a change of type to generate CHANGE COLUMN x x <type>
        #   - those in source but not destination that don't match by name in
        #     destination but not source are new columns to generate
        #     ADD COLUMN x <type>
        #   - those columns that match on both name and type need to be
        #     checked for order changes to generate the
        #     CHANGE COLUMN x BEFORE|AFTER
        #   - we need to check those that the column order changes to see
        #     if they are actually extra col def changes

        dest_min = [item[1:3] for item in destination] # name, type
        src_min = [item[1:3] for item in source] # name, type
        
        # find matches by name + type
        both_min, dest_src_min, src_dest_min = get_common_lists(dest_min,
                                                                src_min)       
        dest_src_names = [item[0] for item in dest_min] # only name
        src_dest_names = [item[0] for item in src_min] # only name
        
        # find matches by name only
        both_names = [item[0] for item in both_min]   # only name
        both_check, dest_drop, src_new = get_common_lists(dest_src_names,
                                                          src_dest_names)
         
        # find matches by name but not type
        both_change_type = list(set(both_check) - set(both_names))
        
        # remove type changes and form list for checking order
        both_change_order = list(set(both_names) - set(both_change_type))
        
        column_drops = []
        column_changes = [] # a list of tuples in form (col_name, operation)

        # Form drops
        for col in dest_drop:
            column_drops.append((col, _DROP_COL))
            
        # Build the drop statements
        for col in column_drops:
            change_str = self._get_column_change(col, destination, source,
                                                 dest_drop, src_new)
            if len(change_str) > 0:
                # if first is specified, push to front of list
                if change_str.endswith(" FIRST"):
                    drop_clauses.insert(0, change_str)
                else:
                    drop_clauses.append(change_str)
   
        # Form change type
        for col in both_change_type:
            column_changes.append((col, _CHANGE_COL_TYPE))
        
        # Form add column
        for col in src_new:
            column_changes.append((col, _ADD_COL))
            
        # Form change order
        for col in both_change_order:
            column_changes.append((col, _CHANGE_COL_ORDER))
        
        # Build the add/change statements
        for col in column_changes:
            change_str = self._get_column_change(col, destination, source,
                                                 dest_drop, src_new)
            if len(change_str) > 0:
                # if first is specified, push to front of list
                if change_str.endswith(" FIRST"):
                    add_clauses.insert(0, change_str)
                else:
                    add_clauses.append(change_str)
        
        return (drop_clauses, add_clauses)
    

    def _get_foreign_keys(self, src_db, src_name, dest_db, dest_name):
        """Get the foreign key constraints
        
        This method returns the table foreign keys via ALTER TABLE clauses
        gathered from the Table class methods.
        
        src_db[in]         database name for source table
        src_name[in]       table name for source table
        dest_db[in]        database name for destination table
        dest_name[in]      table name for destination table

        Returns tuple - (drop, add/changes)
        """
        from mysql.utilities.common.dbcompare import get_common_lists
        from mysql.utilities.common.table import Table

        # Get the Table instances
        self.dest_tbl = Table(self.destination_db.source, "%s.%s" %
                              (dest_db, dest_name))
        self.src_tbl = Table(self.source_db.source, "%s.%s" %
                             (src_db, src_name))
        
        drop_constraints = []
        add_constraints = []
        
        # Now we do foreign keys
        dest_fkeys = self.dest_tbl.get_tbl_foreign_keys()
        src_fkeys = self.src_tbl.get_tbl_foreign_keys()
        
        # Now we determine the foreign keys we need to add and those to drop
        both, drop_rows, add_rows = get_common_lists(dest_fkeys, src_fkeys)
        
        # Generate DROP foreign key clauses
        for fkey in drop_rows:
            drop_constraints.append("  DROP FOREIGN KEY %s" % fkey[0])
            #if fkey[0] not in drop_idx_recorded:
            #    constraints.append("  DROP INDEX %s" % fkey[0])
       
        # Generate Add foreign key clauses
        clause_fmt = "ADD CONSTRAINT %s FOREIGN KEY(%s) REFERENCES " + \
                     "`%s`.`%s`(%s)"
        for fkey in add_rows:
            add_constraints.append(clause_fmt % fkey)

        return (drop_constraints, add_constraints)


    def _get_index_sql_clauses(self, rows):
        """Return the ALTER TABLE index clauses for the table.
        
        This method returns the SQL index clauses for use in ALTER or CREATE
        TABLE commands for defining the indexes for the table.
        
        rows[in]           result set of index definitions

        Returns list - list of SQL index clause statements or
                       [] if no indexes
        """
        alter_stmt = None
        index_clauses = []

        if rows != []:
            pri_key_cols = []
            unique_indexes = []
            unique_key_cols = []
            unique_name = None
            unique_method = None
            unique_setting = None
            for key in rows:
                if key[2] == 'PRIMARY':
                    pri_key_cols.append(key[4])
                else:
                    if unique_name is None:
                        unique_name = key[2]
                        unique_method = key[10]
                        unique_setting = key[1]
                        unique_key_cols.append(key[4])
                    elif unique_name == key[2]:
                        unique_key_cols.append(key[4])
                    else:
                        unique_indexes.append((unique_name, unique_method,
                                               unique_setting, 
                                               unique_key_cols))
                        unique_key_cols = []
                        unique_name = key[2]
                        unique_method = key[10]
                        unique_setting = key[1]
                        unique_key_cols.append(key[4])
                        
            # add the last one
            if unique_name is not None:
                unique_indexes.append((unique_name, unique_method,
                                       unique_setting,
                                       unique_key_cols))

            # Build SQL statement clause
            if len(pri_key_cols) > 0:
                index_clauses.append("  ADD PRIMARY KEY(%s)" % \
                                     ','.join(pri_key_cols))
            if len(unique_indexes) > 0:
                for idx in unique_indexes:
                    create_idx = "  ADD "
                    if int(idx[2]) != 1:
                        create_idx += "UNIQUE "
                    if idx[1] == "FULLTEXT":
                        create_idx += "FULLTEXT "
                    if (idx[1] == "RTREE"):
                        using = " USING %s" % (idx[1])
                    else:
                        using = ""
                    create_idx += "INDEX %s%s (%s)" % \
                                  (idx[0], using,
                                   ','.join(idx[3]))
                    index_clauses.append(create_idx)
                    
        return index_clauses


    def _get_indexes(self, src_db, src_name, dest_db, dest_name):
        """Get the index constraints
        
        This method returns the table primary keys, and other indexes via
        ALTER TABLE clauses gathered from the Table class methods.
        
        src_db[in]         database name for source table
        src_name[in]       table name for source table
        dest_db[in]        database name for destination table
        dest_name[in]      table name for destination table

        Returns tuple - (drop, add/changes)
        """
        from mysql.utilities.common.dbcompare import get_common_lists
        from mysql.utilities.common.table import Table

        # Get the Table instances
        self.dest_tbl = Table(self.destination_db.source, "%s.%s" %
                             (dest_db, dest_name))
        self.src_tbl = Table(self.source_db.source, "%s.%s" %
                             (src_db, src_name))
        
        drop_indexes = []
        add_indexes = []
        
        # Get the list of indexes
        dest_idx = self.dest_tbl.get_tbl_indexes()
        src_idx = self.src_tbl.get_tbl_indexes()
        
        # Now we determine the indexes we need to add and those to drop
        both, drop_idx, add_idx = get_common_lists(dest_idx, src_idx)
        
        # Generate DROP index clauses
        drop_idx_recorded = [] # used to avoid duplicate index drops
        for index in drop_idx:
            if index[2] == "PRIMARY":
                drop_indexes.append("  DROP PRIMARY KEY")
            elif index[2] not in drop_idx_recorded:
                drop_indexes.append("  DROP INDEX %s" % index[2])
                drop_idx_recorded.append(index[2])
        
        # Generate ADD index clauses
        if len(add_idx) > 0:
            add_indexes.extend(self._get_index_sql_clauses(add_idx))
                    
        return (drop_indexes, add_indexes)


    def _check_for_partitions(self, destination_row, source_row):
        """Determine if there are transformations involving partitions
        
        This method returns TRUE if the destination and source differ in
        partitioning configurations
        
        destination_row[in] the original object definition or data
        source_row[in]      the source object definition or data

        Returns bool - True = differences found, False = no differences
        """
        #
        # TODO: Complete this operation with a new worklog.
        #       This release does not support transformation of partitions.
        
        part_changes_found = False
        if len(destination_row) != len(source_row):
            part_changes_found = True
        elif len(destination_row) == 0:
            return None
        elif len(destination_row) == 1:
            if not (destination_row[0][3] == None and source_row[0][3] == None):
                part_changes_found = True            
        else:
            part_stop = len(destination_row)
            row_stop = len(destination_row[0])
            for i in range(0,part_stop):
                for j in range(0,row_stop):
                    if destination_row[i][j] != source_row[i][j]:
                        part_changes_found = True
                        break
        return part_changes_found


    def _transform_table(self):
        """Transform a table definition

        This method will transform a table definition to match the source
        configuration. It returns the ALTER TABLE SQL statement to
        transform the object or None if no transformation is needed.
                    
        Note: The incoming lists contain a tuple defined as:
              (table definitions, columns, partitions, constraints)
              for destination and source.

        Returns list - ALTER TABLE statements for transforming the table
        """        
        statements = []

        # build a list of the parts
        statement_parts = [
            # preamble
            { 'fmt' : "%s", 'col' : _IGNORE_COLUMN, 'val' : "ALTER TABLE" },
            # object name
            { 'fmt' : " %s.%s", 'col' : _IGNORE_COLUMN,
              'val' : (self.destination[_TABLE_DEF][_TABLE_DB],
                       self.destination[_TABLE_DEF][_TABLE_NAME]) },
            # alter clauses - will be completed later
            { 'fmt' : " \n%s", 'col' : _IGNORE_COLUMN, 'val' : "" },
        ]
        
        # Collect a list of all of the ALTER clauses. Order is important in
        # building an ALTER TABLE statement. For safety (and correct execution)
        # we must order the clauses as follows:
        #
        #  - drop foreign key constraints
        #  - drop indexes
        #  - drop columns
        #  - add/change columns
        #  - add/change indexes
        #  - add/change foreign keys
        #  - general table changes
        #
        #  Note: partition changes not supported by this release

        src_db_name = self.source[_TABLE_DEF][_TABLE_DB]
        src_tbl_name = self.source[_TABLE_DEF][_TABLE_NAME]
        dest_db_name = self.destination[_TABLE_DEF][_TABLE_DB]
        dest_tbl_name = self.destination[_TABLE_DEF][_TABLE_NAME]
        
        # For foreign key changes, we need two collections: drop statements,
        # add and change statements. Method returns tuple of (drop, add).
        fkeys = self._get_foreign_keys(src_db_name, src_tbl_name,
                                       dest_db_name, dest_tbl_name)

        # For index changes, we need two collections: drop statements, add and
        # change statements. Method returns tuple of (drop, add).
        indexes = self._get_indexes(src_db_name, src_tbl_name,
                                    dest_db_name, dest_tbl_name)


        # For column changes, we need two collections: drop statements, add and
        # change statements. Method returns tuple of (drop, add/change).
        columns = self._get_columns(self.destination[_COLUMN_DEF],
                                    self.source[_COLUMN_DEF])
            
        # Now add drops then add/changes
        for i in range(0,2):
            statements.extend(fkeys[i])
            statements.extend(indexes[i])
            statements.extend(columns[i])
        
        # General definition returns a single string of the option changes
        gen_defn = self._get_table_defns(self.destination[_TABLE_DEF],
                                         self.source[_TABLE_DEF])
        
        if gen_defn is not None:
            statements.append(gen_defn)
            
        # Form the SQL command.
        statement_parts[2]['val'] = ', \n'.join(statements)

        sql_stmts = ["%s;" % self._build_statement(statement_parts)]

        # Currently, we check partitions last because this code will
        # generate a warning message. Later once this code it complete,
        # it can be moved where it belongs in the order of creation of
        # the ALTER TABLE statement
        if self._check_for_partitions(self.destination[_PART_DEF],
                                      self.source[_PART_DEF]):
            sql_stmts.append("# WARNING: Partition transformation is not "
                             "supported in this release.\n# Please check "
                             "the table definitions for partition changes.")
            
        return sql_stmts

    
    def _transform_view(self):
        """Transform a view definition

        This method will transform a view definition to match the source
        configuration. It returns the CREATE OR ALTER VIEW SQL statement to
        transform the object or None if no transformation is needed.
                
        Returns list - ALTER VIEW statement for transforming the view
        """
        statements = []
        
        # check for create
        do_create = self._check_columns([_VIEW_CHECK])

        # build a list of the parts
        statement_parts = [
            # preamble
            { 'fmt' : "%s", 'col' : _IGNORE_COLUMN,
              'val' : "CREATE" if do_create else "ALTER" },
            # definer
            { 'fmt' : " DEFINER=%s", 'col' : _VIEW_DEFINER, 'val' : "" },
            # security
            { 'fmt' : " SQL SECURITY %s", 'col' : _VIEW_SECURITY, 'val' : "" },
            # object type and name
            { 'fmt' : " VIEW %s.%s", 'col' : _IGNORE_COLUMN,
              'val' : (self.destination[_VIEW_DB],
                       self.destination[_VIEW_NAME]) },
            # definition
            { 'fmt' : " AS \n  %s", 'col' : _VIEW_BODY, 'val' : "" },
            # check option (will be updated later)
            { 'fmt' : "%s", 'col' : _IGNORE_COLUMN, 'val' : "" }
        ]
        
        changes = False
        # view check option is special - we have to handle that separately
        if self.destination[_VIEW_CHECK] != self.source[_VIEW_CHECK]:
            if self.source[_VIEW_CHECK].upper() != 'NONE':
                check = statement_parts[5]
                check['val'] = " WITH %s CHECK OPTION" % \
                               self.source[_VIEW_CHECK]
            changes = True
       
        # if no changes, return None
        if not changes and not self._fill_values(statement_parts, do_create):
            return None

        # check to see if definer or security or check option have changed and
        # if so add definition (always needed if these change)
        if self._check_columns([_VIEW_DEFINER, _VIEW_SECURITY, _VIEW_CHECK]):
            statement_parts[4]['val'] = self.source[_VIEW_BODY]

        # form the drop if we do a create
        if do_create:
            statements.append("DROP VIEW IF EXISTS `%s`.`%s`;" % \
                              (self.destination[_VIEW_DB],
                               self.destination[_VIEW_NAME]))
        
        sql_stmt = "%s;" % self._build_statement(statement_parts)
        statements.append(sql_stmt)
        
        return statements


    def _transform_trigger(self):
        """Transform a trigger definition

        This method will transform a trigger definition to match the source
        configuration. It returns the appropriate SQL statement(s) to
        transform the object or None if no transformation is needed.
        
        Returns list - SQL statement(s) for transforming the trigger
        """
        statements = []
        
        # build a list of the parts
        statement_parts = [
            # preamble
            { 'fmt' : "%s", 'col' : _IGNORE_COLUMN, 'val' : "CREATE" },
            # definer
            { 'fmt' : " DEFINER=%s", 'col' : _TRIGGER_DEFINER, 'val' : "" },
            # object name
            { 'fmt' : " TRIGGER %s.%s", 'col' : _IGNORE_COLUMN,
              'val' : (self.destination[_TRIGGER_DB],
                       self.destination[_TRIGGER_NAME]) },
            # trigger timing
            { 'fmt' : " %s", 'col' : _TRIGGER_TIME, 'val' : "" },
            # trigger event
            { 'fmt' : " %s", 'col' : _TRIGGER_EVENT, 'val' : "" },
            # trigger table
            { 'fmt' : " ON %s." % self.destination[_TRIGGER_DB] + \
                      "%s FOR EACH ROW",
              'col' : _TRIGGER_TABLE, 'val' : "" },
            # trigger body
            { 'fmt' : " %s;", 'col' : _TRIGGER_BODY, 'val' : "" },
        ]
        
        # Triggers don't have ALTER SQL so we just pass back a drop + create.
        # if no changes, return None
        if not self._fill_values(statement_parts, True):
            return None

        statements.append("DROP TRIGGER IF EXISTS `%s`.`%s`;" % \
                          (self.destination[_TRIGGER_DB],
                           self.destination[_TRIGGER_NAME]))

        sql_stmt = self._build_statement(statement_parts)
        statements.append(sql_stmt)
        
        return statements
    

    def _transform_routine(self):
        """Transform a routine definition

        This method will transform a routine (FUNCTION or PROCEDURE) definition
        to match the source configuration. It returns the ALTER [FUNCTION |
        PROCEDURE] SQL statement to transform the object or None if no
        transformation is needed.
        
        Returns list - [CREATE|ALTER] [FUNCTION|PROCEDURE] statement for
                       transforming the routine
        """
        statements = []

        # check for create
        do_create = self._check_columns([_ROUTINE_BODY,
                                         _ROUTINE_DEFINER,
                                         _ROUTINE_PARAMS])

        # build a list of the parts
        statement_parts = [
            # preamble
            { 'fmt' : "%s", 'col' : _IGNORE_COLUMN,
              'val' : "CREATE" if do_create else "ALTER" },
            # definer
            { 'fmt' : " DEFINER=%s", 'col' : _ROUTINE_DEFINER, 'val' : "" },
            # object type and name
            { 'fmt' : " %s %s.%s", 'col' : _IGNORE_COLUMN,
              'val' : (self.obj_type.upper(), self.destination[_ROUTINE_DB],
                       self.destination[_ROUTINE_NAME]) },
            # parameters
            { 'fmt' : " %s", 'col' : _IGNORE_COLUMN, 'val' : ""  },
            # returns (Functions only)
            { 'fmt' : " RETURNS %s", 'col' : _IGNORE_COLUMN, 'val' : "" },
            # access method
            { 'fmt' : " %s", 'col' : _ROUTINE_SQL_DATA_ACCESS, 'val' : "" },
            # deterministic (Functions only)
            { 'fmt' : " %s", 'col' : _IGNORE_COLUMN, 'val' : "" },
            # security
            { 'fmt' : " SQL SECURITY %s", 'col' : _ROUTINE_SECURITY_TYPE,
              'val' : "" },
            # comment
            { 'fmt' : " COMMENT '%s'", 'col' : _ROUTINE_COMMENT, 'val' : "" },
            # body
            { 'fmt' : " %s", 'col' : _ROUTINE_BODY, 'val' : "" },
        ]
            
        # if no changes, return None
        if not self._fill_values(statement_parts, do_create):
            return None
        
        # add Params if do_create
        if do_create:
            statement_parts[3]['val'] = "(%s)" % self.source[_ROUTINE_PARAMS]
        
        # Add the returns for functions
        # Only when doing create or modifications to the body
        if self.obj_type.upper() == "FUNCTION":
            if do_create or \
               self.destination[_ROUTINE_BODY] != self.source[_ROUTINE_BODY]:
                statement_parts[4]['val'] = self.source[_ROUTINE_RETURNS]
            # Add deterministic
            if do_create:
                if self.source[_ROUTINE_IS_DETERMINISTIC] == "YES":
                    statement_parts[6]['val'] = "DETERMINISTIC"
                else: 
                    statement_parts[6]['val'] = "NOT DETERMINISTIC"
        
        # form the drop if we do a create
        if do_create:
            statements.append("DROP %s IF EXISTS `%s`.`%s`;" % \
                              (self.obj_type.upper(),
                               self.destination[_ROUTINE_DB],
                               self.destination[_ROUTINE_NAME]))
        
        sql_stmt = "%s;" % self._build_statement(statement_parts)
        statements.append(sql_stmt)
        
        return statements

    
    def _transform_event(self):
        """Transform a event definition

        This method will transform a event definition to match the source
        configuration. It returns the ALTER EVENT SQL statement to
        transform the object or None if no transformation is needed.
        
        Notes:
        
            The DEFINER does not compare properly for SHOW CREATE EVENT
            comparison.
            
            The RENAME cannot be processed because it requires a different
            name and mysqldiff compares on like names.
        
        Returns list - ALTER EVENT statement for transforming the event
        """
        statements = []
        
        # build a list of the parts
        statement_parts = [
            # preamble
            { 'fmt' : "%s", 'col' : _IGNORE_COLUMN, 'val' : "ALTER" },
            # definer
            { 'fmt' : " DEFINER=%s", 'col' : _EVENT_DEFINER, 'val' : "" },
            # type
            { 'fmt' : " %s", 'col' : _IGNORE_COLUMN, 'val' : "EVENT" },
            # object name
            { 'fmt' : " %s.%s", 'col' : _IGNORE_COLUMN,
              'val' : (self.destination[_EVENT_DB],
                       self.destination[_EVENT_NAME]) },
            # schedule - will be filled in later
            { 'fmt' : " %s", 'col' : _IGNORE_COLUMN, 'val' : "" },
            # complete
            { 'fmt' : " ON COMPLETION %s", 'col' : _EVENT_ON_COMPLETION,
              'val' : "" },
            # rename 
            { 'fmt' : " RENAME TO %s", 'col' : _EVENT_NAME, 'val' : "" },
            # status
            { 'fmt' : " %s", 'col' : _EVENT_STATUS,
              'val' : self.source[_EVENT_STATUS] },
            # event body
            { 'fmt' : " DO %s", 'col' : _EVENT_BODY, 'val' : "" },
        ]

        # We can only do the columns we know about and must ignore the others
        # like STARTS which may be Ok to differ.
        changes = self._check_columns([_EVENT_ON_COMPLETION, _EVENT_STATUS,
                                       _EVENT_BODY, _EVENT_NAME, _EVENT_ENDS,
                                       _EVENT_INTERVAL_FIELD, _EVENT_STARTS,
                                       _EVENT_INTERVAL_VALUE, _EVENT_TYPE])
        
        # We do the schedule separately because requires additional checks
        if changes:
            schedule = statement_parts[4]
            schedule['val'] = "ON SCHEDULE"
            if self.source[_EVENT_TYPE].upper() == "RECURRING":
                schedule['val'] += " EVERY %s" % \
                                   self.source[_EVENT_INTERVAL_VALUE]
            schedule['val'] += " %s" % \
                               self.source[_EVENT_INTERVAL_FIELD].upper()
            if self.source[_EVENT_STARTS] is not None:
                schedule['val'] += " STARTS '%s'" % self.source[_EVENT_STARTS]
            if self.source[_EVENT_ENDS] is not None:
                schedule['val'] += " ENDS '%s'" % self.source[_EVENT_ENDS]
                        
        # if no changes, return None
        if not changes:
            return None

        self._fill_values(statement_parts, False)
        
        # We must fix the status value
        status = statement_parts[7]
        if status['val'].upper() == "DISABLED":
            status['val'] = "DISABLE"
        elif status['val'].upper() == "ENABLED":
            status['val'] = "ENABLE"
        elif status['val'].upper() == "SLAVESIDE_DISABLED":
            status['val'] = "DISABLE ON SLAVE"

        sql_stmt = "%s;" % self._build_statement(statement_parts)
        statements.append(sql_stmt)
        
        return statements


    def _check_columns(self, col_list, destination=None, source=None):
        """Check for special column changes to trigger a CREATE
        
        This method checks a specific list of columns to see if the values
        differ from the destination and source. If they do, the method returns
        True else it returns False.
        
        col_list[in]       a list of column numbers to check
        destination[in]    If not None, use this list for destination
                           (default = None)
        source[in]         If not None, use this list for source
                           (default = None)
        
        Returns bool - True = there are differences, False = no differences
        """
        if destination is None:
            destination = self.destination
        if source is None:
            source = self.source
        for column_num in col_list:
            if destination[column_num] != source[column_num]:
                return True
        return False


    def _fill_values(self, stmt_parts, create=False,
                     destination=None, source=None):
        """Fill the structure with values
        
        This method loops through all of the column dictionaries filling in
        the value for any that differ from the destination to the source. If
        create is True, it will also fill in the values from the source to
        permit the completion of a CREATE statement.
        
        stmt_parts[in]     a list of column dictionaries
        create[in]         if True, fill in all values
                           if False, fill in only those values that differ
                           (default = False)
        destination[in]         If not None, use this list for destination
                           (default = None)
        source[in]         If not None, use this list for source
                           (default = None)
        
        Returns bool - True if changes found
        """
        if destination is None:
            destination = self.destination
        if source is None:
            source = self.source
        changes_found = False
        for part in stmt_parts:
            col = part['col']
            if col != _IGNORE_COLUMN:
                if source[col] is not None and destination[col] != source[col]:
                    part['val'] = source[col]
                    changes_found = True
                elif create:
                    part['val'] = destination[col]
                
        return changes_found
    
    
    def _build_statement(self, stmt_parts):
        """Build the object definition statement
        
        This method will build a completed statement based on the list of parts
        provided.
        
        stmt_parts[in]     a list of column dictionaries
        create[in]         if True, fill in all values
                           if False, fill in only those values that differ
                           (default = False)

        Returns string - the object definition string
        """
        stmt_values = []
        for part in stmt_parts:
            if part['col'] == _FORCE_COLUMN or part['val'] != "":
                stmt_values.append(part['fmt'] % part['val'])

        return ''.join(stmt_values)

