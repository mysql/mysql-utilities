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
This file contains the export operations that will export object metadata or
table data.
"""

import re
import sys
from mysql.utilities.exception import UtilDBError

def export_metadata(src_val, db_list, options):
    """Produce rows to be used to recreate objects in a database.

    This method retrieves the objects for each database listed in the form
    of CREATE (SQL) statements or in a tabular form to the file specified.
    The valid values for the format parameter are SQL, CSV, TSV, VERTICAL,
    or GRID.

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

    from mysql.utilities.common.database import Database
    from mysql.utilities.common.server import connect_servers
    from mysql.utilities.common.format import format_tabular_list
    from mysql.utilities.common.format import format_vertical_list

    format = options.get("format", "SQL")
    no_headers = options.get("no_headers", False)
    column_type = options.get("display", "BRIEF")
    skip_create = options.get("skip_create", False)
    quiet = options.get("quiet", False)
    skip_tables = options.get("skip_tables", False)
    skip_views = options.get("skip_views", False)
    skip_triggers = options.get("skip_triggers", False)
    skip_procs = options.get("skip_procs", False)
    skip_funcs = options.get("skip_funcs", False)
    skip_events = options.get("skip_events", False)
    skip_grants = options.get("skip_grants", False)

    conn_options = {
        'quiet'     : quiet,
        'version'   : "5.1.30",
    }
    servers = connect_servers(src_val, None, conn_options)

    source = servers[0]

    if options.get("all", False):
        rows = source.get_all_databases()
        for row in rows:
            db_list.append(row[0])

    # Check user permissions on source for all databases
    for db_name in db_list:
        source_db = Database(source, db_name)
        # Make a dictionary of the options
        access_options = {
            'skip_views'  : skip_views,
            'skip_procs'  : skip_procs,
            'skip_funcs'  : skip_funcs,
            'skip_grants' : skip_grants,
            'skip_events' : skip_events,
        }

        source_db.check_read_access(src_val["user"], src_val["host"],
                                    access_options)
    
    for db_name in db_list:

        # Get a Database class instance
        db = Database(source, db_name, options)

        # Error is source database does not exist
        if not db.exists():
            raise UtilDBError("Source database does not exist - %s" % db_name,
                              -1, db_name)

        if not quiet:
            print "# Exporting metadata from %s" % db_name

        # Perform the extraction
        if format == "SQL":
            db.init()
            if not skip_create:
                print "DROP DATABASE IF EXISTS %s;" % db_name
                print "CREATE DATABASE %s;" % db_name
            print "USE %s;" % db_name
            for dbobj in db.get_next_object():
                if dbobj[0] == "GRANT" and not skip_grants:
                    if not quiet:
                        print "# Grant:"
                    if dbobj[1][3]:
                        create_str = "GRANT %s ON %s.%s TO %s" % \
                                     (dbobj[1][1], db_name,
                                      dbobj[1][3], dbobj[1][0])
                    else:
                        create_str = "GRANT %s ON %s.* TO %s" % \
                                     (dbobj[1][1], db_name, dbobj[1][0])
                    if create_str.find("%"):
                        create_str = re.sub("%", "%%", create_str)
                    print create_str
                else:
                    if not quiet:
                        print "# %s: %s.%s" % (dbobj[0], db_name,
                                               dbobj[1][0])
                    if (dbobj[0] == "PROCEDURE" and not skip_procs) or \
                       (dbobj[0] == "FUNCTION" and not skip_funcs) or \
                       (dbobj[0] == "EVENT" and not skip_events) or \
                       (dbobj[0] == "TRIGGER" and not skip_triggers):
                        print "DELIMITER ||"
                    print "%s;" % db.get_create_statement(db_name,
                                                          dbobj[1][0],
                                                          dbobj[0])
                    if (dbobj[0] == "PROCEDURE" and not skip_procs) or \
                       (dbobj[0] == "FUNCTION" and not skip_funcs) or \
                       (dbobj[0] == "EVENT" and not skip_events) or \
                       (dbobj[0] == "TRIGGER" and not skip_triggers):
                        print "||"
                        print "DELIMITER ;"
        else:
            objects = []
            if not skip_tables:
                objects.append("TABLE")
            if not skip_views:
                objects.append("VIEW")
            if not skip_triggers:
                objects.append("TRIGGER")
            if not skip_procs:
                objects.append("PROCEDURE")
            if not skip_funcs:
                objects.append("FUNCTION")
            if not skip_events:
                objects.append("EVENT")
            if not skip_grants:
                objects.append("GRANT")
            for obj_type in objects:
                sys.stdout.write("# %sS in %s:" % (obj_type, db_name))
                rows = db.get_db_objects(obj_type, column_type, True)
                if len(rows[1]) < 1:
                    print " (none found)"
                else:
                    print
                    # Cannot use print_list here becasue we must manipulate
                    # the behavior of format_tabular_list
                    list_options = {}
                    if format == "VERTICAL":
                        format_vertical_list(sys.stdout, rows[0], rows[1])
                    elif format == "TAB":
                        list_options['print_header'] = not no_headers
                        list_options['separator'] = '\t'
                        format_tabular_list(sys.stdout, rows[0], rows[1],
                                            list_options)
                    elif format == "CSV":
                        list_options['print_header'] = not no_headers
                        list_options['separator'] = ','
                        format_tabular_list(sys.stdout, rows[0], rows[1],
                                            list_options)
                    else:  # default to table format
                        format_tabular_list(sys.stdout, rows[0], rows[1])

    if not quiet:
        print "#...done."

    return True


