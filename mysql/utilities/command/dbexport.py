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
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307 USA
#

"""
This file contains the export operations that will export object metadata or
table data.
"""

import re
import sys
from mysql.utilities.exception import MySQLUtilError

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

    servers = connect_servers(src_val, None, quiet, "5.1.30")

    source = servers[0]

    # Check user permissions on source for all databases
    for db_name in db_list:
        source_db = Database(source, db_name)
        source_db.check_read_access(src_val["user"], src_val["host"],
                                    skip_views, skip_procs, skip_funcs,
                                    skip_grants, skip_events)

    for db_name in db_list:

        # Get a Database class instance
        db = Database(source, db_name, options)

        # Error is source database does not exist
        if not db.exists():
            raise MySQLUtilError("Source database does not exist - %s" %
                                 db_name)

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
                    if format == "VERTICAL":
                        format_vertical_list(sys.stdout, rows[0], rows[1])
                    elif format == "TAB":
                        format_tabular_list(sys.stdout, rows[0], rows[1],
                                            not no_headers, '\t')
                    elif format == "CSV":
                        format_tabular_list(sys.stdout, rows[0], rows[1],
                                            not no_headers, ',')
                    else:  # default to table format
                        format_tabular_list(sys.stdout, rows[0], rows[1],
                                            True, None, False, True)


    if not quiet:
        print "#...done."

    return True


def _export_row(data_rows, cur_table, col_metadata,
                format, single, skip_blobs, first=False,
                no_headers=False, outfile=None):
    """Export a row

    This method will print a row to stdout based on the format chosen -
    either SQL statements, GRID, CSV, TSV, or VERTICAL.

    datarows[in]       one or more rows for exporting
    cur_table[in]      Table class instance
    col_metadata[in]   metadata about the columns including types and widths
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
    if format != "SQL" and format != "S" and outfile is None:
        outfile = sys.stdout # default file handle
    if format == "SQL" or format == "S":
        if single:
            if single:
                data = data_rows
            else:
                data = data_rows[1]
            blob_rows = []
            for row in data:
                columns = cur_table.get_column_string(row, full_name,
                                                      col_metadata)
                if len(columns[1]) > 0:
                    blob_rows.extend(columns[1])
                row_str = "INSERT INTO %s VALUES%s;" % (full_name, columns[0])
                if outfile is not None:
                    outfile.write(row_str + "\n")
                else:
                    print row_str
        else:
            # Generate bulk insert statements
            data_lists = cur_table.make_bulk_insert(data_rows, db_name,
                                                    col_metadata)
            rows = data_lists[0]
            blob_rows = data_lists[1]

            if len(rows) > 0:
                for row in rows:
                    if outfile is not None:
                        outfile.write("%s;\n" % row)
                    else:
                        print "%s;" % row
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
                    row_str = blob_row[0] % blob_row[1] + ";"
                    if outfile is not None:
                        outfile.write(row_str + "\n")
                    else:
                        print row_str
    elif format == "VERTICAL":
        format_vertical_list(outfile, cur_table.get_col_names(col_metadata),
                             data_rows)
    elif format == "TAB":
        format_tabular_list(outfile, cur_table.get_col_names(col_metadata),
                            data_rows, first, '\t', not no_headers)
    elif format == "CSV":
        format_tabular_list(outfile, cur_table.get_col_names(col_metadata),
                            data_rows, first, ',', not no_headers)
    else:  # default to table format - header is always printed
        format_tabular_list(outfile, cur_table.get_col_names(col_metadata),
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

    from mysql.utilities.common.database import Database
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

    servers = connect_servers(src_val, None, quiet, "5.1.30")

    source = servers[0]

    # Check user permissions on source for all databases
    for db_name in db_list:
        source_db = Database(source, db_name)
        source_db.check_read_access(src_val["user"], src_val["host"],
                                    skip_views, skip_procs, skip_funcs,
                                    skip_grants, skip_events)

    for db_name in db_list:

        # Get a Database class instance
        db = Database(source, db_name, options)

        # Error is source database does not exist
        if not db.exists():
            raise MySQLUtilError("Source database does not exist - %s" %
                                 db_name)

        if not quiet:
            if format == "SQL":
                print "USE %s;" % db_name
            print "# Exporting data from %s" % db_name
            if file_per_table:
                print "# Writing table data to files."

        # Perform the extraction
        tables = db.get_db_objects("TABLE")
        if len(tables) < 1:
            break
        for table in tables:
            tbl_name = "%s.%s" % (db_name, table[0])
            cur_table = Table(source, tbl_name, False, True)
            col_metadata = cur_table.get_column_metadata()
            if single and format not in ("SQL", "GRID", "VERTICAL"):
                retrieval_mode = -1
                first = True
            else:
                retrieval_mode = 1
                first = False

            message = "# Data for table %s: " % tbl_name

            # switch for writing to files
            if file_per_table:
                if format == "SQL" or format == "S":
                    file_name = tbl_name + ".sql"
                else:
                    file_name = tbl_name + ".%s" % format.lower()
                outfile = open(file_name, "w")
                outfile.write(message + "\n")
            else:
                outfile = None
                print message

            for data_rows in cur_table.retrieve_rows(retrieval_mode):
                _export_row(data_rows, cur_table, col_metadata,
                            format, single, skip_blobs, first, no_headers,
                            outfile)
                if first:
                    first = False

            if file_per_table:
                outfile.close()


    if not quiet:
        print "#...done."

    return True
