#!/usr/bin/env python
#
# Copyright (c) 2010, 2013, Oracle and/or its affiliates. All rights reserved.
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

import os
import sys
import time
from mysql.utilities.command.dbexport import export_databases
from mysql.utilities.common.options import parse_connection, add_regexp
from mysql.utilities.common.options import setup_common_options
from mysql.utilities.common.options import add_skip_options, check_skip_options
from mysql.utilities.common.options import add_verbosity, check_verbosity
from mysql.utilities.common.options import add_format_option, add_rpl_mode
from mysql.utilities.common.options import add_all, check_all, add_locking
from mysql.utilities.common.options import add_rpl_user, check_rpl_options

from mysql.utilities.common.sql_transform import remove_backtick_quoting
from mysql.utilities.common.sql_transform import is_quoted_with_backticks

from mysql.utilities.exception import FormatError
from mysql.utilities.exception import UtilError

# Constants
NAME = "MySQL Utilities - mysqldbexport "
DESCRIPTION = "mysqldbexport - export metadata and data from databases"
USAGE = "%prog --server=user:pass@host:port:socket db1, db2, db3"

_PERMITTED_DISPLAY = ["names", "brief", "full"]
_PERMITTED_EXPORTS = ["data", "definitions", "both"]

def print_elapsed_time(start_test):
    """Print the elapsed time to stdout (screen)

    start_test[in]      The starting time of the test
    """
    stop_test = time.time()
    display_time = int((stop_test - start_test) * 100)
    if display_time == 0:
        display_time = 1
    print("Time: %6d\n" % display_time)

# Setup the command parser and setup server, help
parser = setup_common_options(os.path.basename(sys.argv[0]),
                              DESCRIPTION, USAGE)

# Setup utility-specific options:

# Output format
add_format_option(parser, "display the output in either sql (default), "
                  "grid, tab, csv, or vertical format", "sql", True)     

# Display format
parser.add_option("-d", "--display", action="store", dest="display",
                  default="brief", help="control the number of columns shown: "
                  "'brief' = minimal columns for object creation (default), "
                  "'full' = all columns, 'names' = only object names (not "
                  "valid for --format=sql)", type="choice",
                  choices=_PERMITTED_DISPLAY)

# Export mode
parser.add_option("-e", "--export", action="store", dest="export",
                  default="definitions", help="control the export of either "
                  "'data' = only the table data for the tables in the database "
                  "list, 'definitions' = export only the definitions for "
                  "the objects in the database list, or 'both' = export "
                  "the metadata followed by the data "
                  "(default: export definitions)", type="choice",
                  choices=_PERMITTED_EXPORTS)

# Single insert mode
parser.add_option("-b", "--bulk-insert", action="store_true",
                  dest="bulk_import", default=False, help="use bulk insert "
                  "statements for data (default:False)")

# Header row
parser.add_option("-h", "--no-headers", action="store_true", dest="no_headers",
                  default=False, help="do not display the column headers - "
                  "ignored for grid format")

# Skip blobs for export
parser.add_option("--skip-blobs", action="store_true", dest="skip_blobs",
                  default=False, help="do not export blob data.")

# File-per-table mode
parser.add_option("--file-per-table", action="store_true", dest="file_per_tbl",
                  default=False, help="write table data to separate files. "
                  "Valid only for --export=data or --export=both.")

# Add the exclude database option
parser.add_option("-x", "--exclude", action="append", dest="exclude",
                  type="string", default=None, help="exclude one or more "
                  "objects from the operation using either a specific name "
                  "(e.g. db1.t1), a LIKE pattern (e.g. db1.t% or db%.%) or a "
                  "REGEXP search pattern. To use a REGEXP search pattern for "
                  "all exclusions, you must also specify the --regexp option. "
                  "Repeat the --exclude option for multiple exclusions.")

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
add_rpl_user(parser, None)

# Add replication options
add_rpl_mode(parser)

parser.add_option("--skip-gtid", action="store_true", default=False,
                  dest="skip_gtid", help="skip creation of GTID_PURGED "
                  "statements.")

# Add comment replication output
parser.add_option("--comment-rpl", action="store_true", default=False,
                  dest="comment_rpl", help="place the replication statements "
                  "in comment statements. Valid only with --rpl option.")

# Now we process the rest of the arguments.
opt, args = parser.parse_args()

# Warn if quiet and verbosity are both specified
check_verbosity(opt)

try:
    skips = check_skip_options(opt.skip_objects)
except UtilError:
    _, e, _ = sys.exc_info()
    print("ERROR: %s" % e.errmsg)
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
    print("# WARNING: --file-per-table option ignored for metadata export.")

if "data" in skips and opt.export == "data":
    print("ERROR: You cannot use --export=data and --skip-data when exporting "
          "table data.")
    sys.exit(1)

# Set options for database operations.
options = {
    "skip_tables"      : "tables" in skips,
    "skip_views"       : "views" in skips,
    "skip_triggers"    : "triggers" in skips,
    "skip_procs"       : "procedures" in skips,
    "skip_funcs"       : "functions" in skips,
    "skip_events"      : "events" in skips,
    "skip_grants"      : "grants" in skips,
    "skip_create"      : "create_db" in skips,
    "skip_data"        : "data" in skips,
    "skip_blobs"       : opt.skip_blobs,
    "format"           : opt.format,
    "no_headers"       : opt.no_headers,
    "display"          : opt.display,
    "single"           : not opt.bulk_import,
    "quiet"            : opt.quiet,
    "verbosity"        : opt.verbosity,
    "debug"            : opt.verbosity >= 3,
    "file_per_tbl"     : opt.file_per_tbl,
    "exclude_patterns" : opt.exclude,
    "all"              : opt.all,
    "use_regexp"       : opt.use_regexp,
    "locking"          : opt.locking,
    "rpl_user"         : opt.rpl_user,
    "rpl_mode"         : opt.rpl_mode,
    "rpl_file"         : opt.rpl_file,
    "comment_rpl"      : opt.comment_rpl,
    "export"           : opt.export,
    "skip_gtid"        : opt.skip_gtid,
}

# Parse server connection values
try:
    server_values = parse_connection(opt.server, None, options)
except FormatError:
    _, err, _ = sys.exc_info()
    parser.error("Server connection values invalid: %s." % err)
except UtilError:
    _, err, _ = sys.exc_info()
    parser.error("Server connection values invalid: %s." % err.errmsg)

# Build list of databases to copy
db_list = []
for db in args:
    # Remove backtick quotes (handled later)
    db = remove_backtick_quoting(db) if is_quoted_with_backticks(db) else db
    db_list.append(db)

try:
    # record start time
    if opt.verbosity >= 3:
        start_test = time.time()
        
    # Export all databases specified
    export_databases(server_values, db_list, options)
        
    # record elapsed time
    if opt.verbosity >= 3:
        print_elapsed_time(start_test)

except UtilError:
    _, e, _ = sys.exc_info()
    print("ERROR: %s" % e.errmsg)
    sys.exit(1)

sys.exit()
