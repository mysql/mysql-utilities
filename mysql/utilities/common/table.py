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
This module contains abstractions of a MySQL table and an index.
"""

import multiprocessing
import sys
from itertools import izip

from mysql.utilities.exception import UtilError, UtilDBError
from mysql.connector.conversion import MySQLConverter
from mysql.utilities.common.format import print_list
from mysql.utilities.common.lock import Lock
from mysql.utilities.common.pattern_matching import parse_object_name
from mysql.utilities.common.server import Server
from mysql.utilities.common.sql_transform import (convert_special_characters,
                                                  quote_with_backticks,
                                                  remove_backtick_quoting,
                                                  is_quoted_with_backticks)

# Constants
_MAXPACKET_SIZE = 1024 * 1024
_MAXBULK_VALUES = 25000
_MAXTHREADS_INSERT = 6
_MAXROWS_PER_THREAD = 100000
_MAXAVERAGE_CALC = 100

_FOREIGN_KEY_QUERY = """
  SELECT CONSTRAINT_NAME, COLUMN_NAME, REFERENCED_TABLE_SCHEMA,
         REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME
  FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
  WHERE TABLE_SCHEMA = '%s' AND TABLE_NAME = '%s' AND
        REFERENCED_TABLE_SCHEMA IS NOT NULL