def _export_row(data_rows, cur_table, format, single, skip_blobs, first=False,
                no_headers=False, outfile=None):
    """Export a row

    This method will print a row to stdout based on the format chosen -
    either SQL statements, GRID, CSV, TSV, or VERTICAL.

    datarows[in]       one or more rows for exporting
    cur_table[in]      Table class instance
    format[in]         desired output format
    skip_blobs[in]     if True, skip blob data
    single[in]         if True, generate single INSERT statements (valid
                       only for format=SQL)
    first[in]          if True, this is the first row to be exported - this
                       causes the header to be printed if chosen.
    no_headers[in]     if True, do not print headers
    outfile[in]        if is not None, write table data to this file.
    """
    from mysql.utilities.common.format import format_tabular_list
    from mysql.utilities.common.format import format_vertical_list

    tbl_name = cur_table.tbl_name
    db_name = cur_table.db_name
    full_name = "%s.%s" % (db_name, tbl_name)
    list_options = {}
    # if outfile is not set, use stdout.
    if outfile is None:
        outfile = sys.stdout # default file handle
    if format in ('SQL', 'S'):
        if single:
            if single:
                data = data_rows
            else:
                data = data_rows[1]
            blob_rows = []
            for row in data:
                columns = cur_table.get_column_string(row, full_name)
                if len(columns[1]) > 0:
                    blob_rows.extend(columns[1])
                row_str = "INSERT INTO %s VALUES%s;" % (full_name, columns[0])
                outfile.write(row_str + "\n")
        else:
            # Generate bulk insert statements
            data_lists = cur_table.make_bulk_insert(data_rows, db_name)
            rows = data_lists[0]
            blob_rows = data_lists[1]

            if len(rows) > 0:
                for row in rows:
                    outfile.write("%s;\n" % row)
            else:
                print "# Table %s has no data." % tbl_name

        if len(blob_rows) > 0:
            if skip_blobs:
                print "# WARNING : Table %s has blob data that " \
                      "has been excluded by --skip-blobs." % \
                      tbl_name
            else:
                print "# Blob data for table %s:" % tbl_name
                for blob_row in blob_rows:
                    outfile.write(blob_row + "\n")

    # Cannot use print_list here becasue we must manipulate
    # the behavior of format_tabular_list
    elif format == "VERTICAL":
        format_vertical_list(outfile, cur_table.get_col_names(),
                             data_rows)
    elif format == "TAB":
        list_options['print_header'] = first
        list_options['separator'] = '\t'
        list_options['quiet'] = not no_headers
        format_tabular_list(outfile, cur_table.get_col_names(),
                            data_rows, list_options)
    elif format == "CSV":
        list_options['print_header'] = first
        list_options['separator'] = ','
        list_options['quiet'] = not no_headers
        format_tabular_list(outfile, cur_table.get_col_names(),
                            data_rows, list_options)
    else:  # default to table format - header is always printed
        format_tabular_list(outfile, cur_table.get_col_names(),
                            data_rows)


