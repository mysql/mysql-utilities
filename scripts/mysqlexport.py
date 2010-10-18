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
This file contains the export database utility which allows users to export
metadata for objects in a database and data for tables.
"""

import optparse
import os
import re
import sys
import time
from mysql.utilities import VERSION_FRM
from mysql.utilities.command import export
from mysql.utilities.common.options import parse_connection, add_skip_options
from mysql.utilities.common.options import check_skip_options
from mysql.utilities.exception import MySQLUtilError

# Constants
NAME = "MySQL Utilities - mysqlexport "
VERSION = "1.0.0 alpha"
DESCRIPTION = "mysqlexport - export metadata and data from databases"
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

# Setup the command parser
parser = optparse.OptionParser(
    version=VERSION_FRM.format(program=os.path.basename(sys.argv[0])),
    description=DESCRIPTION,
    usage=USAGE,
    add_help_option=False)
parser.add_option("--help", action="help")

# Setup utility-specific options:

# Connection information for the server
parser.add_option("--server", action="store", dest="server",
                  type = "string", default="root@localhost:3306",
                  help="connection information for the server in " + \
                  "the form: <user>:<password>@<host>:<port>:<socket>")

# Output format
parser.add_option("-f", "--format", action="store", dest="format", default="SQL",
                  help="display the output in either SQL|S (default), "
                       "GRID|G, TAB|T, CSV|C, or VERTICAL|V format")

# Output format
parser.add_option("-d", "--display", action="store", dest="display",
                  default="BRIEF", help="control the number of columns shown: "
                  "BRIEF = minimal columns for object creation (default), "
                  "FULL = all columns, NAMES = only object names (not "
                  "valid for --format=SQL), VERTICAL - vertical display like "
                  "the mysql monitor \G output")

# Export mode
parser.add_option("-e", "--export", action="store", dest="export",
                  default="definitions", help="control the export of either "
                  "DATA|D = only the table data for the tables in the database "
                  "list, DEFINITIONS|F = export only the definitions for "
                  "the objects in the database list, or BOTH|B = export "
                  "the metadata followed by the data "
                  "(default: export metadata)")

# Single insert mode
parser.add_option("-b", "--bulk-insert", action="store_true",
                  dest="bulk_import", default=False, help="Use bulk insert "
                  "statements for data (default:False)")

# Header row
parser.add_option("-h", "--show-header", action="store_true", dest="header",
                  default=False, help="display the column headers")

# Verbose mode
parser.add_option("--verbose", "-v", action="store_true", dest="verbose",
                  help="display additional information during operation",
                  default=False)

# Verbose mode
parser.add_option("--silent", action="store_true", dest="silent",
                  help="do not display feedback information during operation",
                  default=False)

# Debug mode
parser.add_option("--debug", action="store_true", dest="debug",
                  default=False, help="print debug information")

# Add the skip common options
add_skip_options(parser)

# Skip blobs for export
parser.add_option("--skip-blobs", action="store_true", dest="skip_blobs",
                  default=False, help="Do not export blob data.")

# Now we process the rest of the arguments.
opt, args = parser.parse_args()

try:
    skips = check_skip_options(opt.skip_objects)
except MySQLUtilError, e:
    print "ERROR: %s" % e.errmsg
    exit(1)
    
# Fail if no arguments
if len(args) == 0:
    parser.error("You must specify at least one database to export.")
    
_PERMITTED_FORMATS = ("SQL", "GRID", "TAB", "CSV", "VERTICAL",
                      "S", "G", "T", "C", "V")

if opt.format.upper() not in _PERMITTED_FORMATS:
    print "# WARNING : '%s' is not a valid output format. Using default." % \
          opt.format
    opt.format = "SQL"
else:
    opt.format = opt.format.upper()

# Convert to full word for easier coding in command module
if opt.format == "S":
    opt.format = "SQL"
elif opt.format == "G":
    opt.format = "GRID"
elif opt.format == "T":
    opt.format = "TAB"
elif opt.format == "C":
    opt.format = "CSV"
elif opt.format == "V":
    opt.format = "VERTICAL"

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
    print "# WARNING : --skip-blobs option ignored for metadata export."
    
if "DATA" in skips and opt.export == "DATA":
    print "You cannot use --export=data and --skip-data when exporting " \
          "table data."
    exit(1)

# Set options for database operations.
options = {
    "skip_tables"   : "TABLES" in skips,
    "skip_views"    : "VIEWS" in skips,
    "skip_triggers" : "TRIGGERS" in skips,
    "skip_procs"    : "PROCEDURES" in skips,
    "skip_funcs"    : "FUNCTIONS" in skips,
    "skip_events"   : "EVENTS" in skips,
    "skip_grants"   : "GRANTS" in skips,
    "skip_create"   : "CREATE_DB" in skips,
    "skip_data"     : "DATA" in skips,
    "skip_blobs"    : opt.skip_blobs,
    "verbose"       : opt.verbose,
    "format"        : opt.format,
    "header"        : opt.header,
    "display"       : opt.display,
    "single"        : not opt.bulk_import,
    "debug"         : opt.debug
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
    if opt.debug:
        start_test = time.time()
    if opt.export == "DEFINITIONS" or opt.export == "BOTH":
        export.export_metadata(server_values, db_list, options)
    if opt.export == "DATA" or opt.export == "BOTH":
        if opt.display != "BRIEF":
            print "# NOTE : --display is ignored for data export."
        export.export_data(server_values, db_list, options)
    if opt.debug:
        print_elapsed_time(start_test)
except MySQLUtilError, e:
    print "ERROR:", e.errmsg
    exit(1)

exit()
