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
This file contains the import database utility which allows users to import
metadata for objects in a database and data for tables.
"""

import optparse
import os
import re
import sys
import time
from mysql.utilities import VERSION_FRM
from mysql.utilities.command import dbimport
from mysql.utilities.common.options import parse_connection, add_skip_options
from mysql.utilities.common.options import check_skip_options
from mysql.utilities.exception import MySQLUtilError

# Constants
NAME = "MySQL Utilities - mysqlimport "
VERSION = "1.0.0 alpha"
DESCRIPTION = "mysqlimport - import metadata and data from files"
USAGE = "%prog --server=user:pass@host:port:socket db1.csv db2.sql db3.grid"

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

# Input format
parser.add_option("-f", "--format", action="store", dest="format", default="SQL",
                  help="display the output in either SQL|S (default), "
                       "GRID|G, TAB|T, CSV|C, or VERTICAL|V format")

# Import mode
parser.add_option("-i", "--import", action="store", dest="import_type",
                  default="definitions", help="control the import of either "
                  "DATA|D = only the table data for the tables in the database "
                  "list, DEFINITIONS|F = import only the definitions for "
                  "the objects in the database list, or BOTH|B = import "
                  "the metadata followed by the data "
                  "(default: import definitions)")

# Drop mode
parser.add_option("-d", "--drop-first", action="store_true", default=False,
                  help="Drop database before importing.", dest="do_drop")

# Single insert mode
parser.add_option("-b", "--bulk-insert", action="store_true",
                  dest="bulk_insert", default=False, help="Use bulk insert "
                  "statements for data (default:False)")

# Header row
parser.add_option("-h", "--no-headers", action="store_true", dest="no_headers",
                  default=False, help="files do not contain column headers")

# Verbose mode
parser.add_option("--silent", action="store_true", dest="silent",
                  help="do not display feedback information during operation",
                  default=False)

# Debug mode
parser.add_option("--debug", action="store_true", dest="debug",
                  default=False, help="print debug information")

# Dryrun mode
parser.add_option("--dryrun", action="store_true", dest="dryrun",
                  default=False, help="import the files and generate the "
                  "statements but do not execute them - useful for testing "
                  "file validity")

# Add the skip common options
add_skip_options(parser)

# Skip blobs for import
parser.add_option("--skip-blobs", action="store_true", dest="skip_blobs",
                  default=False, help="Do not import blob data.")

# Now we process the rest of the arguments.
opt, args = parser.parse_args()

try:
    skips = check_skip_options(opt.skip_objects)
except MySQLUtilError, e:
    print "ERROR: %s" % e.errmsg
    exit(1)
    
# Fail if no arguments
if len(args) == 0:
    parser.error("You must specify at least one file to import.")
    
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

_PERMITTED_EXPORTS = ("DATA", "DEFINITIONS", "BOTH", "D", "F", "B")

if opt.import_type.upper() not in _PERMITTED_EXPORTS:
    print "# WARNING : '%s' is not a valid import mode. Using default." % \
          opt.import_type
    opt.import_type = "DEFINITIONS"
else:
    opt.import_type = opt.import_type.upper()
    
# Convert to full word for easier coding in command module
if opt.import_type == "D":
    opt.import_type = "DATA"
elif opt.import_type == "F":
    opt.import_type = "DEFINITIONS"
elif opt.import_type == "B":
    opt.import_type = "BOTH"
    
if opt.skip_blobs and not opt.import_type == "DATA":
    print "# WARNING: --skip-blobs option ignored for metadata import."
    
if "DATA" in skips and opt.import_type == "DATA":
    print "ERROR: You cannot use --import=data and --skip-data when " \
          "importing table data."
    exit(1)

if "CREATE_DB" in skips and opt.do_drop:
    print "ERROR: You cannot combine --drop-first and --skip=create_db."
    exit (1)

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
    "format"        : opt.format,
    "no_headers"    : opt.no_headers,
    "single"        : not opt.bulk_insert,
    "silent"        : opt.silent,
    "import_type"   : opt.import_type,
    "dryrun"        : opt.dryrun,
    "do_drop"       : opt.do_drop,
    "debug"         : opt.debug
}

# Parse server connection values
try:
    server_values = parse_connection(opt.server)
except:
    parser.error("Server connection values invalid or cannot be parsed.")

# Build list of files to import
file_list = []
for file_name in args:
    file_list.append(file_name)

try:
    # record start time
    if opt.debug:
        start_test = time.time()

    for file_name in file_list:
        dbimport.import_file(server_values, file_name, options)

    if opt.debug:
        print_elapsed_time(start_test)
        
except MySQLUtilError, e:
    print "ERROR:", e.errmsg
    exit(1)

exit()