def export_data(src_val, db_list, options):
    """Produce data for the tables in a database.

    This method retrieves the data for each table in the databases listed in
    the form of BULK INSERT (SQL) statements or in a tabular form to the file
    specified. The valid values for the format parameter are SQL, CSV, TSV,
    VERITCAL, or GRID.

    src_val[in]        a dictionary containing connection information for the
                       source including:
                       (user, password, host, port, socket)
    options[in]        a dictionary containing the options for the copy:
                       (skip_tables, skip_views, skip_triggers, skip_procs,
                       skip_funcs, skip_events, skip_grants, skip_create,
                       skip_data, no_header, display, format, file_per_tbl,
                       and debug)

    Returns bool True = success, False = error
    """

    from mysql.utilities.command.dbcopy import get_copy_lock
    from mysql.utilities.common.database import Database
    from mysql.utilities.common.lock import Lock
    from mysql.utilities.common.table import Table
    from mysql.utilities.common.server import connect_servers

    format = options.get("format", "SQL")
    no_headers = options.get("no_headers", True)
    column_type = options.get("display", "BRIEF")
    single = options.get("single", False)
    skip_blobs = options.get("skip_blobs", False)
    quiet = options.get("quiet", False)
    file_per_table = options.get("file_per_tbl", False)
    skip_views = options.get("skip_views", False)
    skip_procs = options.get("skip_procs", False)
    skip_funcs = options.get("skip_funcs", False)
    skip_events = options.get("skip_events", False)
    skip_grants = options.get("skip_grants", False)
    locking = options.get("locking", "snapshot")
    my_lock = None

    conn_options = {
        'quiet'     : quiet,
        'version'   : "5.1.30",
    }
    servers = connect_servers(src_val, None, conn_options)

    source = servers[0]

    if options.get("all", False):
        rows = source.get_all_databases()
        for row in rows:
            if row[0] not in db_list:
                db_list.append(row[0])

    # Check if database exists and user permissions on source for all databases
    table_lock_list = []
    table_list = []
    for db_name in db_list:
        source_db = Database(source, db_name)

        # Make a dictionary of the options
        access_options = {
            'skip_views'  : skip_views,
            'skip_procs'  : skip_procs,
            'skip_funcs'  : skip_funcs,
            'skip_grants' : skip_grants,
            'skip_events' : skip_events,
        }

        # Error is source database does not exist
        if not source_db.exists():
            raise UtilDBError("Source database does not exist - %s" % db_name,
                              -1, db_name)
            
        source_db.check_read_access(src_val["user"], src_val["host"],
                                    access_options)
        
        # Build table list
        # if this is a lock-all type, find all tables for locking
        tables = source_db.get_db_objects("TABLE")
        for table in tables:
            table_list.append((db_name, table[0]))
            if locking == 'lock-all':
                table_lock_list.append(("%s.%s" % (db_name, table[0]),
                                        'READ'))

    my_lock = get_copy_lock(source, table_lock_list, options, True)        
        
    old_db = ""
    for table in table_list:
        db_name = table[0]
        tbl_name = "%s.%s" % (db_name, table[1])
        if not quiet and old_db != db_name:
            old_db = db_name
            if format == "SQL":
               print "USE %s;" % db_name
            print "# Exporting data from %s" % db_name
            if file_per_table:
                print "# Writing table data to files."

        tbl_options = {
            'verbose'  : False,
            'get_cols' : True,
            'quiet'    : quiet
        }
        cur_table = Table(source, tbl_name, tbl_options)
        if single and format not in ("SQL", "GRID", "VERTICAL"):
            retrieval_mode = -1
            first = True
        else:
            retrieval_mode = 1
            first = False

        message = "# Data for table %s: " % tbl_name

        # switch for writing to files
        if file_per_table:
            if format in ('SQL', 'S'):
               file_name = tbl_name + ".sql"
            else:
                file_name = tbl_name + ".%s" % format.lower()
            outfile = open(file_name, "w")
            outfile.write(message + "\n")
        else:
            outfile = None
            print message

        for data_rows in cur_table.retrieve_rows(retrieval_mode):
            _export_row(data_rows, cur_table, format, single,
                        skip_blobs, first, no_headers, outfile)
            if first:
               first = False
 
        if file_per_table:
            outfile.close()
  
    my_lock.unlock()

    if not quiet:
        print "#...done."

    return True
