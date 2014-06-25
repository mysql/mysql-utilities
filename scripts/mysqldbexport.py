#!/usr/bin/env python
#
# Copyright (c) 2010, 2014, Oracle and/or its affiliates. All rights reserved.
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
This file contains the export database utility which allows users to export
metadata for objects in a database and data for tables.
"""

from mysql.utilities.common.tools import check_python_version

# Check Python version compatibility
check_python_version()

import multiprocessing
import os
import shutil
import sys
import tempfile
import time

from mysql.utilities.command.dbexport import export_databases
from mysql.utilities.command.dbexport import multiprocess_db_export_task
from mysql.utilities.common.ip_parser import parse_connection
from mysql.utilities.common.options import (
    add_all, add_character_set_option, add_format_option, add_locking,
    add_no_headers_option, add_regexp, add_rpl_mode, add_rpl_user,
    add_skip_options, add_verbosity, check_all, check_rpl_options,
    check_skip_options, check_verbosity, setup_common_options
)
from mysql.utilities.common.sql_transform import (is_quoted_with_backticks,
                                                  remove_backtick_quoting)
from mysql.utilities.common.tools import (check_connector_python,
                                          print_elapsed_time)

from mysql.utilities.exception import FormatError
from mysql.utilities.exception import UtilError

# Constants
NAME = "MySQL Utilities - mysqldbexport "
DESCRIPTION = "mysqldbexport - export metadata and data from databases"
USAGE = "%prog --server=user:pass@host:port:socket db1, db2, db3"

_PERMITTED_DISPLAY = ["names", "brief", "full"]
_PERMITTED_EXPORTS = ["data", "definitions", "both"]

# Check for connector/python
if not check_connector_python():
    sys.exit(1)

if __name__ == '__main__':
    # Needed for freeze support to avoid RuntimeError when running as a Windows
    # executable, otherwise ignored.
    multiprocessing.freeze_support()

    # Setup the command parser and setup server, help
    parser = setup_common_options(os.path.basename(sys.argv[0]),
                                  DESCRIPTION, USAGE)

    # Setup utility-specific options:

    # Add character set option
    add_character_set_option(parser)

    # Output format
    add_format_option(parser, "display the output in either sql (default), "
                      "grid, tab, csv, or vertical format", "sql", True)

    # Display format
    parser.add_option("-d", "--display", action="store", dest="display",
                      default="brief", help="control the number of columns "
                      "shown: 'brief' = minimal columns for object creation "
                      "(default), 'full' = all columns, 'names' = only object "
                      "names (not valid for --format=sql)", type="choice",
                      choices=_PERMITTED_DISPLAY)

    # Export mode
    parser.add_option("-e", "--export", action="store", dest="export",
                      default="definitions", help="control the export of "
                      "either 'data' = only the table data for the tables in "
                      "the database list, 'definitions' = export only the "
                      "definitions for the objects in the database list, or "
                      "'both' = export the metadata followed by the data "
                      "(default: export definitions)", type="choice",
                      choices=_PERMITTED_EXPORTS)

    # Single insert mode
    parser.add_option("-b", "--bulk-insert", action="store_true",
                      dest="bulk_import", default=False,
                      help="use bulk insert statements for data "
                           "(default:False)")

    # No header option
    add_no_headers_option(parser, restricted_formats=['tab', 'csv'])

    # Skip blobs for export
    parser.add_option("--skip-blobs", action="store_true", dest="skip_blobs",
                      default=False, help="do not export blob data.")

    # File-per-table mode
    parser.add_option("--file-per-table", action="store_true",
                      dest="file_per_tbl", default=False, help="write table "
                      "data to separate files. Valid only for --export=data "
                      "or --export=both.")

    # Add the exclude database option
    parser.add_option("-x", "--exclude", action="append", dest="exclude",
                      type="string", default=None, help="exclude one or more "
                      "objects from the operation using either a specific "
                      "name (e.g. db1.t1), a LIKE pattern (e.g. db1.t% or "
                      "db%.%) or a REGEXP search pattern. To use a REGEXP "
                      "search pattern for all exclusions, you must also "
                      "specify the --regexp option. Repeat the --exclude "
                      "option for multiple exclusions.")

    # Add the all database options
    add_all(parser, "databases")

    # Add the skip common options
    add_skip_options(parser)

    # Add verbosity and quiet (silent) mode
    add_verbosity(parser, True)

    # Add regexp
    add_regexp(parser)

    # Add locking
    add_locking(parser)

    # Replication user and password
    add_rpl_user(parser)

    # Add replication options
    add_rpl_mode(parser)

    parser.add_option("--skip-gtid", action="store_true", default=False,
                      dest="skip_gtid", help="skip creation of GTID_PURGED "
                      "statements.")

    # Add comment replication output
    parser.add_option("--comment-rpl", action="store_true", default=False,
                      dest="comment_rpl", help="place the replication "
                      "statements in comment statements. Valid only with "
                      "--rpl option.")

    parser.add_option("--skip-fkey-checks", action="store_true", default=False,
                      dest="skip_fkeys", help="skip creation of foreign key "
                      "disable/enable statements.")

    # Add multiprocessing option.
    parser.add_option("--multiprocess", action="store", dest="multiprocess",
                      type="int", default="1", help="use multiprocessing, "
                      "number of processes to use for concurrent execution. "
                      "Special values: 0 (number of processes equal to the "
                      "CPUs detected) and 1 (default - no concurrency).")

    # Add output file option.
    parser.add_option("--output-file", action="store", dest="output_file",
                      help="path and file name to store the generated output, "
                           "by default the standard output (no file).")

    # Now we process the rest of the arguments.
    opt, args = parser.parse_args()

    # Warn if quiet and verbosity are both specified
    check_verbosity(opt)

    try:
        skips = check_skip_options(opt.skip_objects)
    except UtilError:
        _, err, _ = sys.exc_info()
        print("ERROR: {0}".format(err.errmsg))
        sys.exit(1)

    # Fail if no db arguments or all
    if len(args) == 0 and not opt.all:
        parser.error("You must specify at least one database to export or "
                     "use the --all option to export all databases.")

    # Check replication options
    check_rpl_options(parser, opt)

    # Fail if we have arguments and all databases option listed.
    check_all(parser, opt, args, "databases")

    if opt.skip_blobs and not opt.export == "data":
        print("# WARNING: --skip-blobs option ignored for metadata export.")

    if opt.file_per_tbl and opt.export in ("definitions", "both"):
        print("# WARNING: --file-per-table option ignored for metadata "
              "export.")

    if "data" in skips and opt.export == "data":
        print("ERROR: You cannot use --export=data and --skip-data when "
              "exporting table data.")
        sys.exit(1)

    # Process --exclude values to remove unnecessary quotes (when used) in
    # order to avoid further matching issues.
    if opt.exclude:
        # Remove unnecessary outer quotes.
        exclude_list = [pattern.strip("'\"") for pattern in opt.exclude]
    else:
        exclude_list = opt.exclude

    # Check multiprocessing options.
    if opt.multiprocess < 0:
        parser.error("Number of processes '{0}' must be greater or equal than "
                     "zero.".format(opt.multiprocess))
    num_cpu = multiprocessing.cpu_count()
    if opt.multiprocess > num_cpu and not opt.quiet:
        print("# WARNING: Number of processes '{0}' is greater than the "
              "number of CPUs '{1}'.".format(opt.multiprocess, num_cpu))

    # Warning for non-posix (windows) systems if too many process are used.
    num_db = len(args)
    if (os.name != 'posix' and num_db and opt.multiprocess > num_db
            and not opt.quiet):
        print("# WARNING: Number of processes '{0}' is greater than the "
              "number of databases to export '{1}'.".format(opt.multiprocess,
                                                            num_db))

    # Check output_file option.
    if opt.output_file:
        # Check if file already exists.
        if os.path.exists(opt.output_file) and not opt.quiet:
            print("# WARNING: Specified output file already exists. The file "
                  "will be overwritten.")
        output_filename = opt.output_file
        try:
            output_file = open(output_filename, 'w')
        except IOError:
            parser.error("Unable to create file (check path and access "
                         "privileges): {0}".format(opt.output_file))
    else:
        # Always send output to a file for performance reasons (contents sent
        # at the end to the stdout).
        output_file = tempfile.NamedTemporaryFile(delete=False)
        output_filename = None

    # Set options for database operations.
    options = {
        "skip_tables": "tables" in skips,
        "skip_views": "views" in skips,
        "skip_triggers": "triggers" in skips,
        "skip_procs": "procedures" in skips,
        "skip_funcs": "functions" in skips,
        "skip_events": "events" in skips,
        "skip_grants": "grants" in skips,
        "skip_create": "create_db" in skips,
        "skip_data": "data" in skips,
        "skip_blobs": opt.skip_blobs,
        "skip_fkeys": opt.skip_fkeys,
        "format": opt.format,
        "no_headers": opt.no_headers,
        "display": opt.display,
        "single": not opt.bulk_import,
        "quiet": opt.quiet,
        "verbosity": opt.verbosity,
        "debug": opt.verbosity >= 3,
        "file_per_tbl": opt.file_per_tbl,
        "exclude_patterns": exclude_list,
        "all": opt.all,
        "use_regexp": opt.use_regexp,
        "locking": opt.locking,
        "rpl_user": opt.rpl_user,
        "rpl_mode": opt.rpl_mode,
        "rpl_file": opt.rpl_file,
        "comment_rpl": opt.comment_rpl,
        "export": opt.export,
        "skip_gtid": opt.skip_gtid,
        "charset": opt.charset,
        "multiprocess": num_cpu if opt.multiprocess == 0 else opt.multiprocess,
        "output_filename": output_filename,
    }

    # Parse server connection values
    try:
        server_values = parse_connection(opt.server, None, options)
    except FormatError:
        _, err, _ = sys.exc_info()
        parser.error("Server connection values invalid: {0}.".format(err))
    except UtilError:
        _, err, _ = sys.exc_info()
        parser.error("Server connection values invalid: "
                     "{0}.".format(err.errmsg))

    # Build list of databases to copy
    db_list = []
    for db in args:
        # Remove backtick quotes (handled later)
        db = remove_backtick_quoting(db) \
            if is_quoted_with_backticks(db) else db
        db_list.append(db)

    try:
        # record start time
        if opt.verbosity >= 3:
            start_export_time = time.time()

        # Export databases concurrently for non posix systems (windows).
        if options['multiprocess'] > 1 and os.name != 'posix':
            # Create export databases tasks.
            export_db_tasks = []
            for db in db_list:
                export_task = {
                    'srv_con': server_values,
                    'db_list': [db],
                    'options': options,
                }
                export_db_tasks.append(export_task)

            # Create process pool.
            workers_pool = multiprocessing.Pool(
                processes=options['multiprocess']
            )

            # Concurrently export databases.
            res = workers_pool.map_async(multiprocess_db_export_task,
                                         export_db_tasks)
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
        else:
            # Export all specified databases (no database level concurrency).
            # Note: on POSIX systems multiprocessing is applied at the table
            # level (not database).
            export_databases(server_values, db_list, output_file, options)

        if output_filename is None:
            # Dump the export output to the stdout.
            output_file.seek(0)
            shutil.copyfileobj(output_file, sys.stdout)
            output_file.close()
            os.remove(output_file.name)

        # record elapsed time
        if opt.verbosity >= 3:
            sys.stdout.flush()
            print_elapsed_time(start_export_time)

    except UtilError:
        _, err, _ = sys.exc_info()
        print("ERROR: {0}".format(err.errmsg))
        sys.exit(1)

    sys.exit()
