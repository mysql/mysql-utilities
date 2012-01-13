#!/usr/bin/env python
#
# Copyright (c) 2011, Oracle and/or its affiliates. All rights reserved.
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
This file contains the operations to perform database consistency checking
on two databases.
"""

import optparse
import os
import sys
from mysql.utilities import VERSION_FRM
from mysql.utilities.command.dbcompare import database_compare
from mysql.utilities.common.options import parse_connection, add_difftype
from mysql.utilities.common.options import add_verbosity, check_verbosity
from mysql.utilities.common.options import add_changes_for, add_reverse
from mysql.utilities.common.options import add_format_option
from mysql.utilities.common.options import setup_common_options
from mysql.utilities.exception import UtilError, FormatError

# Constants
NAME = "MySQL Utilities - mysqldbcompare "
DESCRIPTION = "mysqldbcompare - compare databases for consistency"
USAGE = "%prog --server1=user:pass@host:port:socket " + \
        "--server2=user:pass@host:port:socket db1:db2"
PRINT_WIDTH = 75

# Setup the command parser
parser = setup_common_options(os.path.basename(sys.argv[0]),
                              DESCRIPTION, USAGE)

# Connection information for the source server
parser.add_option("--server1", action="store", dest="server1",
                  type="string", default="root@localhost:3306",
                  help="connection information for first server in " + \
                  "the form: <user>:<password>@<host>:<port>:<socket>")

# Connection information for the destination server
parser.add_option("--server2", action="store", dest="server2",
                  type="string", default=None,
                  help="connection information for second server in " + \
                  "the form: <user>:<password>@<host>:<port>:<socket>")

# Output format
add_format_option(parser, "display the output in either grid (default), "
                  "tab, csv, or vertical format", "grid")  

# Add skips
parser.add_option("--skip-object-compare", action="store_true",
                  dest="no_object_check",
                  help="skip object comparison step")

parser.add_option("--skip-row-count", action="store_true",
                  dest="no_row_count",
                  help="skip row count step")

parser.add_option("--skip-diff", action="store_true",
                  dest="no_diff",
                  help="skip the object diff step")

parser.add_option("--skip-data-check", action="store_true",
                  dest="no_data",
                  help="skip data consistency check")

# Add display width option
parser.add_option("--width", action="store", dest="width",
                  type = "int", help="display width",
                  default=PRINT_WIDTH)

# run-all-tests mode
parser.add_option("-a", "--run-all-tests", action="store_true",
                  dest="run_all_tests",
                  help="do not abort when a diff test fails")

# turn off binlog mode
parser.add_option("--disable-binary-logging", action="store_true",
                  default="False", dest="toggle_binlog",
                  help="turn binary logging off during operation if enabled "
                  "(SQL_LOG_BIN=1). Note: may require SUPER privilege. "
                  "Prevents compare operations from being written to the "
                  "binary log.")

# Add verbosity and quiet (silent) mode
add_verbosity(parser, True)

# Add difftype option
add_difftype(parser, True)

# Add the direction (changes-for)
add_changes_for(parser)

# Add show reverse option
add_reverse(parser)

# Now we process the rest of the arguments.
opt, args = parser.parse_args()

# Warn if quiet and verbosity are both specified
check_verbosity(opt)

# Set options for database operations.
options = {
    "quiet"            : opt.quiet,
    "verbosity"        : opt.verbosity,
    "difftype"         : opt.difftype,
    "run_all_tests"    : opt.run_all_tests,
    "width"            : opt.width,
    "no_object_check"  : opt.no_object_check,
    "no_diff"          : opt.no_diff,
    "no_row_count"     : opt.no_row_count,
    "no_data"          : opt.no_data,
    "format"           : opt.format,
    "toggle_binlog"    : opt.toggle_binlog,
    "changes-for"      : opt.changes_for,
    "reverse"          : opt.reverse,
}

# Parse server connection values
server2_values = None
try:
    server1_values = parse_connection(opt.server1)
    if opt.server2 is not None:
        server2_values = parse_connection(opt.server2)
except FormatError as details:
    parser.error(details)

# Operations to perform:
# 1) databases exist
# 2) check object counts
# 3) check object differences
# 4) check row counts among the tables
# 5) check table data consistency

res = True
check_failed = False
for db in args:
    parts = db.split(":")
    if len(parts) == 1:
        parts.append(parts[0])
    elif len(parts) != 2:
        parser.error("Invalid format for database compare argument. "
                     "Format should be: db1:db2 or db.")
    try:
        res = database_compare(server1_values, server2_values,
                             parts[0], parts[1], options)
        print
    except UtilError, e:
        print "ERROR:", e.errmsg
        check_failed = True
        if not opt.run_all_tests:
            break
    if not res:
        check_failed = True

    if check_failed and not opt.run_all_tests:
        break
    
if not opt.quiet:
    print
    if check_failed:
        print "# Database consistency check failed."
    else:
        sys.stdout.write("Databases are consistent")
        if opt.no_object_check or opt.no_diff or \
           opt.no_row_count or opt.no_data:
            sys.stdout.write(" given skip options specified")
        print "."
    print "#\n# ...done"

if check_failed:
    exit(1)
    
exit()

