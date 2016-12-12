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
This file contains the export operations that will export object metadata or
table data.
"""

import multiprocessing
import os
import shutil
import sys
import tempfile

from mysql.utilities.common.database import Database
from mysql.utilities.common.format import (format_tabular_list,
                                           format_vertical_list)
from mysql.utilities.common.lock import Lock
from mysql.utilities.common.replication import negotiate_rpl_connection
from mysql.utilities.common.server import connect_servers, Server
from mysql.utilities.common.sql_transform import quote_with_backticks
from mysql.utilities.common.table import Table
from mysql.utilities.exception import UtilError, UtilDBError


_RPL_COMMANDS, _RPL_FILE = 0, 1
_RPL_PREFIX = "--"
_SESSION_BINLOG_OFF1 = "SET @MYSQLUTILS_TEMP_LOG_BIN = @@SESSION.SQL_LOG_BIN;"
_SESSION_BINLOG_OFF2 = "SET @@SESSION.SQL_LOG_BIN = 0;"
_SESSION_BINLOG_ON = "SET @@SESSION.SQL_LOG_BIN = @MYSQLUTILS_TEMP_LOG_BIN;"
_GET_GTID_EXECUTED = "SELECT @@GLOBAL.GTID_EXECUTED"
_SET_GTID_PURGED = "SET @@GLOBAL.GTID_PURGED = '{0}';"
_GTID_WARNING = ("# WARNING: The server supports GTIDs but you have elected "
                 "to skip generating the GTID_EXECUTED statement. Please "
                 "refer to the MySQL online reference manual for more "
                 "information about how to handle GTID enabled servers with "
                 "backup and restore operations.\n")
_GTID_BACKUP_WARNING = ("# WARNING: A partial export from a server that has "
                        "GTIDs enabled will by default include the GTIDs of "
                        "all transactions, even those that changed suppressed "
                        "parts of the database. If you don't want to generate "
                        "the GTID statement, use the --skip-gtid option. To "
                        "export all databases, use the --all and "
                        "--export=both options.\n")
_FKEYS = ("SELECT DISTINCT constraint_schema "
          "FROM INFORMATION_SCHEMA.referential_constraints "
          "WHERE constraint_schema in ({0})")
_FKEYS_SWITCH = "SET FOREIGN_KEY_CHECKS={0};"
_AUTO_INC_WARNING = ("#\n# WARNING: One or more tables were detected with a "
                     "value of 0 in an auto_increment column. If you want "
                     "to import the data, you must enable the SQL_MODE '"
                     "NO_AUTO_VALUE_ON_ZERO' during the import. Failure to "
                     "do so may result in the wrong value used for the "
                     "rows with 0 as the auto_increment value. The following "
                     "statement is an example taken from the source server. "
                     "Uncomment and adjust this statement as needed for the "
                     "destination server.")


def check_read_permissions(server, db_list, options):
    """
    Check user permissions on server for specified databases.

    This method checks if the user used to establish the connection to the
    server has read permissions to access the specified lists of databases.

    server[in]      Server instance.
    db_list[in]     List of databases to check.
    options[in]     Dictionary with access options:
        skip_views     True = no views processed
        skip_proc      True = no procedures processed
        skip_func      True = no functions processed
        skip_grants    True = no grants processed
        skip_events    True = no events processed

    Returns an UtilDBError error if the server user does not have read
    permissions to access all specified databases or if any of them does not
    exist.
    """
    for db_name in db_list:
        source_db = Database(server, db_name, options)

        # Error if source database does not exist.
        if not source_db.exists():
            raise UtilDBError("Source database does not exist - "
                              "{0}".format(db_name), -1, db_name)

        # Check privileges to access database.
        source_db.check_read_access(server.user, server.host, options)


def export_metadata(server_values, db_list, options):
    """Produce rows to be used to recreate objects in a database.

    This method retrieves the objects for each database listed in the form
    of CREATE (SQL) statements or in a tabular form to the file specified.
    The valid values for the format parameter are SQL, CSV, TSV, VERTICAL,
    or GRID.

    server_values[in]  server connection value dictionary.
    src_val[in]        a dictionary containing connection information for the
                       source including:
                       (user, password, host, port, socket)
    options[in]        a dictionary containing the options for the copy:
                       (skip_tables, skip_views, skip_triggers, skip_procs,
                       skip_funcs, skip_events, skip_grants, skip_create,
                       skip_data, no_header, display, format,
                       debug, exclude_names, exclude_patterns)

    Returns bool True = success, False = error
    """
    # Connect to source server.
    quiet = options.get("quiet", False)
    conn_options = {
        'quiet': quiet,
        'version': "5.1.30",
    }
    servers = connect_servers(server_values, None, conn_options)
    source = servers[0]

    if options.get("all", False):
        rows = source.get_all_databases()
        for row in rows:
            if row[0] not in db_list:
                db_list.append(row[0])

    # Check user permissions on source for all databases.
    check_read_permissions(source, db_list, options)

    # Export databases metadata.
    _export_metadata(source, db_list, None, options)

    return True


def _export_metadata(source, db_list, output_file, options):
    """Export metadata from the specified list of databases.

    This private method retrieves the objects metadata for each database listed
    in the form of CREATE (SQL) statements or in a tabular form (GRID, TAB,
    CSV, VERTICAL) to the specified file.

    This private method does not check permissions.

    source[in]         Server instance.
    db_list[in]        List of databases to export.
    output_file[in]    Output file to store the metadata information.
    options[in]        Dictionary containing the options for the export:
                       (skip_tables, skip_views, skip_triggers, skip_procs,
                       skip_funcs, skip_events, skip_grants, skip_create,
                       skip_data, no_header, display, format,
                       debug, exclude_names, exclude_patterns)
    """
    frmt = options.get("format", "sql")
    no_headers = options.get("no_headers", False)
    column_type = options.get("display", "brief")
    quiet = options.get("quiet", False)
    skip_create = options.get("skip_create", False)
    skip_tables = options.get("skip_tables", False)
    skip_views = options.get("skip_views", False)
    skip_triggers = options.get("skip_triggers", False)
    skip_procs = options.get("skip_procs", False)
    skip_funcs = options.get("skip_funcs", False)
    skip_events = options.get("skip_events", False)
    skip_grants = options.get("skip_grants", False)
    sql_mode = source.select_variable("SQL_MODE")

    for db_name in db_list:

        # Get a Database class instance
        db = Database(source, db_name, options)

        # Export database metadata
        if not quiet:
            output_file.write(
                "# Exporting metadata from {0}\n".format(db.q_db_name)
            )

        # Perform the extraction
        if frmt == "sql":
            db.init()
            if not skip_create:
                output_file.write(
                    "DROP DATABASE IF EXISTS {0};\n".format(db.q_db_name)
                )
                output_file.write(
                    "CREATE DATABASE {0};\n".format(db.q_db_name)
                )
            output_file.write("USE {0};\n".format(db.q_db_name))
            for dbobj in db.get_next_object():
                if dbobj[0] == "GRANT" and not skip_grants:
                    if not quiet:
                        output_file.write("# Grant:\n")
                    if dbobj[1][3]:
                        create_str = "GRANT {0} ON {1}.{2} TO {3};\n".format(
                            dbobj[1][1], db.q_db_name,
                            quote_with_backticks(dbobj[1][3], sql_mode),
                            dbobj[1][0]
                        )
                    else:
                        create_str = "GRANT {0} ON {1}.* TO {2};\n".format(
                            dbobj[1][1], db.q_db_name, dbobj[1][0]
                        )
                    output_file.write(create_str)
                else:
                    if not quiet:
                        output_file.write(
                            "# {0}: {1}.{2}\n".format(
                                dbobj[0], db.q_db_name,
                                quote_with_backticks(dbobj[1][0], sql_mode)
                            )
                        )
                    if (dbobj[0] == "PROCEDURE" and not skip_procs) or \
                       (dbobj[0] == "FUNCTION" and not skip_funcs) or \
                       (dbobj[0] == "EVENT" and not skip_events) or \
                       (dbobj[0] == "TRIGGER" and not skip_triggers):
                        output_file.write("DELIMITER ||\n")
                    output_file.write("{0};\n".format(
                        db.get_create_statement(db.db_name, dbobj[1][0],
                                                dbobj[0])
                    ))
                    if (dbobj[0] == "PROCEDURE" and not skip_procs) or \
                       (dbobj[0] == "FUNCTION" and not skip_funcs) or \
                       (dbobj[0] == "EVENT" and not skip_events) or \
                       (dbobj[0] == "TRIGGER" and not skip_triggers):
                        output_file.write("||\n")
                        output_file.write("DELIMITER ;\n")
        else:
            objects = []
            if not skip_tables:
                objects.append("TABLE")
            if not skip_funcs:
                objects.append("FUNCTION")
            if not skip_procs:
                objects.append("PROCEDURE")
            if not skip_views:
                objects.append("VIEW")
            if not skip_triggers:
                objects.append("TRIGGER")
            if not skip_events:
                objects.append("EVENT")
            if not skip_grants:
                objects.append("GRANT")
            for obj_type in objects:
                output_file.write(
                    "# {0}S in {1}:".format(obj_type, db.q_db_name)
                )
                if frmt in ('grid', 'vertical'):
                    rows = db.get_db_objects(obj_type, column_type, True)
                else:
                    rows = db.get_db_objects(obj_type, column_type, True, True)
                if len(rows[1]) < 1:
                    output_file.write(" (none found)\n")
                else:
                    output_file.write("\n")
                    # Cannot use print_list here because we must manipulate
                    # the behavior of format_tabular_list.
                    list_options = {}
                    if frmt == "vertical":
                        format_vertical_list(output_file, rows[0], rows[1])
                    elif frmt == "tab":
                        list_options['print_header'] = not no_headers
                        list_options['separator'] = '\t'
                        format_tabular_list(output_file, rows[0], rows[1],
                                            list_options)
                    elif frmt == "csv":
                        list_options['print_header'] = not no_headers
                        list_options['separator'] = ','
                        format_tabular_list(output_file, rows[0], rows[1],
                                            list_options)
                    else:  # default to table format
                        format_tabular_list(output_file, rows[0], rows[1])

    if not quiet:
        output_file.write("#...done.\n")


def _export_row(data_rows, cur_table, out_format, single, skip_blobs,
                first=False, no_headers=False, outfile=None):
    """Export a row

    This method will print a row to stdout based on the format chosen -
    either SQL statements, GRID, CSV, TSV, or VERTICAL.

    datarows[in]       one or more rows for exporting
    cur_table[in]      Table class instance
    out_format[in]     desired output format
    skip_blobs[in]     if True, skip blob data
    single[in]         if True, generate single INSERT statements (valid
                       only for format=SQL)
    first[in]          if True, this is the first row to be exported - this
                       causes the header to be printed if chosen.
    no_headers[in]     if True, do not print headers
    outfile[in]        if is not None, write table data to this file.
    """
    tbl_name = cur_table.tbl_name
    q_db_name = cur_table.q_db_name
    full_name = cur_table.q_table
    list_options = {'none_to_null': True}
    # if outfile is not set, use stdout.
    if outfile is None:
        outfile = sys.stdout  # default file handle
    if out_format == 'sql':
        if single:
            if single:
                data = data_rows
            else:
                data = data_rows[1]
            blob_rows = []
            for row in data:
                columns = cur_table.get_column_string(row, q_db_name,
                                                      skip_blobs)
                if len(columns[1]) > 0:
                    blob_rows.extend(columns[1])
                if columns[0]:
                    row_str = "INSERT INTO {0} VALUES{1};\n".format(full_name,
                                                                    columns[0])
                    outfile.write(row_str)
        else:
            # Generate bulk insert statements
            data_lists = cur_table.make_bulk_insert(data_rows, q_db_name,
                                                    skip_blobs=skip_blobs)
            rows = data_lists[0]
            blob_rows = data_lists[1]

            if len(rows) > 0:
                for row in rows:
                    outfile.write("{0};\n".format(row))
            else:
                outfile.write("# Table {0} has no data.\n"
                              "".format(cur_table.q_tbl_name))
        if len(blob_rows) > 0:
            if skip_blobs:
                outfile.write("# WARNING : Table {0} has blob data that "
                              "has been excluded by --skip-blobs."
                              "\n".format(cur_table.q_tbl_name))
            else:
                outfile.write("# Blob data for table "
                              "{0}:\n".format(cur_table.q_tbl_name))
                for blob_row in blob_rows:
                    outfile.write("{0}\n".format(blob_row))

    # Cannot use print_list here because we must manipulate
    # the behavior of format_tabular_list
    elif out_format == "vertical":
        format_vertical_list(outfile, cur_table.get_col_names(),
                             data_rows, list_options)
    elif out_format == "tab":
        list_options['print_header'] = first
        list_options['separator'] = '\t'
        list_options['quiet'] = not no_headers
        format_tabular_list(outfile, cur_table.get_col_names(True),
                            data_rows, list_options)
    elif out_format == "csv":
        list_options['print_header'] = first
        list_options['separator'] = ','
        list_options['quiet'] = not no_headers
        format_tabular_list(outfile, cur_table.get_col_names(True),
                            data_rows, list_options)
    else:  # default to table format - header is always printed
        format_tabular_list(outfile, cur_table.get_col_names(),
                            data_rows, list_options)


def export_data(server_values, db_list, options):
    """Produce data for the tables in a database.

    This method retrieves the data for each table in the databases listed in
    the form of BULK INSERT (SQL) statements or in a tabular form to the file
    specified. The valid values for the format parameter are SQL, CSV, TSV,
    VERITCAL, or GRID.

    server_values[in]  server connection value dictionary.
    options[in]        a dictionary containing the options for the copy:
                       (skip_tables, skip_views, skip_triggers, skip_procs,
                       skip_funcs, skip_events, skip_grants, skip_create,
                       skip_data, no_header, display, format, file_per_tbl,
                       and debug).

    Returns bool True = success, False = error
    """
    # Connect to source server.
    quiet = options.get("quiet", False)
    conn_options = {
        'quiet': quiet,
        'version': "5.1.30",
    }
    servers = connect_servers(server_values, None, conn_options)
    source = servers[0]

    # Check user permissions on source for all databases.
    check_read_permissions(source, db_list, options)

    # Export databases data.
    _export_data(source, server_values, db_list, None, options)

    return True


def _export_data(source, server_values, db_list, output_file, options):
    """Export data from the specified list of databases.

    This private method retrieves the data for each specified databases in SQL
    format (e.g., INSERT statements) or in a tabular form (GRID, TAB, CSV,
    VERTICAL) to the specified file.

    This private method does not check permissions.

    source[in]         Server instance.
    server_values[in]  Server connection values.
    db_list[in]        List of databases to export.
    output_file[in]    Output file to store the export data.
    options[in]        Dictionary containing the options for the export:
                       (skip_tables, skip_views, skip_triggers, skip_procs,
                       skip_funcs, skip_events, skip_grants, skip_create,
                       skip_data, no_header, display, format, file_per_tbl,
                       and debug).
    """
    frmt = options.get("format", "sql")
    quiet = options.get("quiet", False)
    file_per_table = options.get("file_per_tbl", False)
    sql_mode = source.select_variable("SQL_MODE")

    # Get tables list.
    table_list = []
    for db_name in db_list:
        source_db = Database(source, db_name, options)
        # Build table list.
        tables = source_db.get_db_objects("TABLE")
        for table in tables:
            table_list.append((db_name, table[0]))

    previous_db = ""
    export_tbl_tasks = []
    for table in table_list:

        # Determine start for processing table from a different database.
        db_name = table[0]
        if previous_db != db_name:
            previous_db = db_name
            if not quiet:
                q_db_name = quote_with_backticks(db_name, sql_mode)
                if frmt == "sql":
                    output_file.write("USE {0};\n".format(q_db_name))
                output_file.write(
                    "# Exporting data from {0}\n".format(q_db_name)
                )
                if file_per_table:
                    output_file.write("# Writing table data to files.\n")

            # Print sample SOURCE command warning even in quiet mode.
            if file_per_table and frmt == 'sql':
                output_file.write("# The following are sample SOURCE commands."
                                  " If needed correct the path to match files "
                                  "location.\n")

        # Check multiprocess table export (only on POSIX systems).
        if options['multiprocess'] > 1 and os.name == 'posix':
            # Create export task.
            # Note: Server connection values are passed in the task dictionary
            # instead of a server instance, otherwise a multiprocessing error
            # is issued when assigning the task to a worker.
            export_task = {
                'srv_con': server_values,
                'table': table,
                'options': options,
            }
            export_tbl_tasks.append(export_task)
        else:
            # Export data from a table (no multiprocessing).
            _export_table_data(source, table, output_file, options)

        # Print SOURCE command if --file-per-table is used and format is SQL.
        if file_per_table and frmt == 'sql':
            tbl_name = ".".join(table)
            output_file.write(
                "# SOURCE {0}\n".format(_generate_tbl_filename(tbl_name, frmt))
            )

    # Export tables concurrently.
    if export_tbl_tasks:
        # Create process pool.
        workers_pool = multiprocessing.Pool(
            processes=options['multiprocess']
        )
        # Concurrently export tables.
        res = workers_pool.map_async(multiprocess_tbl_export_task,
                                     export_tbl_tasks)
        workers_pool.close()
        # Get list of temporary files with the exported data.
        tmp_files_list = res.get()
        workers_pool.join()

        # Merge resulting temp files (if generated).
        for tmp_filename in tmp_files_list:
            if tmp_filename:
                tmp_file = open(tmp_filename, 'r')
                shutil.copyfileobj(tmp_file, output_file)
                tmp_file.close()
                os.remove(tmp_filename)

    if not quiet:
        output_file.write("#...done.\n")


def _export_table_data(source_srv, table, output_file, options):
    """Export the table data.

    This private method retrieves the data for the specified table in SQL
    format (e.g., INSERT statements) or in a tabular form (GRID, TAB, CSV,
    VERTICAL) to the specified output file or a separated file, according to
    the defined options.

    source_srv[in]  Server instance or dictionary with connection values.
    table[in]       Table to export, tuple with database name and table name.
    output_file[in] Output file to store the export data.
    options[in]     Dictionary containing the options for the export:
                        (skip_tables, skip_views, skip_triggers, skip_procs,
                        skip_funcs, skip_events, skip_grants, skip_create,
                        skip_data, no_header, display, format, file_per_tbl,
                        and debug).

    return a filename if a temporary file is created to store the output result
    (used for multiprocessing) otherwise None.
    """
    frmt = options.get("format", "sql")
    no_headers = options.get("no_headers", True)
    single = options.get("single", False)
    skip_blobs = options.get("skip_blobs", False)
    quiet = options.get("quiet", False)
    file_per_table = options.get("file_per_tbl", False)

    # Handle source server instance or server connection values.
    # Note: For multiprocessing the use of connection values instead of a
    # server instance is required to avoid internal errors.
    if isinstance(source_srv, Server):
        source = source_srv
    else:
        # Get source server instance from connection values.
        conn_options = {
            'quiet': True,  # Avoid repeating output for multiprocessing.
            'version': "5.1.30",
        }
        servers = connect_servers(source_srv, None, conn_options)
        source = servers[0]

    # Must be after the connection test to get SQL_MODE
    sql_mode = source.select_variable("SQL_MODE")

    # Handle qualified table name (with backtick quotes).
    db_name = table[0]
    tbl_name = "{0}.{1}".format(db_name, table[1])
    q_db_name = quote_with_backticks(db_name, sql_mode)
    q_tbl_name = "{0}.{1}".format(q_db_name, quote_with_backticks(table[1],
                                                                  sql_mode))

    # Determine output file to store exported table data.
    if file_per_table:
        # Store result of table export to a separated file.
        file_name = _generate_tbl_filename(tbl_name, frmt)
        outfile = open(file_name, "w+")
        tempfile_used = False
    else:
        if output_file:
            # Output file to store result is defined.
            outfile = output_file
            tempfile_used = False
        else:
            # Store result in a temporary file (merged later).
            # Used by multiprocess export.
            tempfile_used = True
            outfile = tempfile.NamedTemporaryFile(delete=False)

    message = "# Data for table {0}:".format(q_tbl_name)
    outfile.write("{0}\n".format(message))

    tbl_options = {
        'verbose': False,
        'get_cols': True,
        'quiet': quiet
    }
    cur_table = Table(source, q_tbl_name, tbl_options)
    if single and frmt not in ("sql", "grid", "vertical"):
        retrieval_mode = -1
        first = True
    else:
        retrieval_mode = 1
        first = False

    # Find if we have some UNIQUE NOT NULL column indexes.
    unique_indexes = len(cur_table.get_not_null_unique_indexes())

    # If all columns are BLOBS or there aren't any UNIQUE NOT NULL indexes
    # then rows won't be correctly copied using the update statement,
    # so we must warn the user.
    if (not skip_blobs and frmt == "sql" and
            (cur_table.blob_columns == len(cur_table.column_names) or
             (not unique_indexes and cur_table.blob_columns))):
        print("# WARNING: Table {0}.{1} contains only BLOB and TEXT "
              "fields. Rows will be generated with separate INSERT "
              "statements.".format(cur_table.q_db_name, cur_table.q_tbl_name))

    for data_rows in cur_table.retrieve_rows(retrieval_mode):
        _export_row(data_rows, cur_table, frmt, single,
                    skip_blobs, first, no_headers, outfile)
        if first:
            first = False

    if file_per_table:
        outfile.close()

    return outfile.name if tempfile_used else None


def _generate_tbl_filename(table_name, output_format):
    """Generate the filename fot the given table.

    Generate the filename based on the specified table name and format to
    export data.

    table_name[in]      Qualified table name (i.e., <db name>.<table name>).
    output_format[in]   Output format to export data.

    return a string with the generated file name.
    """
    # Store result of table export to a separated file.
    if output_format == 'sql':
        return "{0}.sql".format(table_name)
    else:
        return "{0}.{1}".format(table_name, output_format.lower())


def get_copy_lock(server, db_list, options, include_mysql=False,
                  cloning=False):
    """Get an instance of the Lock class with a standard copy (read) lock

    This method creates an instance of the Lock class using the lock type
    specified in the options. It is used to initiate the locks for the copy
    and related operations.

    server[in]             Server instance for locking calls
    db_list[in]            list of database names
    options[in]            option dictionary
                           Must include the skip_* options for copy and export
    include_mysql[in]      if True, include the mysql tables for copy operation
    cloning[in]            if True, create lock tables with WRITE on dest db
                           Default = False

    Returns Lock - Lock class instance
    """
    rpl_mode = options.get("rpl_mode", None)
    locking = options.get('locking', 'snapshot')

    # Determine if we need to use FTWRL. There are two conditions:
    #  - running on master (rpl_mode = 'master')
    #  - using locking = 'lock-all' and rpl_mode present
    if (rpl_mode in ["master", "both"]) or \
            (rpl_mode and locking == 'lock-all'):
        new_opts = options.copy()
        new_opts['locking'] = 'flush'
        lock = Lock(server, [], new_opts)

    # if this is a lock-all type and not replication operation,
    # find all tables and lock them
    # pylint: disable=R0101
    elif locking == 'lock-all':
        table_lock_list = []

        # Build table lock list
        for db_name in db_list:
            db = db_name[0] if isinstance(db_name, tuple) else db_name
            source_db = Database(server, db)
            tables = source_db.get_db_objects("TABLE")
            for table in tables:
                table_lock_list.append(("{0}.{1}".format(db, table[0]),
                                        'READ'))
                # Cloning requires issuing WRITE locks because we use same
                # conn.
                # Non-cloning will issue WRITE lock on a new destination conn.
                if cloning:
                    if db_name[1] is None:
                        db_clone = db_name[0]
                    else:
                        db_clone = db_name[1]
                    # For cloning, we use the same connection so we need to
                    # lock the destination tables with WRITE.
                    table_lock_list.append(("{0}.{1}".format(db_clone,
                                                             table[0]),
                                            'WRITE'))
            # We must include views for server version 5.5.3 and higher
            if server.check_version_compat(5, 5, 3):
                tables = source_db.get_db_objects("VIEW")
                for table in tables:
                    table_lock_list.append(("{0}.{1}".format(db, table[0]),
                                            'READ'))
                    # Cloning requires issuing WRITE locks because we use same
                    # conn.
                    # Non-cloning will issue WRITE lock on a new destination
                    # conn.
                    if cloning:
                        if db_name[1] is None:
                            db_clone = db_name[0]
                        else:
                            db_clone = db_name[1]
                        # For cloning, we use the same connection so we need to
                        # lock the destination tables with WRITE.
                        table_lock_list.append(("{0}.{1}".format(db_clone,
                                                                 table[0]),
                                                'WRITE'))

        # Now add mysql tables
        if include_mysql:
            # Don't lock proc tables if no procs of funcs are being read
            if not options.get('skip_procs', False) and \
               not options.get('skip_funcs', False):
                table_lock_list.append(("mysql.proc", 'READ'))
                table_lock_list.append(("mysql.procs_priv", 'READ'))
            # Don't lock event table if events are skipped
            if not options.get('skip_events', False):
                table_lock_list.append(("mysql.event", 'READ'))
        lock = Lock(server, table_lock_list, options)

    # Use default or no locking option
    else:
        lock = Lock(server, [], options)

    return lock


def get_change_master_command(source, options):
    """Get the CHANGE MASTER command for export or copy of databases

    This method creates the replication commands based on the options chosen.
    This includes the stop and start slave commands as well as the change
    master command as follows.

    To create the CHANGE MASTER command for connecting to the existing server
    as the master, set rpl_mode = 'master'.

    To create the CHANGE MASTER command for using the existing server as the
    master, set rpl_mode = 'master'.

    You can also get both CHANGE MASTER commands by setting rpl_mode = 'both'.
    In this case, the second change master command (rpl_mode = 'slave') will
    be commented out.

    The method also checks the rpl_file option. If a file name is provided, it
    is checked to see if file exists or the user does not have access, an error
    is thrown. If no file is provided, the method writes the commands to
    stdout.

    The user may also comment the replication commands by specifying the
    comment_rpl option (True = comment).

    The method calls the negotiate_rpl_connection method of the replication
    module to create the CHANGE MASTER command. Additional error checking is
    performed in that method as follows. See the negotiate_rpl_connection
    method documentation for complete specifics.

      - binary log must be ON for a master
      - the rpl_user must exist

    source[in]         Server instance
    options[in]        option dictionary

    Returns tuple - CHANGE MASTER command[s], output file for writing commands.
    """
    if options is None:
        options = {}
    rpl_file = None
    rpl_cmds = []

    rpl_filename = options.get("rpl_file", "")
    rpl_mode = options.get("rpl_mode", "master")
    quiet = options.get("quiet", False)

    # Check for rpl_filename and create file.
    if rpl_filename:
        rpl_file = rpl_filename
        try:
            rf = open(rpl_filename, "w")
        except:
            raise UtilError("File inaccessible or bad path: "
                            "{0}".format(rpl_filename))
        rf.write("# Replication Commands:\n")
        rf.close()

    strict = rpl_mode == 'both' or options.get("strict", False)
    # Get change master as if this server was a master
    if rpl_mode in ["master", "both"]:

        if not quiet:
            rpl_cmds.append("# Connecting to the current server as master")

        change_master = negotiate_rpl_connection(source, True, strict, options)

        rpl_cmds.extend(change_master)

    # Get change master using this slave's master information
    if rpl_mode in ["slave", "both"]:

        if not quiet:
            rpl_cmds.append("# Connecting to the current server's master")

        change_master = negotiate_rpl_connection(source, False, strict,
                                                 options)

        rpl_cmds.extend(change_master)

    return rpl_cmds, rpl_file


def get_gtid_commands(master):
    """Get the GTID commands for beginning and ending operations

    This method returns those commands needed at the start of an export/copy
    operation (turn off session binlog, setting GTIDs) and those needed at
    the end of an export/copy operation (turn on binlog session).

    master[in]         Master connection information

    Returns tuple - ([],"") = list of commands for start, command for end or
                              None if GTIDs are not enabled.
    """
    if master.supports_gtid() != "ON":
        return None
    rows = master.exec_query(_GET_GTID_EXECUTED)
    master_gtids_list = ["%s" % row[0] for row in rows]
    master_gtids = ",".join(master_gtids_list)
    if len(master_gtids_list) == 1 and rows[0][0] == '':
        return None
    return ([_SESSION_BINLOG_OFF1, _SESSION_BINLOG_OFF2,
             _SET_GTID_PURGED.format(master_gtids)], _SESSION_BINLOG_ON)


def write_commands(target_file, rows, options, extra_linespacing=False,
                   comment=False, comment_prefix="#"):
    """Write commands to file or stdout

    This method writes the rows passed to either a file specified in the
    rpl_file option or stdout if no file is specified.

    file[in]           filename to use or None for sys.stdout
    rows[in]           rows to write
    options[in]        replication options
    """
    quiet = options.get("quiet", False)
    verbosity = options.get("verbosity", 0)

    # Open the file for append
    if target_file:
        out_file = target_file
    else:
        out_file = sys.stdout

    if extra_linespacing and not quiet and verbosity:
        out_file.write("#\n")

    # Write rows.
    for row in rows:
        if comment:
            if row.startswith(comment_prefix):
                # Row already start with comment prefix, no need to add it.
                out_file.write("{0}\n".format(row))
            else:
                out_file.write("{0} {1}\n".format(comment_prefix, row))
        else:
            out_file.write("{0}\n".format(row))

    if extra_linespacing and not quiet and verbosity:
        out_file.write("#\n")


def multiprocess_db_export_task(export_db_task):
    """Multiprocess export database method.

    This method wraps the export_database method to allow its concurrent
    execution by a pool of processes.

    export_db_task[in]  dictionary of values required by a process to perform
                        the database export task, namely:
                        {'srv_con': <dict with server connections values>,
                         'db_list': <list of databases to export>,
                         'options': <dict of options>,
                        }
    """
    # Get input values to execute task.
    srv_con_values = export_db_task.get('srv_con')
    db_list = export_db_task.get('db_list')
    options = export_db_task.get('options')
    # Create temporay file to hold export data.
    outfile = tempfile.NamedTemporaryFile(delete=False)
    # Execute export databases task.
    # NOTE: Must handle any exception here, because worker processes will not
    # propagate them to the main process.
    try:
        export_databases(srv_con_values, db_list, outfile, options)
        return outfile.name
    except UtilError:
        _, err, _ = sys.exc_info()
        print("ERROR: {0}".format(err.errmsg))
    except:
        _, err, _ = sys.exc_info()
        print("UNEXPECTED ERROR: {0}".format(err.errmsg))


def multiprocess_tbl_export_task(export_tbl_task):
    """Multiprocess export table data method.

    This method wraps the table data export to allow its concurrent execution
    by a pool of processes.

    export_tbl_task[in]     dictionary of values required by a process to
                            perform the table export task, namely:
                            {'srv_con': <dict with server connections values>,
                             'table': <table to export>,
                             'options': <dict of options>,
                            }
    """
    # Get input to execute task.
    source_srv = export_tbl_task.get('srv_con')
    table = export_tbl_task.get('table')
    options = export_tbl_task.get('options')
    # Execute export table task.
    # NOTE: Must handle any exception here, because worker processes will not
    # propagate them to the main process.
    try:
        return _export_table_data(source_srv, table, None, options)
    except UtilError:
        _, err, _ = sys.exc_info()
        print("ERROR exporting data for table '{0}': {1}".format(table,
                                                                 err.errmsg))


def _check_auto_increment(source, db_list, options):
    """Check auto increment values for 0

    If any tables are found to have 0 in the list of databases,
    the code prints a warning along with a sample statement
    that can be used should the user decide she needs it when
    she does the import.

    source[in]      Source connection
    db_list[in]     List of databases to export
    options[in[     Global option list
    """
    for db in db_list:
        db_obj = Database(source, db, options)
        # print warning if any tables have 0 as auto_increment value
        if db_obj.check_auto_increment():
            sql_mode = source.show_server_variable("sql_mode")
            sql_mode_str = "NO_AUTO_VALUE_ON_ZERO"
            if sql_mode[0]:
                sql_mode_str = sql_mode[0][1]
                if 'NO_AUTO_VALUE_ON_ZERO' not in sql_mode[0][1]:
                    sql_mode_str = ("'{0}',NO_AUTO_VALUE_ON_ZERO"
                                    "".format(sql_mode_str))
            print(_AUTO_INC_WARNING)
            print("# SET SQL_MODE = '{0}'\n#".format(sql_mode_str))


def export_databases(server_values, db_list, output_file, options):
    """Export one or more databases

    This method performs the export of a list of databases first dumping the
    definitions then the data. It supports dumping replication commands (STOP
    SLAVE, CHANGE MASTER, START SLAVE) for exporting data for use in
    replication scenarios.

    server_values[in]   server connection value dictionary.
    db_list[in]         list of database names.
    output_file[in]     file to store export output.
    options[in]         option dictionary.
                        Note: Must include the skip_* options for export.
    """
    fkeys_present = False
    export = options.get("export", "definitions")
    rpl_mode = options.get("rpl_mode", "master")
    quiet = options.get("quiet", False)
    skip_gtids = options.get("skip_gtid", False)  # default: generate GTIDs
    skip_fkeys = options.get("skip_fkeys", False)  # default: gen fkeys stmts

    conn_options = {
        'quiet': quiet,
        'version': "5.1.30",
    }
    servers = connect_servers(server_values, None, conn_options)
    source = servers[0]

    # Retrieve all databases, if --all is used.
    if options.get("all", False):
        rows = source.get_all_databases()
        for row in rows:
            if row[0] not in db_list:
                db_list.append(row[0])

    # Check user permissions on source server for all databases.
    check_read_permissions(source, db_list, options)

    # Check for GTID support
    supports_gtid = servers[0].supports_gtid()
    if not skip_gtids and supports_gtid != 'ON':
        skip_gtids = True
    elif skip_gtids and supports_gtid == 'ON':
        output_file.write(_GTID_WARNING)

    if not skip_gtids and supports_gtid == 'ON':
        # Check GTID version for complete feature support
        servers[0].check_gtid_version()
        warning_printed = False
        # Check to see if this is a full export (complete backup)
        all_dbs = servers[0].exec_query("SHOW DATABASES")
        for db in all_dbs:
            if warning_printed:
                continue
            # Internal databases 'sys' added by default for MySQL 5.7.7+.
            if db[0].upper() in ["MYSQL", "INFORMATION_SCHEMA",
                                 "PERFORMANCE_SCHEMA", "SYS"]:
                continue
            if db[0] not in db_list:
                output_file.write(_GTID_BACKUP_WARNING)
                warning_printed = True

    # Check for existence of foreign keys
    fkeys_enabled = servers[0].foreign_key_checks_enabled()
    if fkeys_enabled and skip_fkeys:
        output_file.write("# WARNING: Output contains tables with foreign key "
                          "contraints. You should disable foreign key checks "
                          "prior to importing this stream.\n")
    elif fkeys_enabled and db_list:
        db_name_list = ["'{0}'".format(db) for db in db_list]
        res = source.exec_query(_FKEYS.format(",".join(db_name_list)))
        if res and res[0]:
            fkeys_present = True
            write_commands(output_file, [_FKEYS_SWITCH.format("0")], options,
                           True)

    # Lock tables first
    my_lock = get_copy_lock(source, db_list, options, True)

    # Determine comment prefix for rpl commands.
    rpl_cmt_prefix = ""
    rpl_cmt = False
    if options.get("comment_rpl", False) or rpl_mode == "both":
        rpl_cmt_prefix = "#"
        rpl_cmt = True
    if options.get("format", "sql") != 'sql':
        rpl_cmt_prefix = _RPL_PREFIX
        rpl_cmt = True

    # if --rpl specified, write initial replication command
    rpl_info = None
    rpl_file = None
    if rpl_mode:
        rpl_info = get_change_master_command(source, options)
        if rpl_info[_RPL_FILE]:
            rpl_file = open(rpl_info[_RPL_FILE], 'w')
        else:
            rpl_file = output_file
        write_commands(rpl_file, ["STOP SLAVE;"], options, True, rpl_cmt,
                       rpl_cmt_prefix)

    # if GTIDs enabled and user requested the output, write the GTID commands
    if skip_gtids:
        gtid_info = None
    else:
        gtid_info = get_gtid_commands(source)

    if gtid_info:
        write_commands(output_file, gtid_info[0], options, True, rpl_cmt,
                       rpl_cmt_prefix)

    # Checking auto increment. See if any tables have 0 in their auto
    # increment column.
    _check_auto_increment(source, db_list, options)

    # dump metadata
    if export in ("definitions", "both"):
        _export_metadata(source, db_list, output_file, options)

    # dump data
    if export in ("data", "both"):
        if options.get("display", "brief") != "brief":
            output_file.write(
                "# NOTE : --display is ignored for data export.\n"
            )
        _export_data(source, server_values, db_list, output_file, options)

    # if GTIDs enabled, write the GTID-related commands
    if gtid_info:
        write_commands(output_file, [gtid_info[1]], options, True, rpl_cmt,
                       rpl_cmt_prefix)
    # if --rpl specified, write replication end command
    if rpl_mode:
        write_commands(rpl_file, rpl_info[_RPL_COMMANDS], options,
                       True, rpl_cmt, rpl_cmt_prefix)
        write_commands(rpl_file, ["START SLAVE;"], options, True,
                       rpl_cmt, rpl_cmt_prefix)
        # Last command wrote rpl_file, close it.
        if rpl_info[_RPL_FILE]:
            rpl_file.close()

    my_lock.unlock()

    if fkeys_present and fkeys_enabled and not skip_fkeys:
        write_commands(output_file, [_FKEYS_SWITCH.format("1")], options, True)
