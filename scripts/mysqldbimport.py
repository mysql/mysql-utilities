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
This file contains the import database utility which allows users to import
metadata for objects in a database and data for tables.
"""

from mysql.utilities.common.tools import check_python_version

# Check Python version compatibility
check_python_version()

import os
import sys
import time

from mysql.utilities.command import dbimport
from mysql.utilities.common.options import parse_connection
from mysql.utilities.common.options import setup_common_options, add_engines
from mysql.utilities.common.options import add_skip_options, check_skip_options
from mysql.utilities.common.options import add_verbosity, check_verbosity
from mysql.utilities.common.options import add_format_option
from mysql.utilities.exception import FormatError
from mysql.utilities.exception import UtilError

# Constants
NAME = "MySQL Utilities - mysqldbimport "
DESCRIPTION = "mysqldbimport - import metadata and data from files"
USAGE = "%prog --server=user:pass@host:port:socket db1.csv db2.sql db3.grid"

_PERMITTED_IMPORTS = ["data", "definitions", "both"]

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

# Input format
add_format_option(parser, "the input file format in either sql (default), "
                  "grid, tab, csv, or vertical format", "sql", True)     

# Import mode
parser.add_option("-i", "--import", action="store", dest="import_type",
                  default="definitions", help="control the import of either "
                  "'data' = only the table data for the tables in the database "
                  "list, 'definitions' = import only the definitions for "
                  "the objects in the database list, or 'both' = import "
                  "the metadata followed by the data "
                  "(default: import definitions)", type="choice",
                  choices=_PERMITTED_IMPORTS)

# Drop mode
parser.add_option("-d", "--drop-first", action="store_true", default=False,
                  help="drop database before importing.", dest="do_drop")

# Single insert mode
parser.add_option("-b", "--bulk-insert", action="store_true",
                  dest="bulk_insert", default=False, help="use bulk insert "
                  "statements for data (default:False)")

# Header row
parser.add_option("-h", "--no-headers", action="store_true", dest="no_headers",
                  default=False, help="files do not contain column headers")

# Dryrun mode
parser.add_option("--dryrun", action="store_true", dest="dryrun",
                  default=False, help="import the files and generate the "
                  "statements but do not execute them - useful for testing "
                  "file validity")

# Skip blobs for import
parser.add_option("--skip-blobs", action="store_true", dest="skip_blobs",
                  default=False, help="do not import blob data.")

# Skip replication commands
parser.add_option("--skip-rpl", action="store_true", dest="skip_rpl",
                  default=False, help="do not execute replication commands.")

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

# Fail if no arguments
if len(args) == 0:
    parser.error("You must specify at least one file to import.")

if opt.skip_blobs and not opt.import_type == "data":
    print("# WARNING: --skip-blobs option ignored for metadata import.")

if "data" in skips and opt.import_type == "data":
    print("ERROR: You cannot use --import=data and --skip-data when "
          "importing table data.")
    sys.exit(1)

if "create_db" in skips and opt.do_drop:
    print("ERROR: You cannot combine --drop-first and --skip=create_db.")
    exit (1)

# Set options for database operations.
options = {
    "skip_tables"   : "tables" in skips,
    "skip_views"    : "views" in skips,
    "skip_triggers" : "triggers" in skips,
    "skip_procs"    : "procedures" in skips,
    "skip_funcs"    : "functions" in skips,
    "skip_events"   : "events" in skips,
    "skip_grants"   : "grants" in skips,
    "skip_create"   : "create_db" in skips,
    "skip_data"     : "data" in skips,
    "skip_blobs"    : opt.skip_blobs,
    "format"        : opt.format,
    "no_headers"    : opt.no_headers,
    "single"        : not opt.bulk_insert,
    "import_type"   : opt.import_type,
    "dryrun"        : opt.dryrun,
    "do_drop"       : opt.do_drop,
    "quiet"         : opt.quiet,
    "verbosity"     : opt.verbosity,
    "debug"         : opt.verbosity >= 3,
    "new_engine"    : opt.new_engine,
    "def_engine"    : opt.def_engine,
    "skip_rpl"      : opt.skip_rpl,
    "skip_gtid"     : opt.skip_gtid,
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

# Build list of files to import
file_list = []
for file_name in args:
    file_list.append(file_name)

try:
    # record start time
    if opt.verbosity >= 3:
        start_test = time.time()

    for file_name in file_list:
        dbimport.import_file(server_values, file_name, options)

    if opt.verbosity >= 3:
        print_elapsed_time(start_test)

except UtilError:
    _, e, _ = sys.exc_info()
    print("ERROR: %s" % e.errmsg)
    sys.exit(1)

sys.exit()
