#!/usr/bin/env python
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
This file contains the import database utility which allows users to import
metadata for objects in a database and data for tables.
"""

import multiprocessing
import os
import sys
import time
import re

from mysql.utilities.common.tools import check_python_version
from mysql.utilities.command import dbimport
from mysql.utilities.common.ip_parser import parse_connection
from mysql.utilities.common.messages import (WARN_OPT_ONLY_USED_WITH,
                                             FILE_DOES_NOT_EXIST,
                                             INSUFFICIENT_FILE_PERMISSIONS)
from mysql.utilities.common.options import (add_character_set_option,
                                            add_engines, add_format_option,
                                            add_no_headers_option,
                                            add_skip_options, add_verbosity,
                                            check_skip_options,
                                            check_verbosity,
                                            setup_common_options,
                                            get_ssl_dict,
                                            check_password_security)
from mysql.utilities.common.pattern_matching import (
    REGEXP_QUALIFIED_OBJ_NAME,
    REGEXP_QUALIFIED_OBJ_NAME_AQ)
from mysql.utilities.common.server import connect_servers
from mysql.utilities.common.tools import (check_connector_python,
                                          print_elapsed_time)
from mysql.utilities.exception import FormatError, UtilError

# Check Python version compatibility
check_python_version()

# Constants
NAME = "MySQL Utilities - mysqldbimport "
DESCRIPTION = "mysqldbimport - import metadata and data from files"
USAGE = "%prog --server=user:pass@host:port:socket db1.csv db2.sql db3.grid"

_PERMITTED_IMPORTS = ["data", "definitions", "both"]

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

    # Input format
    add_format_option(parser, "the input file format in either sql (default), "
                      "grid, tab, csv, raw_csv or vertical format", "sql",
                      True, extra_formats=["raw_csv"])

    # Import mode
    parser.add_option("-i", "--import", action="store", dest="import_type",
                      default="definitions", help="control the import of "
                      "either 'data' = only the table data for the tables in "
                      "the database list, 'definitions' = import only the "
                      "definitions for the objects in the database list, or "
                      "'both' = import the metadata followed by the data "
                      "(default: import definitions)", type="choice",
                      choices=_PERMITTED_IMPORTS)

    # Drop mode
    parser.add_option("-d", "--drop-first", action="store_true", default=False,
                      help="drop database before importing.", dest="do_drop")

    # Single insert mode
    parser.add_option("-b", "--bulk-insert", action="store_true",
                      dest="bulk_insert", default=False, help="use bulk "
                      "insert statements for data (default:False)")

    # No header option
    add_no_headers_option(parser, restricted_formats=['tab', 'csv'],
                          help_msg="files do not contain column headers")

    # Dryrun mode
    parser.add_option("--dryrun", action="store_true", dest="dryrun",
                      default=False, help="import the files and generate the "
                      "statements but do not execute them - useful for "
                      "testing file validity")

    # Add table for import raw csv files
    parser.add_option("--table", action="store", dest="table", default=None,
                      help="destination table in the form: <db>.<table>.")

    # Skip blobs for import
    parser.add_option("--skip-blobs", action="store_true", dest="skip_blobs",
                      default=False, help="do not import blob data.")

    # Skip replication commands
    parser.add_option("--skip-rpl", action="store_true", dest="skip_rpl",
                      default=False, help="do not execute replication "
                                          "commands.")

    # Add skip generation of GTID statements
    parser.add_option("--skip-gtid", action="store_true", default=False,
                      dest="skip_gtid", help="do not execute the GTID_PURGED "
                      "statements.")

    # Add the skip common options
    add_skip_options(parser)

    # Add verbosity and quiet (silent) mode
    add_verbosity(parser, True)

    # Add engine options
    add_engines(parser)

    # Add multiprocessing option
    parser.add_option("--multiprocess", action="store", dest="multiprocess",
                      type="int", default="1", help="use multiprocessing, "
                      "number of processes to use for concurrent execution. "
                      "Special values: 0 (number of processes equal to the "
                      "CPUs detected) and 1 (default - no concurrency).")

    # Add autocommit option.
    parser.add_option("--autocommit", action="store_true", dest="autocommit",
                      default=False, help="use autocommit, by default "
                      "autocommit is off and transactions are only committed "
                      "once at the end of each imported file.")

    # Add max bulk insert option (to avoid broken pipe errors).
    parser.add_option("--max-bulk-insert", action="store", type="int",
                      dest="max_bulk_insert",
                      help="maximum bulk insert size, by default 30000.")

    # Now we process the rest of the arguments.
    opt, args = parser.parse_args()

    # Check security settings
    check_password_security(opt, args)

    # Warn if quiet and verbosity are both specified
    check_verbosity(opt)

    try:
        skips = check_skip_options(opt.skip_objects)
    except UtilError:
        _, err, _ = sys.exc_info()
        print("ERROR: {0}".format(err.errmsg))
        sys.exit(1)

    # Fail if no arguments
    if len(args) == 0:
        parser.error("You must specify at least one file to import.")

    if opt.skip_blobs and opt.import_type != "data" and not opt.quiet:
        print("# WARNING: --skip-blobs option ignored for metadata import.")

    if "data" in skips and opt.import_type == "data":
        print("ERROR: You cannot use --import=data and --skip-data when "
              "importing table data.")
        sys.exit(1)

    if "create_db" in skips and opt.do_drop:
        print("ERROR: You cannot combine --drop-first and --skip=create_db.")
        exit(1)

    # Check multiprocessing option.
    if opt.multiprocess < 0:
        parser.error("Number of processes '{0}' must be greater or equal than "
                     "zero.".format(opt.multiprocess))
    num_cpu = multiprocessing.cpu_count()
    if opt.multiprocess > num_cpu and not opt.quiet:
        print("# WARNING: Number of processes '{0}' is greater than the "
              "number of CPUs '{1}'.".format(opt.multiprocess, num_cpu))

    # Warning if too many process are used.
    num_files = len(args)
    if opt.multiprocess > num_files and not opt.quiet:
        print("# WARNING: Number of processes '{0}' is greater than the "
              "number of files to import '{1}'.".format(opt.multiprocess,
                                                        num_files))

    # Check max bulk insert option.
    if opt.max_bulk_insert and opt.max_bulk_insert <= 1:
        parser.error("Maximum bulk insert size '{0}' must be greater than "
                     "one.".format(opt.max_bulk_insert))
    if opt.max_bulk_insert and not opt.bulk_insert and not opt.quiet:
        print(WARN_OPT_ONLY_USED_WITH.format(opt="--max-bulk-insert",
                                             used_with="--bulk-insert"))
    # Set default value for max bulk insert.
    max_bulk_size = opt.max_bulk_insert if opt.max_bulk_insert else 30000

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
        "format": opt.format,
        "no_headers": opt.no_headers,
        "single": not opt.bulk_insert,
        "import_type": opt.import_type,
        "dryrun": opt.dryrun,
        "do_drop": opt.do_drop,
        "quiet": opt.quiet,
        "verbosity": opt.verbosity,
        "debug": opt.verbosity >= 3,
        "new_engine": opt.new_engine,
        "def_engine": opt.def_engine,
        "skip_rpl": opt.skip_rpl,
        "skip_gtid": opt.skip_gtid,
        "table": opt.table,
        "charset": opt.charset,
        "multiprocess": num_cpu if opt.multiprocess == 0 else opt.multiprocess,
        "autocommit": opt.autocommit,
        "max_bulk_insert": max_bulk_size,
    }

    # Parse server connection values
    try:
        options.update(get_ssl_dict(opt))
        server_values = parse_connection(opt.server, None, options)
    except FormatError:
        _, err, _ = sys.exc_info()
        parser.error("Server connection values invalid: {0}.".format(err))
    except UtilError:
        _, err, _ = sys.exc_info()
        parser.error("Server connection values invalid: "
                     "{0}.".format(err.errmsg))

    # Get the sql_mode set on source and destination server
    conn_opts = {
        'quiet': True,
        'version': "5.1.30",
    }
    try:
        servers = connect_servers(server_values, None, conn_opts)
        server_sql_mode = servers[0].select_variable("SQL_MODE")
    except UtilError:
        server_sql_mode = ''

    # Check values for --format=raw_csv
    if opt.format == "raw_csv":
        if not opt.table:
            print("ERROR: You must provide --table while using "
                  "--format=raw_csv.")
            sys.exit(1)
        # Validate table name using format <db>.<table>
        table_regex = REGEXP_QUALIFIED_OBJ_NAME
        if "ANSI_QUOTES" in server_sql_mode:
            table_regex = REGEXP_QUALIFIED_OBJ_NAME_AQ
        table_re = re.compile(
            r"{0}(?:\.){0}".format(table_regex)
        )
        if not table_re.match(opt.table):
            parser.error("Invalid table name: {0}.".format(opt.table))

    # Ignore --table for formats other than RAW_CSV.
    if opt.table and opt.format != "raw_csv" and not opt.quiet:
        print("WARNING: The --table option is only required for "
              "--format=raw_csv (option ignored).")

    # Build list of files to import
    file_list = []
    for file_name in args:
        # Test if is a file
        if not os.path.isfile(file_name):
            parser.error(FILE_DOES_NOT_EXIST.format(path=file_name))
        # Test if is readable
        try:
            with open(file_name, "r"):
                pass
        except IOError:
            parser.error(
                INSUFFICIENT_FILE_PERMISSIONS.format(permissions="read",
                                                     path=file_name))

        file_list.append(file_name)

    try:
        # record start time
        if opt.verbosity >= 3:
            start_test = time.time()

        # Import all specified files.
        import_file_tasks = []
        for file_name in file_list:
            # Check multiprocess file import.
            # Note: Multiprocessing is only applied at the file level,
            # independently from the system (posix or not).
            if options['multiprocess'] > 1:
                # Create import file task.
                import_task = {
                    'srv_con': server_values,
                    'file_name': file_name,
                    'options': options
                }
                import_file_tasks.append(import_task)
            else:
                # Import file (no concurrency at the file level).
                dbimport.import_file(server_values, file_name, options)

        # Import files concurrently.
        if import_file_tasks:
            # Create process pool.
            workers_pool = multiprocessing.Pool(
                processes=options['multiprocess']
            )

            # Concurrently import files.
            workers_pool.map_async(dbimport.multiprocess_file_import_task,
                                   import_file_tasks)
            workers_pool.close()
            workers_pool.join()

        if opt.verbosity >= 3:
            print_elapsed_time(start_test)

    except UtilError:
        _, err, _ = sys.exc_info()
        print("ERROR: {0}".format(err.errmsg))
        sys.exit(1)

    sys.exit()
