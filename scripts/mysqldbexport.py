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
This file contains the export database utility which allows users to export
metadata for objects in a database and data for tables.
"""

import optparse
import os
import re
import sys
import time
from mysql.utilities import VERSION_FRM
from mysql.utilities.command import dbexport
from mysql.utilities.common.options import parse_connection
from mysql.utilities.common.options import setup_common_options
from mysql.utilities.common.options import add_skip_options, check_skip_options
from mysql.utilities.common.options import add_verbosity, check_verbosity
from mysql.utilities.common.options import check_format_option
from mysql.utilities.exception import MySQLUtilError

# Constants
NAME = "MySQL Utilities - mysqldbexport "
DESCRIPTION = "mysqldbexport - export metadata and data from databases"
USAGE = "%prog --server=user:pass@host:port:socket db1, db2, db3"

def print_elapsed_time(start_test):
    """ Print the elapsed time to stdout (screen)

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
parser.add_option("-f", "--format", action="store", dest="format", default="SQL",
                  help="display the output in either SQL|S (default), "
                       "GRID|G, TAB|T, CSV|C, or VERTICAL|V format")

# Output format
parser.add_option("-d", "--display", action="store", dest="display",
                  default="BRIEF", help="control the number of columns shown: "
                  "BRIEF = minimal columns for object creation (default), "
                  "FULL = all columns, NAMES = only object names (not "
                  "valid for --format=SQL)")

# Export mode
parser.add_option("-e", "--export", action="store", dest="export",
                  default="definitions", help="control the export of either "
                  "DATA|D = only the table data for the tables in the database "
                  "list, DEFINITIONS|F = export only the definitions for "
                  "the objects in the database list, or BOTH|B = export "
                  "the metadata followed by the data "
                  "(default: export definitions)")

# Single insert mode
parser.add_option("-b", "--bulk-insert", action="store_true",
                  dest="bulk_import", default=False, help="Use bulk insert "
                  "statements for data (default:False)")

# Header row
parser.add_option("-h", "--no-headers", action="store_true", dest="no_headers",
                  default=False, help="do not display the column headers - "
                  "ignored for GRID format")

# Skip blobs for export
parser.add_option("--skip-blobs", action="store_true", dest="skip_blobs",
                  default=False, help="Do not export blob data.")

# File-per-table mode
parser.add_option("--file-per-table", action="store_true", dest="file_per_tbl",
                  default=False, help="Write table data to separate files. "
                  "Valid only for --export=data or --export=both.")

# Add the exclude database option
parser.add_option("-x", "--exclude", action="append", dest="exclude",
                  type="string", default=None, help="Exclude one or more "
                  "objects from the operation using either a specific name "
                  "(e.g. db1.t1) or a REGEXP search pattern. Repeat option "
                  "for multiple exclusions.")

# Add the skip common options
add_skip_options(parser)

# Add verbosity and quiet (silent) mode
add_verbosity(parser, True)

# Now we process the rest of the arguments.
opt, args = parser.parse_args()

# Warn if quiet and verbosity are both specified
check_verbosity(opt)

# Build exclusion lists
exclude_objects = []
exclude_object_names = []
if opt.exclude is not None:
    try:
        for item in opt.exclude:
            if item.find(".") > 0:
                db, name = item.split(".")
                exclude_object_names.append((db, name))
            else:
                exclude_objects.append(item)
    except:
        print "WARNING: Cannot parse exclude list. " + \
              "Proceeding without exclusions."

try:
    skips = check_skip_options(opt.skip_objects)
except MySQLUtilError, e:
    print "ERROR: %s" % e.errmsg
    exit(1)

# Fail if no arguments
if len(args) == 0:
    parser.error("You must specify at least one database to export.")

# Fail if format specified is invalid
try:
    opt.format = check_format_option(opt.format, True, True).upper()
except MySQLUtilError, e:
    parser.error(e.errmsg)

_PERMITTED_DISPLAY_TYPES = ("NAMES", "BRIEF", "FULL")

if opt.display.upper() not in _PERMITTED_DISPLAY_TYPES:
    print "# WARNING : '%s' is not a valid display mode. Using default." % \
          opt.display
    opt.display = "BRIEF"
else:
    opt.display = opt.display.upper()

_PERMITTED_EXPORTS = ("DATA", "DEFINITIONS", "BOTH", "D", "F", "B")

if opt.export.upper() not in _PERMITTED_EXPORTS:
    print "# WARNING : '%s' is not a valid export mode. Using default." % \
          opt.export
    opt.export = "DEFINITIONS"
else:
    opt.export = opt.export.upper()

# Convert to full word for easier coding in command module
if opt.export == "D":
    opt.export = "DATA"
elif opt.export == "F":
    opt.export = "DEFINITIONS"
elif opt.export == "B":
    opt.export = "BOTH"

if opt.skip_blobs and not opt.export == "DATA":
    print "# WARNING: --skip-blobs option ignored for metadata export."

if opt.file_per_tbl and (opt.export == "DEFINITIONS" or opt.export == "BOTH"):
    print "# WARNING: --file-per-table option ignored for metadata export."

if "DATA" in skips and opt.export == "DATA":
    print "ERROR: You cannot use --export=data and --skip-data when exporting " \
          "table data."
    exit(1)

# Set options for database operations.
options = {
    "skip_tables"      : "TABLES" in skips,
    "skip_views"       : "VIEWS" in skips,
    "skip_triggers"    : "TRIGGERS" in skips,
    "skip_procs"       : "PROCEDURES" in skips,
    "skip_funcs"       : "FUNCTIONS" in skips,
    "skip_events"      : "EVENTS" in skips,
    "skip_grants"      : "GRANTS" in skips,
    "skip_create"      : "CREATE_DB" in skips,
    "skip_data"        : "DATA" in skips,
    "skip_blobs"       : opt.skip_blobs,
    "format"           : opt.format,
    "no_headers"       : opt.no_headers,
    "display"          : opt.display,
    "single"           : not opt.bulk_import,
    "quiet"            : opt.quiet,
    "verbosity"        : opt.verbosity,
    "debug"            : opt.verbosity >= 3,
    "file_per_tbl"     : opt.file_per_tbl,
    "exclude_names"    : exclude_object_names,
    "exclude_patterns" : exclude_objects
}

# Parse server connection values
try:
    server_values = parse_connection(opt.server)
except:
    parser.error("Server connection values invalid or cannot be parsed.")

# Build list of databases to copy
db_list = []
for db in args:
    db_list.append(db)

try:
    # record start time
    if opt.verbosity >= 3:
        start_test = time.time()
    if opt.export == "DEFINITIONS" or opt.export == "BOTH":
        dbexport.export_metadata(server_values, db_list, options)
    if opt.export == "DATA" or opt.export == "BOTH":
        if opt.display != "BRIEF":
            print "# NOTE : --display is ignored for data export."
        dbexport.export_data(server_values, db_list, options)
    if opt.verbosity >= 3:
        print_elapsed_time(start_test)
except MySQLUtilError, e:
    print "ERROR:", e.errmsg
    exit(1)

exit()