"""


class Index(object):
    """
    The Index class encapsulates an index for a given table as defined by
    the output of SHOW INDEXES FROM. The class has the following
    capabilities:

        - Check for duplicates
        - Create DROP statement for index
        - Print index CREATE statement
    """

    def __init__(self, db, index_tuple, verbose=False, sql_mode=''):
        """Constructor

        db[in]             Name of database
        index_tuple[in]    A tuple from the get_tbl_indexes() result set
        verbose[in]        print extra data during operations (optional)
                           default value = False
        """

        # Initialize and save values
        self.db = db
        self.sql_mode = sql_mode
        self.q_db = quote_with_backticks(db, self.sql_mode)
        self.verbose = verbose
        self.columns = []
        self.table = index_tuple[0]
        self.q_table = quote_with_backticks(index_tuple[0], self.sql_mode)
        self.unique = not int(index_tuple[1])
        self.name = index_tuple[2]
        self.q_name = quote_with_backticks(index_tuple[2], self.sql_mode)
        col = (index_tuple[4], index_tuple[7])
        self.columns.append(col)
        self.accept_nulls = True if index_tuple[9] else False
        self.type = index_tuple[10]
        self.compared = False                    # mark as compared for speed
        self.duplicate_of = None                 # saves duplicate index
        # pylint: disable=R0102
        if index_tuple[7] > 0:
            self.column_subparts = True          # check subparts e.g. a(20)
        else:
            self.column_subparts = False

    @staticmethod
    def __cmp_columns(col_a, col_b):
        """Compare two columns on name and subpart lengths if present

        col_a[in]          First column to compare
        col_b[in]          Second column to compare

        Returns True if col_a has the same name as col_b and if the
        subparts are col_a.sub <= col_b.sub.
        """

        sz_this = col_a[1]
        sz_that = col_b[1]
        # if column has the same name
        if col_a[0] == col_b[0]:
            # if they both have sub_parts, compare them
            if sz_this and sz_that:
                return (sz_this <= sz_that)
            # if this index has a sub_part and the other does
            # not, it is potentially redundant
            elif sz_this and sz_that is None:
                return True
            # if neither have sub_parts, it is a match
            elif sz_this is None and sz_that is None:
                return True
        else:
            return False  # no longer a duplicate

    def __check_column_list(self, index):
        """Compare the column list of this index with another

        index[in]          Instance of Index to compare

        Returns True if column list is a subset of index.
        """

        num_cols_this = len(self.columns)
        num_cols_that = len(index.columns)
        same_size = num_cols_this == num_cols_that
        if self.type == "BTREE":
            indexes = izip(self.columns, index.columns)
            for idx_pair in indexes:
                if not self.__cmp_columns(*idx_pair):
                    return False
            # All index pairs are the same, so return index with smaller number
            # of columns.
            return num_cols_this <= num_cols_that
        else:  # HASH, RTREE, FULLTEXT
            if self.type != "FULLTEXT":
                # For RTREE or HASH type indexes, an index is redundant if
                # it has the exact same columns on the exact same order.
                indexes = izip(self.columns, index.columns)
                return (same_size and
                        all((self.__cmp_columns(*idx_pair)
                             for idx_pair in indexes)))
            else:  # FULLTEXT index
                # A FULLTEXT index A is redundant of FULLTEXT index B if
                # the columns of A are a subset of B's columns, the order
                # does not matter.
                return all(any(self.__cmp_columns(col, icol) for
                               icol in index.columns) for col in self.columns)

    def is_duplicate(self, index):
        """Compare this index with another

        index[in]          Instance of Index to compare

        Returns True if this index is a subset of the Index presented.
        """

        # Don't compare the same index - no two indexes can have the same name
        if self.name == index.name:
            return False
        else:
            return self.__check_column_list(index)

    def contains_columns(self, col_names):
        """Check if the current index contains the columns of the given index.

        Returns True if it contains all the columns of the given index,
        otherwise False.
        """
        if len(self.columns) < len(col_names):
            # If has less columns than given index it does not contain all.
            return False
        else:
            this_col_names = [col[0] for col in self.columns]
            # Check if all index column are included in current one..
            for col_name in col_names:
                if col_name not in this_col_names:
                    return False  # found one column not included.

        # Pass previous verification; contains all the columns of given index.
        return True

    def add_column(self, column, sub_part, accept_null):
        """Add a column to the list of columns for this index

        column[in]         Column to add
        sub_part[in]       Sub part of colunm e.g. a(20)
        accept_null[in]       True to indicate the column accepts nulls
        """

        col = (column, sub_part)
        if sub_part > 0:
            self.column_subparts = True
        if accept_null:
            self.accept_nulls = True
        self.columns.append(col)

    def get_drop_statement(self):
        """Get the drop statement for this index

        Note: Ignores PRIMARY key indexes.

        Returns the DROP statement for this index.
        """
        if self.name == "PRIMARY":
            return None
        query_str = "ALTER TABLE {db}.{table} DROP INDEX {name}".format(
            db=self.q_db, table=self.q_table, name=self.q_name
        )
        return query_str

    def get_remove_columns_statement(self, col_names):
        """Get the ALTER TABLE statement to remove columns for this index.

        col_names[in]   list of columns names to remove from the index.

        Returns the ALTER TABLE statement (DROP/ADD) to remove the given
        columns names from the index.
        """
        # Create the new columns list for the index.
        idx_cols = [col[0] for col in self.columns if col[0] not in col_names]
        if not idx_cols:
            # Return a DROP statement if no columns are left.
            query_str = "ALTER TABLE {db}.{table} DROP INDEX {name}".format(
                db=self.q_db, table=self.q_table, name=self.q_name
            )
        else:
            # Otherwise, return a DROP/ADD statement with remaining columns.
            idx_cols_str = ', '.join(idx_cols)
            query_str = ("ALTER TABLE {db}.{table} DROP INDEX {name}, "
                         "ADD INDEX {name} ({cols})".format(db=self.q_db,
                                                            table=self.q_table,
                                                            name=self.q_name,
                                                            cols=idx_cols_str))
        return query_str

    def __get_column_list(self, backtick_quoting=True):
        """Get the column list for an index

        This method is used to print the CREATE and DROP statements.

        backtick_quoting[in]    Indicates if the columns names are to be quoted
                                with backticks or not. By default: True.

        Returns a string representing the list of columns for a
        column list. e.g. 'a, b(10), c'
        """
        col_list = []
        for col in self.columns:
            name, sub_part = (col[0], col[1])
            if backtick_quoting:
                name = quote_with_backticks(name, self.sql_mode)
            if sub_part > 0:
                col_str = "{0}({1})".format(name, sub_part)
            else:
                col_str = name
            col_list.append(col_str)
        return ', '.join(col_list)

    def print_index_sql(self):
        """Print the CREATE INDEX for indexes and ALTER TABLE for a primary key
        """
        if self.name == "PRIMARY":
            print("ALTER TABLE {db}.{table} ADD PRIMARY KEY ({cols})"
                  "".format(db=self.q_db, table=self.q_table,
                            cols=self.__get_column_list()))
        else:
            create_str = ("CREATE {unique}{fulltext}INDEX {name} ON "
                          "{db}.{table} ({cols}) {using}")
            unique_str = 'UNIQUE ' if self.unique else ''
            fulltext_str = 'FULLTEXT ' if self.type == 'FULLTEXT' else ''
            if (self.type == "BTREE") or (self.type == "RTREE"):
                using_str = 'USING {0}'.format(self.type)
            else:
                using_str = ''
            print(create_str.format(unique=unique_str, fulltext=fulltext_str,
                                    name=self.q_name, db=self.q_db,
                                    table=self.q_table,
                                    cols=self.__get_column_list(),
                                    using=using_str))

    def get_row(self, verbosity=0):
        """Return index information as a list of columns for tabular output.
        """
        cols = self.__get_column_list(backtick_quoting=False)
        if verbosity > 0:
            return (self.db, self.table, self.name, self.type, self.unique,
                    self.accept_nulls, cols)
        return (self.db, self.table, self.name, self.type, cols)


class Table(object):
    """
    The Table class encapsulates a table for a given database. The class
    has the following capabilities:

        - Check to see if the table exists
        - Check indexes for duplicates and redundancies
        - Print list of indexes for the table
        - Extract table data
        - Import table data
        - Copy table data
    """

    def __init__(self, server1, name, options=None):
        """Constructor

        server[in]         A Server object
        name[in]           Name of table in the form (db.table)
        options[in]        options for class: verbose, quiet, get_cols,
            quiet     If True, do not print information messages
            verbose   print extra data during operations (optional)
                      (default is False)
            get_cols  If True, get the column metadata on construction
                      (default is False)
        """
        if options is None:
            options = {}
        self.verbose = options.get('verbose', False)
        self.quiet = options.get('quiet', False)
        self.server = server1

        # Get sql_mode set on server
        self.sql_mode = self.server.select_variable("SQL_MODE")

        # Keep table identifier considering backtick quotes
        if is_quoted_with_backticks(name, self.sql_mode):
            self.q_table = name
            self.q_db_name, self.q_tbl_name = parse_object_name(name,
                                                                self.sql_mode)
            self.db_name = remove_backtick_quoting(self.q_db_name,
                                                   self.sql_mode)
            self.tbl_name = remove_backtick_quoting(self.q_tbl_name,
                                                    self.sql_mode)
            self.table = ".".join([self.db_name, self.tbl_name])
        else:
            self.table = name
            self.db_name, self.tbl_name = parse_object_name(name,
                                                            self.sql_mode)
            self.q_db_name = quote_with_backticks(self.db_name, self.sql_mode)
            self.q_tbl_name = quote_with_backticks(self.tbl_name,
                                                   self.sql_mode)
            self.q_table = ".".join([self.q_db_name, self.q_tbl_name])
        self.obj_type = "TABLE"
        self.pri_idx = None

        # We store each type of index in a separate list to make it easier
        # to manipulate
        self.btree_indexes = []
        self.hash_indexes = []
        self.rtree_indexes = []
        self.fulltext_indexes = []
        self.unique_not_null_indexes = None
        self.text_columns = []
        self.blob_columns = []
        self.bit_columns = []
        self.column_format = None
        self.column_names = []
        self.column_name_type = []
        self.q_column_names = []
        self.indexes_q_names = []
        if options.get('get_cols', False):
            self.get_column_metadata()
        self.dest_vals = None
        self.storage_engine = None

        # Get max allowed packet
        res = self.server.exec_query("SELECT @@session.max_allowed_packet")
        if res:
            self.max_packet_size = res[0][0]
        else:
            self.max_packet_size = _MAXPACKET_SIZE
        # Watch for invalid values
        if self.max_packet_size > _MAXPACKET_SIZE:
            self.max_packet_size = _MAXPACKET_SIZE

        self._insert = "INSERT INTO %s.%s VALUES "
        self.query_options = {  # Used for skipping fetch of rows
            'fetch': False
        }

    def exists(self, tbl_name=None):
        """Check to see if the table exists

        tbl_name[in]       table name (db.table)
                           (optional) If omitted, operation is performed
                           on the class instance table name.

        return True = table exists, False = table does not exist
        """

        db, table = (None, None)
        if tbl_name:
            db, table = parse_object_name(tbl_name, self.sql_mode)
        else:
            db = self.db_name
            table = self.tbl_name
        res = self.server.exec_query("SELECT TABLE_NAME " +
                                     "FROM INFORMATION_SCHEMA.TABLES " +
                                     "WHERE TABLE_SCHEMA = '%s'" % db +
                                     " and TABLE_NAME = '%s'" % table)

        return (res is not None and len(res) >= 1)

    def get_column_metadata(self, columns=None):
        """Get information about the table for the bulk insert operation.

        This method builds lists that describe the metadata of the table. This
        includes lists for:

          column names
          column format for building VALUES clause
          blob fields - for use in generating INSERT/UPDATE for blobs
          text fields - for use in checking for single quotes

        columns[in]        if None, use EXPLAIN else use column list.
        """

        if columns is None:
            columns = self.server.exec_query("explain %s" % self.q_table)
        stop = len(columns)
        self.column_names = []
        self.q_column_names = []
        col_format_values = [''] * stop
        if columns is not None:
            for col in range(0, stop):
                if is_quoted_with_backticks(columns[col][0], self.sql_mode):
                    self.column_names.append(
                        remove_backtick_quoting(columns[col][0],
                                                self.sql_mode))
                    self.q_column_names.append(columns[col][0])
                else:
                    self.column_names.append(columns[col][0])
                    self.q_column_names.append(
                        quote_with_backticks(columns[col][0], self.sql_mode))
                col_type = columns[col][1].lower()
                if ('char' in col_type or 'enum' in col_type or
                        'set' in col_type or 'binary' in col_type):
                    self.text_columns.append(col)
                    col_format_values[col] = "'%s'"
                elif 'blob' in col_type or 'text'in col_type:
                    self.blob_columns.append(col)
                    col_format_values[col] = "%s"
                elif "date" in col_type or "time" in col_type:
                    col_format_values[col] = "'%s'"
                elif "bit" in col_type:
                    self.bit_columns.append(col)
                    col_format_values[col] = "%d"
                else:
                    col_format_values[col] = "%s"
        self.column_format = "%s%s%s" % \
                             (" (", ', '.join(col_format_values), ")")

    def get_col_names(self, quote_backticks=False):
        """Get column names for the export operation.

        quote_backticks[in]    If True the column names will be quoted with
                               backticks. Default is False.

        Return (list) column names
        """

        if self.column_format is None:
            self.column_names = []
            self.q_column_names = []
            rows = self.server.exec_query("explain {0}".format(self.q_table))
            for row in rows:
                self.column_names.append(row[0])
                self.q_column_names.append(quote_with_backticks(row[0],
                                                                self.sql_mode))

        return self.q_column_names if quote_backticks else self.column_names

    def get_col_names_types(self, quote_backticks=False):
        """Get a list of tuples of column name and type.

        quote_backticks[in]    If True the column name will be quoted with
                               backticks. Default is False.

        Return (list) of touple (column name, type)
        """

        self.column_name_type = []
        rows = self.server.exec_query("explain {0}".format(self.q_table))
        for row in rows:
            if quote_backticks:
                self.column_name_type.append(
                    [quote_with_backticks(row[0], self.sql_mode)] +
                    list(row[1:])
                )
            else:
                self.column_name_type.append(row)

        return self.column_name_type

    def has_index(self, index_q_name):
        """A method to determine if this table has a determinate index using
        his name.

        index_q_name[in]    the name of the index (must be quoted).

        returns True if this Table has an index with the given name, otherwise
        false.
        """
        if [idx_q_name for idx_q_name in self.indexes_q_names
                if idx_q_name == index_q_name]:
            return True
        return False

    def get_not_null_unique_indexes(self, refresh=False):
        """get all the unique indexes which columns does not accepts null
        values.
        refresh[in] Boolean value used to force the method to read index
                    information directly from the server, instead of using
                    cached values.

        Returns list of indexes.
        """
        # First check if the instance variable exists.
        if self.unique_not_null_indexes is None or refresh:
            # Get the indexes for the table.
            try:
                self.get_indexes()
            except UtilDBError:
                # Table may not exist yet. Happens on import operations.
                pass
            # Now for each of them, check if they are UNIQUE and NOT NULL.
            no_null_idxes = []
            no_null_idxes.extend(
                [idx for idx in self.btree_indexes if not idx.accept_nulls and
                 idx.unique]
            )
            no_null_idxes.extend(
                [idx for idx in self.hash_indexes if not idx.accept_nulls and
                 idx.unique]
            )
            no_null_idxes.extend(
                [idx for idx in self.rtree_indexes if not idx.accept_nulls and
                 idx.unique]
            )
            no_null_idxes.extend(
                [idx for idx in self.fulltext_indexes
                 if not idx.accept_nulls and idx.unique]
            )
            self.unique_not_null_indexes = no_null_idxes

        return self.unique_not_null_indexes

    def _build_update_blob(self, row, new_db, name):
        """Build an UPDATE statement to update blob fields.

        row[in]            a row to process
        new_db[in]         new database name
        name[in]           name of the table

        Returns UPDATE string
        """
        if self.column_format is None:
            self.get_column_metadata()

        blob_insert = "UPDATE %s.%s SET " % (new_db, name)
        where_values = []
        do_commas = False
        has_data = False
        stop = len(row)
        for col in range(0, stop):
            col_name = self.q_column_names[col]
            if col in self.blob_columns:
                if row[col] is not None and len(row[col]) > 0:
                    if do_commas:
                        blob_insert += ", "
                    blob_insert += "%s = " % col_name + "%s" % \
                                   MySQLConverter().quote(
                                       convert_special_characters(row[col]))
                    has_data = True
                    do_commas = True
            else:
                # Convert None values to NULL (not '' to NULL)
                if row[col] is None:
                    value = 'NULL'
                else:
                    value = "'{0}'".format(row[col])
                where_values.append("{0} = {1}".format(col_name, value))
        if has_data:
            return "{0} WHERE {1};".format(blob_insert,
                                           " AND ".join(where_values))
        return None

    def _build_insert_blob(self, row, new_db, tbl_name):
        """Build an INSERT statement for the given row.

        row[in]                a row to process
        new_db[in]             new database name
        tbl_name[in]           name of the table

        Returns INSERT string.
        """
        if self.column_format is None:
            self.get_column_metadata()

        converter = MySQLConverter()
        row_vals = []
        # Deal with blob, special characters and NULL values.
        for index, column in enumerate(row):
            # pylint: disable=W0212
            if index in self.blob_columns:
                row_vals.append(converter.quote(
                    convert_special_characters(column)))
            elif index in self.text_columns:
                if column is None:
                    row_vals.append("NULL")
                else:
                    row_vals.append(convert_special_characters(column))
            elif index in self.bit_columns:
                if column is None:
                    row_vals.append("NULL")
                else:
                    row_vals.append(converter._BIT_to_python(column))
            else:
                if column is None:
                    row_vals.append("NULL")
                else:
                    row_vals.append(column)

        # Create the insert statement.
        insert_stm = ("INSERT INTO {0}.{1} VALUES {2};"
                      "".format(new_db, tbl_name,
                                self.column_format % tuple(row_vals)))

        # Replace 'NULL' occurrences with NULL values.
        insert_stm = insert_stm.replace("'NULL'", "NULL")

        return insert_stm

    def get_column_string(self, row, new_db, skip_blobs=False):
        """Return a formatted list of column data.

        row[in]            a row to process
        new_db[in]         new database name
        skip_blobs[in]     boolean value, if True, blob columns are skipped

        Returns (string) column list
        """

        if self.column_format is None:
            self.get_column_metadata()

        blob_inserts = []
        values = list(row)
        is_blob_insert = False
        # find if we have some unique column indexes
        unique_indexes = len(self.get_not_null_unique_indexes())
        # If all columns are blobs or there aren't any UNIQUE NOT NULL indexes
        # then rows won't be correctly copied using the update statement,
        # so we must use insert statements instead.
        if not skip_blobs and \
                (len(self.blob_columns) == len(self.column_names) or
                 self.blob_columns and not unique_indexes):
            blob_inserts.append(self._build_insert_blob(row, new_db,
                                                        self.q_tbl_name))
            is_blob_insert = True
        else:
            # Find blobs
            if self.blob_columns:
                # Save blob updates for later...
                blob = self._build_update_blob(row, new_db, self.q_tbl_name)
                if blob is not None:
                    blob_inserts.append(blob)
                for col in self.blob_columns:
                    values[col] = "NULL"

        if not is_blob_insert:
            # Replace single quotes located in the value for a text field with
            # the correct special character escape sequence. This fixes SQL
            # errors related to using single quotes in a string value that is
            # single quoted. For example, 'this' is it' is changed to
            # 'this\' is it'.
            for col in self.text_columns:
                # Check if the value is not None before replacing quotes
                if values[col]:
                    # Apply escape sequences to special characters
                    values[col] = convert_special_characters(values[col])

            for col in self.bit_columns:
                if values[col] is not None:
                    # Convert BIT to INTEGER for dump.
                    # pylint: disable=W0212
                    values[col] = MySQLConverter()._BIT_to_python(values[col])

            # Build string (add quotes to "string" like types)
            val_str = self.column_format % tuple(values)

            # Change 'None' occurrences with "NULL"
            val_str = val_str.replace(", None", ", NULL")
            val_str = val_str.replace("(None", "(NULL")
            val_str = val_str.replace(", 'None'", ", NULL")
            val_str = val_str.replace("('None'", "(NULL")

        else:
            val_str = None

        return val_str, blob_inserts

    def make_bulk_insert(self, rows, new_db, columns_names=None,
                         skip_blobs=False):
        """Create bulk insert statements for the data

        Reads data from a table (rows) and builds group INSERT statements for
        bulk inserts.

        Note: This method does not print any information to stdout.

        rows[in]           a list of rows to process
        new_db[in]         new database name
        skip_blobs[in]     boolean value, if True, blob columns are skipped

        Returns (tuple) - (bulk insert statements, blob data inserts)
        """

        if self.column_format is None:
            self.get_column_metadata()

        data_inserts = []
        blob_inserts = []
        row_count = 0
        data_size = 0
        val_str = None

        for row in rows:
            if row_count == 0:
                if columns_names:
                    insert_str = "INSERT INTO {0}.{1} ({2}) VALUES ".format(
                        new_db, self.q_tbl_name, ", ".join(columns_names)
                    )
                else:
                    insert_str = self._insert % (new_db, self.q_tbl_name)
                if val_str:
                    row_count += 1
                    insert_str += val_str
                data_size = len(insert_str)

            col_data = self.get_column_string(row, new_db, skip_blobs)
            if len(col_data[1]) > 0:
                blob_inserts.extend(col_data[1])
            if col_data[0]:
                val_str = col_data[0]

                row_size = len(val_str)
                next_size = data_size + row_size + 3
                if ((row_count >= _MAXBULK_VALUES) or
                        (next_size > (int(self.max_packet_size) - 512))):
                    # add to buffer
                    data_inserts.append(insert_str)
                    row_count = 0
                else:
                    row_count += 1
                    if row_count > 1:
                        insert_str += ", "
                    insert_str += val_str
                    data_size += row_size + 3

        if row_count > 0:
            data_inserts.append(insert_str)

        return data_inserts, blob_inserts

    def get_storage_engine(self):
        """Get the storage engine (in UPPERCASE) for the table.

        Returns the name in UPPERCASE of the storage engine use for the table
        or None if the information is not found.
        """
        self.server.exec_query("USE {0}".format(self.q_db_name),
                               self.query_options)
        res = self.server.exec_query(
            "SHOW TABLE STATUS WHERE name = '{0}'".format(self.tbl_name)
        )
        try:
            # Return store engine converted to UPPER cases.
            return res[0][1].upper() if res[0][1] else None
        except IndexError:
            # Return None if table status information is not available.
            return None

    def get_segment_size(self, num_conn=1):
        """Get the segment size based on number of connections (threads).

        num_conn[in]       Number of threads(connections) to use
                           Default = 1 (one large segment)

        Returns (int) segment_size

                Note: if num_conn <= 1 - returns number of rows
        """

        # Get number of rows
        num_rows = 0
        try:
            res = self.server.exec_query("USE %s" % self.q_db_name,
                                         self.query_options)
        except:
            pass
        res = self.server.exec_query("SHOW TABLE STATUS LIKE '%s'" %
                                     self.tbl_name)
        if res:
            num_rows = int(res[0][4])

        if num_conn <= 1:
            return num_rows

        # Calculate number of threads and segment size to fetch
        thread_limit = num_conn
        if thread_limit > _MAXTHREADS_INSERT:
            thread_limit = _MAXTHREADS_INSERT
        if num_rows > (_MAXROWS_PER_THREAD * thread_limit):
            max_threads = thread_limit
        else:
            max_threads = int(num_rows / _MAXROWS_PER_THREAD)
        if max_threads == 0:
            max_threads = 1
        if max_threads > 1 and self.verbose:
            print "# Using multi-threaded insert option. Number of " \
                  "threads = %d." % max_threads
        return (num_rows / max_threads) + max_threads

    def _bulk_insert(self, rows, new_db, destination=None):
        """Import data using bulk insert

        Reads data from a table and builds group INSERT statements for writing
        to the destination server specified (new_db.name).

        This method is designed to be used in a thread for parallel inserts.
        As such, it requires its own connection to the destination server.

        Note: This method does not print any information to stdout.

        rows[in]           a list of rows to process
        new_db[in]         new database name
        destination[in]    the destination server
        """
        if self.dest_vals is None:
            self.dest_vals = self.get_dest_values(destination)

        # Spawn a new connection
        server_options = {
            'conn_info': self.dest_vals,
            'role': "thread",
        }
        dest = Server(server_options)
        dest.connect()

        # Test if SQL_MODE is 'NO_BACKSLASH_ESCAPES' in the destination server
        if dest.select_variable("SQL_MODE") == "NO_BACKSLASH_ESCAPES":
            # Change temporarily the SQL_MODE in the destination server
            dest.exec_query("SET @@SESSION.SQL_MODE=''")

        # Issue the write lock
        lock_list = [("%s.%s" % (new_db, self.q_tbl_name), 'WRITE')]
        my_lock = Lock(dest, lock_list, {'locking': 'lock-all', })

        # First, turn off foreign keys if turned on
        dest.disable_foreign_key_checks(True)

        if self.column_format is None:
            self.get_column_metadata()
        data_lists = self.make_bulk_insert(rows, new_db)
        insert_data = data_lists[0]
        blob_data = data_lists[1]

        # Insert the data first
        for data_insert in insert_data:
            try:
                dest.exec_query(data_insert, self.query_options)
            except UtilError, e:
                raise UtilError("Problem inserting data. "
                                "Error = %s" % e.errmsg)

        # Now insert the blob data if there is any
        for blob_insert in blob_data:
            try:
                dest.exec_query(blob_insert, self.query_options)
            except UtilError, e:
                raise UtilError("Problem updating blob field. "
                                "Error = %s" % e.errmsg)

        # Now, turn on foreign keys if they were on at the start
        dest.disable_foreign_key_checks(False)
        my_lock.unlock()
        del dest

    def insert_rows(self, rows, new_db, destination=None, spawn=False):
        """Insert rows in the table using bulk copy.

        This method opens a new connect to the destination server to insert
        the data with a bulk copy. If spawn is True, the method spawns a new
        process and returns it. This allows for using a multi-threaded insert
        which can be faster on some platforms. If spawn is False, the method
        will open a new connection to insert the data.

        num_conn[in]       Number of threads(connections) to use for insert
        rows[in]           List of rows to insert
        new_db[in]         Rename the db to this name
        destination[in]    Destination server
                           Default = None (copy to same server)
        spawn[in]          If True, spawn a new process for the insert
                           Default = False

        Returns If spawn == True, process
                If spawn == False, None
        """

        if self.column_format is None:
            self.get_column_metadata()

        if self.dest_vals is None:
            self.dest_vals = self.get_dest_values(destination)

        proc = None
        if spawn:
            proc = multiprocessing.Process(target=self._bulk_insert,
                                           args=(rows, new_db, destination))
        else:
            self._bulk_insert(rows, new_db, destination)

        return proc

    def _clone_data(self, new_db):
        """Clone table data.

        This method will copy all of the data for a table
        from the old database to the new database on the same server.

        new_db[in]         New database name for the table
        """
        query_str = "INSERT INTO %s.%s SELECT * FROM %s.%s" % \
                    (new_db, self.q_tbl_name, self.q_db_name, self.q_tbl_name)
        if self.verbose and not self.quiet:
            print query_str

        # Disable foreign key checks to allow data to be copied without running
        # into foreign key referential integrity issues
        self.server.disable_foreign_key_checks(True)
        self.server.exec_query(query_str)
        self.server.disable_foreign_key_checks(False)

    def copy_data(self, destination, cloning=False, new_db=None,
                  connections=1):
        """Retrieve data from a table and copy to another server and database.

        Reads data from a table and inserts the correct INSERT statements into
        the file provided.

        Note: if connections < 1 - retrieve the data one row at-a-time

        destination[in]    Destination server
        cloning[in]        If True, we are copying on the same server
        new_db[in]         Rename the db to this name
        connections[in]    Number of threads(connections) to use for insert
        """
        # Get sql_mode from destination
        dest_sql_mode = destination.select_variable("SQL_MODE")
        if new_db is None:
            new_db = self.q_db_name
        else:
            # If need quote new_db identifier with backticks
            if not is_quoted_with_backticks(new_db, dest_sql_mode):
                new_db = quote_with_backticks(new_db, dest_sql_mode)

        num_conn = int(connections)

        if cloning:
            self._clone_data(new_db)
        else:
            # Read and copy the data
            pthreads = []
            # Change the sql_mode if the mode is different on each server
            # and if "ANSI_QUOTES" is set in source, this is for
            # compatibility between the names.
            prev_sql_mode = ''
            if self.sql_mode != dest_sql_mode and \
               "ANSI_QUOTES" in self.sql_mode:
                prev_sql_mode = self.server.select_variable("SQL_MODE")
                self.server.exec_query("SET @@SESSION.SQL_MODE=''")
                self.sql_mode = ''

                self.q_tbl_name = quote_with_backticks(
                    self.tbl_name,
                    self.sql_mode
                )
                self.q_db_name = quote_with_backticks(
                    self.db_name,
                    self.sql_mode
                )
                self.q_table = ".".join([self.q_db_name, self.q_tbl_name])
                self.q_column_names = []
                for column in self.column_names:
                    self.q_column_names.append(
                        quote_with_backticks(column, self.sql_mode)
                    )
            for rows in self.retrieve_rows(num_conn):
                p = self.insert_rows(rows, new_db, destination, num_conn > 1)
                if p is not None:
                    p.start()
                    pthreads.append(p)

            if num_conn > 1:
                # Wait for all threads to finish
                for p in pthreads:
                    p.join()
            # restoring the previous sql_mode, changed if the sql_mode in both
            # servers is different and one is "ANSI_QUOTES"
            if prev_sql_mode:
                self.server.exec_query("SET @@SESSION.SQL_MODE={0}"
                                       "".format(prev_sql_mode))
                self.sql_mode = prev_sql_mode
                self.q_tbl_name = quote_with_backticks(
                    self.tbl_name,
                    self.sql_mode
                )
                self.q_db_name = quote_with_backticks(
                    self.db_name,
                    self.sql_mode
                )
                self.q_table = ".".join([self.q_db_name, self.q_tbl_name])
                for column in self.column_names:
                    self.q_column_names.append(
                        quote_with_backticks(column, self.sql_mode)
                    )

    def retrieve_rows(self, num_conn=1):
        """Retrieve the table data in rows.

        This method can be used to retrieve rows from a table as a generator
        specifying how many rows to retrieve at one time (segment_size is
        calculated based on number of rows / number of connections).

        Note: if num_conn < 1 - retrieve the data one row at-a-time

        num_conn[in]       Number of threads(connections) to use
                           Default = 1 (one large segment)

        Returns (yield) row data
        """

        if num_conn > 1:
            # Only get the segment size when needed.
            segment_size = self.get_segment_size(num_conn)

        # Execute query to get all of the data
        cur = self.server.exec_query("SELECT * FROM {0}".format(self.q_table),
                                     self.query_options)

        while True:
            rows = None
            if num_conn < 1:
                rows = []
                row = cur.fetchone()
                if row is None:
                    raise StopIteration()
                rows.append(row)
            elif num_conn == 1:
                rows = cur.fetchall()
                yield rows
                raise StopIteration()
            else:
                rows = cur.fetchmany(segment_size)
                if not rows:
                    raise StopIteration()
            if rows is None:
                raise StopIteration()
            yield rows

        cur.close()

    def get_dest_values(self, destination=None):
        """Get the destination connection values if not already set.

        destination[in]    Connection values for destination server

        Returns connection values for destination if set or self.server
        """
        # Get connection to database
        if destination is None:
            conn_val = {
                "host": self.server.host,
                "user": self.server.user,
                "passwd": self.server.passwd,
                "unix_socket": self.server.socket,
                "port": self.server.port
            }
        else:
            conn_val = {
                "host": destination.host,
                "user": destination.user,
                "passwd": destination.passwd,
                "unix_socket": destination.socket,
                "port": destination.port
            }
        return conn_val

    def get_tbl_indexes(self):
        """Return a result set containing all indexes for a given table

        Returns result set
        """
        res = self.server.exec_query("SHOW INDEXES FROM %s" % self.q_table)
        # Clear the cardinality column
        if res:
            new_res = []
            for row in res:
                new_row = []
                i = 0
                for item in row:
                    if not i == 6:
                        new_row.append(item)
                    else:
                        new_row.append("0")
                    i = i + 1
                new_res.append(tuple(new_row))
            res = new_res
        return res

    def get_tbl_foreign_keys(self):
        """Return a result set containing all foreign keys for the table

        Returns result set
        """
        res = self.server.exec_query(_FOREIGN_KEY_QUERY % (self.db_name,
                                                           self.tbl_name))
        return res

    @staticmethod
    def __append(indexes, index):
        """Encapsulated append() method to ensure the primary key index
        is placed at the front of the list.
        """

        # Put the primary key first so that it can be compared to all indexes
        if index.name == "PRIMARY":
            indexes.insert(0, index)
        else:
            indexes.append(index)

    @staticmethod
    def __check_index(index, indexes, master_list):
        """Check a single index for duplicate or redundancy against a list
        of other Indexes.

        index[in]          The Index to compare
        indexes[in]        A list of Index instances to compare
        master_list[in]    A list of know duplicate Index instances

        Returns a tuple of whether duplicates are found and if found the
        list of duplicate indexes for this table
        """

        duplicates_found = False
        duplicate_list = []
        if indexes and index:
            for idx in indexes:
                if index == idx:
                    continue
                # Don't compare b == a when a == b has already occurred
                if not index.compared and idx.is_duplicate(index):
                    # make sure we haven't already found this match
                    if not idx.column_subparts:
                        idx.compared = True
                    if idx not in master_list:
                        duplicates_found = True
                        # PRIMARY key can be identified as redundant of an
                        # unique index with more columns, in that case always
                        # mark the other as the duplicate.
                        if idx.name == "PRIMARY":
                            index.duplicate_of = idx
                            duplicate_list.append(index)
                        else:
                            idx.duplicate_of = index
                            duplicate_list.append(idx)
        return (duplicates_found, duplicate_list)

    def __check_index_list(self, indexes):
        """Check a list of Index instances for duplicates.

        indexes[in]        A list of Index instances to compare

        Returns a tuple of whether duplicates are found and if found the
        list of duplicate indexes for this table
        """

        duplicates_found = False
        duplicate_list = []
        # Caller must ensure there are at least 2 elements in the list.
        if len(indexes) < 2:
            return (False, None)
        for index in indexes:
            res = self.__check_index(index, indexes, duplicate_list)
            if res[0]:
                duplicates_found = True
                duplicate_list.extend(res[1])
        return (duplicates_found, duplicate_list)

    def __check_clustered_index_list(self, indexes):
        """ Check for indexes containing the clustered index from the list.

        indexes[in]     list of indexes instances to check.

        Returns the list of indexes that contain the clustered index or
        None (if none found).
        """
        redundant_indexes = []
        if not self.pri_idx:
            self.get_primary_index()
        pri_idx_cols = [col[0] for col in self.pri_idx]
        for index in indexes:
            if index.name == 'PRIMARY':
                # Skip primary key.
                continue
            elif index.contains_columns(pri_idx_cols):
                redundant_indexes.append(index)

        return redundant_indexes if redundant_indexes else []

    def _get_index_list(self):
        """Get the list of indexes for a table.
        Returns list containing indexes.
        """
        rows = self.get_tbl_indexes()
        return rows

    def get_primary_index(self):
        """Retrieve the primary index columns for this table.
        """
        pri_idx = []

        rows = self.server.exec_query("EXPLAIN {0}".format(self.q_table))

        # Return False if no indexes found.
        if not rows:
            return pri_idx

        for row in rows:
            if row[3] == 'PRI':
                pri_idx.append(row)

        self.pri_idx = pri_idx

        return pri_idx

    def get_column_explanation(self, column_name):
        """Retrieve the explain description for the given column.
        """
        column_exp = []

        rows = self.server.exec_query("EXPLAIN {0}".format(self.q_table))

        # Return False if no indexes found.
        if not rows:
            return column_exp

        for row in rows:
            if row[0] == column_name:
                column_exp.append(row)

        return column_exp

    def get_indexes(self):
        """Retrieve the indexes from the server and load them into lists
        based on type.

        Returns True - table has indexes, False - table has no indexes
        """

        self.btree_indexes = []
        self.hash_indexes = []
        self.rtree_indexes = []
        self.fulltext_indexes = []
        self.indexes_q_names = []

        if self.verbose:
            print "# Getting indexes for %s" % (self.table)
        rows = self._get_index_list()

        # Return False if no indexes found.
        if not rows:
            return False
        idx = None
        prev_name = ""
        for row in rows:
            if (row[2] != prev_name) or (prev_name == ""):
                prev_name = row[2]
                idx = Index(self.db_name, row, sql_mode=self.sql_mode)
                if idx.type == "BTREE":
                    self.__append(self.btree_indexes, idx)
                elif idx.type == "HASH":
                    self.__append(self.hash_indexes, idx)
                elif idx.type == "RTREE":
                    self.__append(self.rtree_indexes, idx)
                else:
                    self.__append(self.fulltext_indexes, idx)
            elif idx:
                idx.add_column(row[4], row[7], row[9])
            self.indexes_q_names.append(quote_with_backticks(row[2],
                                                             self.sql_mode))
        return True

    def check_indexes(self, show_drops=False):
        """Check for duplicate or redundant indexes and display all matches

        show_drops[in]     (optional) If True the DROP statements are printed

        Note: You must call get_indexes() prior to calling this method. If
        get_indexes() is not called, no duplicates will be found.
        """

        dupes = []
        res = self.__check_index_list(self.btree_indexes)
        # if there are duplicates, add them to the dupes list
        if res[0]:
            dupes.extend(res[1])
        res = self.__check_index_list(self.hash_indexes)
        # if there are duplicates, add them to the dupes list
        if res[0]:
            dupes.extend(res[1])
        res = self.__check_index_list(self.rtree_indexes)
        # if there are duplicates, add them to the dupes list
        if res[0]:
            dupes.extend(res[1])
        res = self.__check_index_list(self.fulltext_indexes)
        # if there are duplicates, add them to the dupes list
        if res[0]:
            dupes.extend(res[1])

        # Check if secondary keys contains the clustered index (i.e. Primary
        # key). In InnoDB, each record in a secondary index contains the
        # primary key columns. Therefore the use of keys that include the
        # primary key might be redundant.
        redundant_idxs = []
        if not self.storage_engine:
            self.storage_engine = self.get_storage_engine()
        if self.storage_engine == 'INNODB':
            all_indexes = self.btree_indexes
            all_indexes.extend(self.hash_indexes)
            all_indexes.extend(self.rtree_indexes)
            all_indexes.extend(self.fulltext_indexes)
            redundant_idxs = self.__check_clustered_index_list(all_indexes)

        # Print duplicate and redundant keys on composite indexes.
        if len(dupes) > 0:
            plural_1, verb_conj, plural_2 = (
                ('', 'is a', '') if len(dupes) == 1 else ('es', 'are', 's')
            )
            print("# The following index{0} {1} duplicate{2} or redundant "
                  "for table {3}:".format(plural_1, verb_conj, plural_2,
                                          self.table))
            for index in dupes:
                print("#")
                index.print_index_sql()
                print("#     may be redundant or duplicate of:")
                index.duplicate_of.print_index_sql()
            if show_drops:
                print("#\n# DROP statement{0}:\n#".format(plural_2))
                for index in dupes:
                    print("{0};".format(index.get_drop_statement()))
                print("#")

        # Print redundant indexes containing clustered key.
        if redundant_idxs:
            plural, verb_conj, plural_2 = (
                ('', 's', '') if len(redundant_idxs) == 1 else ('es', '', 's')
            )

            print("# The following index{0} for table {1} contain{2} the "
                  "clustered index and might be redundant:".format(plural,
                                                                   self.table,
                                                                   verb_conj))
            for index in redundant_idxs:
                print("#")
                index.print_index_sql()
            if show_drops:
                print("#\n# DROP/ADD statement{0}:\n#".format(plural_2))
                # Get columns from primary key to be removed.
                pri_idx_cols = [col[0] for col in self.pri_idx]
                for index in redundant_idxs:
                    print("{0};".format(
                        index.get_remove_columns_statement(pri_idx_cols)
                    ))
                print("#")

        if not self.quiet and not dupes and not redundant_idxs:
            print("# Table {0} has no duplicate nor redundant "
                  "indexes.".format(self.table))

    def show_special_indexes(self, fmt, limit, best=False):
        """Display a list of the best or worst queries for this table.

        This shows the best (first n) or worst (last n) performing queries
        for a given table.

        fmt[in]            format out output = sql, table, tab, csv
        limit[in]          number to limit the display
        best[in]           (optional) if True, print best performing indexes
                                      if False, print worst performing indexes
        """

        _QUERY = """
            SELECT
                t.TABLE_SCHEMA AS `db`, t.TABLE_NAME AS `table`,
                s.INDEX_NAME AS `index name`, s.COLUMN_NAME AS `field name`,
                s.SEQ_IN_INDEX `seq in index`, s2.max_columns AS `# cols`,
                s.CARDINALITY AS `card`, t.TABLE_ROWS AS `est rows`,
                ROUND(((s.CARDINALITY / IFNULL(
                IF(t.TABLE_ROWS < s.CARDINALITY, s.CARDINALITY, t.TABLE_ROWS),
                0.01)) * 100), 2) AS `sel_percent`
            FROM INFORMATION_SCHEMA.STATISTICS s
                INNER JOIN INFORMATION_SCHEMA.TABLES t
                ON s.TABLE_SCHEMA = t.TABLE_SCHEMA
                AND s.TABLE_NAME = t.TABLE_NAME
            INNER JOIN (
                SELECT TABLE_SCHEMA, TABLE_NAME, INDEX_NAME,
                    MAX(SEQ_IN_INDEX) AS max_columns
                FROM INFORMATION_SCHEMA.STATISTICS
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
                      AND INDEX_NAME != 'PRIMARY'
                GROUP BY TABLE_SCHEMA, TABLE_NAME, INDEX_NAME
             ) AS s2
             ON s.TABLE_SCHEMA = s2.TABLE_SCHEMA
                AND s.TABLE_NAME = s2.TABLE_NAME
                AND s.INDEX_NAME = s2.INDEX_NAME
            WHERE t.TABLE_SCHEMA != 'mysql'
                AND t.TABLE_ROWS > 10 /* Only tables with some rows */
                AND s.CARDINALITY IS NOT NULL
                AND (s.CARDINALITY / IFNULL(
                IF(t.TABLE_ROWS < s.CARDINALITY, s.CARDINALITY, t.TABLE_ROWS),
                0.01)) <= 1.00
            ORDER BY `sel_percent`
        """
        query_options = {
            'params': (self.db_name, self.tbl_name,)
        }
        rows = []
        idx_type = "best"
        if not best:
            idx_type = "worst"
        if best:
            rows = self.server.exec_query(_QUERY + "DESC LIMIT %s" % limit,
                                          query_options)
        else:
            rows = self.server.exec_query(_QUERY + "LIMIT %s" % limit,
                                          query_options)
        if rows:
            print("#")
            if limit == 1:
                print("# Showing the {0} performing index from "
                      "{1}:".format(idx_type, self.table))
            else:
                print("# Showing the top {0} {1} performing indexes from "
                      "{2}:".format(limit, idx_type, self.table))
            print("#")
            cols = ("database", "table", "name", "column", "sequence",
                    "num columns", "cardinality", "est. rows", "percent")
            print_list(sys.stdout, fmt, cols, rows)
        else:
            print("# WARNING: Not enough data to calculate "
                  "best/worst indexes.")

    @staticmethod
    def __print_index_list(indexes, fmt, no_header=False, verbosity=0):
        """Print the list of indexes

        indexes[in]        list of indexes to print
        fmt[in]            format out output = sql, table, tab, csv
        no_header[in]      (optional) if True, do not print the header
        """
        if fmt == "sql":
            for index in indexes:
                index.print_index_sql()
        else:
            if verbosity > 0:
                cols = ("database", "table", "name", "type", "unique",
                        "accepts nulls", "columns")
            else:
                cols = ("database", "table", "name", "type", "columns")

            rows = []
            for index in indexes:
                rows.append(index.get_row(verbosity))
            print_list(sys.stdout, fmt, cols, rows, no_header)

    def print_indexes(self, fmt, verbosity):
        """Print all indexes for this table

        fmt[in]         format out output = sql, table, tab, csv
        """

        print "# Showing indexes from %s:\n#" % (self.table)
        if fmt == "sql":
            self.__print_index_list(self.btree_indexes, fmt,
                                    verbosity=verbosity)
            self.__print_index_list(self.hash_indexes, fmt, False,
                                    verbosity=verbosity)
            self.__print_index_list(self.rtree_indexes, fmt, False,
                                    verbosity=verbosity)
            self.__print_index_list(self.fulltext_indexes, fmt, False,
                                    verbosity=verbosity)
        else:
            master_indexes = []
            master_indexes.extend(self.btree_indexes)
            master_indexes.extend(self.hash_indexes)
            master_indexes.extend(self.rtree_indexes)
            master_indexes.extend(self.fulltext_indexes)
            self.__print_index_list(master_indexes, fmt,
                                    verbosity=verbosity)
        print "#"

    def has_primary_key(self):
        """Check to see if there is a primary key.
        Returns bool - True - a primary key was found,
                       False - no primary key.
        """
        primary_key = False
        rows = self._get_index_list()
        for row in rows:
            if row[2] == "PRIMARY":
                primary_key = True
        return primary_key

    def has_unique_key(self):
        """Check to see if there is a unique key.
        Returns bool - True - a unique key was found,
                       False - no unique key.
        """
        unique_key = False
        rows = self._get_index_list()
        for row in rows:
            if row[1] == '0':
                unique_key = True
        return unique_key
