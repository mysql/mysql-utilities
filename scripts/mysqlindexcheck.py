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
This file contains the check index utility. It is used to check for
duplicate or redundant indexes for a list of database (operates on
all tables in each database), a list of tables in the for db.table,
or all tables in all databases except internal databases.
"""

import optparse
import os.path
import sys

from mysql.utilities import VERSION_FRM
from mysql.utilities.command import indexcheck
from mysql.utilities.exception import MySQLUtilError
from mysql.utilities.common.options import parse_connection
from mysql.utilities.common.options import setup_common_options

# Constants
DESCRIPTION = "mysqlindexcheck - check for duplicate or redundant indexes"
USAGE = "%prog --server=user:pass@host:port:socket db1.table1 db2 db3.table2"

# Setup the command parser and setup server, help
parser = setup_common_options(os.path.basename(sys.argv[0]),
                              DESCRIPTION, USAGE)

# Display DROP statements
parser.add_option("--show-drops", "-d", action="store_true",
                  dest="show_drops", default=False,
                  help="display DROP statements for dropping indexes")

# Display all indexes per table
parser.add_option("--show-indexes", "-i", action="store_true",
                  dest="show_indexes", default=False,
                  help="display indexes for each table")

# Force mode
parser.add_option("-s", "--skip", action="store_true", dest="skip",
                  help="skip tables that do not exist",
                  default=False)

# Verbose mode
parser.add_option("--verbose", "-v", action="store_true",
                  dest="verbose", default=False,
                  help="display additional information during operation")

# Silent mode
parser.add_option("--silent", action="store_true",
                  dest="silent", default=False,
                  help="do not display informational messages")

# Index list mode
parser.add_option("--index-format", action="store",
                  dest="index_format", default="GRID",
                  help="display the list of indexes per table in either " \
                       "SQL, GRID (default), TAB, or CSV format")

# Show index statistics
parser.add_option("--stats", action="store_true",
                  dest="stats", default=False,
                  help="show index performance statistics")

# Set limit for best
parser.add_option("--first", action="store",
                  dest="first", default=None,
                  help="limit index statistics to the best N indexes")

# Set limit for worst
parser.add_option("--last", action="store",
                  dest="last", default=None,
                  help="limit index statistics to the worst N indexes")

# Now we process the rest of the arguments.
opt, args = parser.parse_args()

if opt.silent and opt.verbose:
    parser.error("You cannot use --silent and --verbose together.")

# Check to make sure at least one table specified.
if len(args) == 0:
    parser.error("You must specify at least one table or database to check.")
    
PERMITTED_FORMATS = ("SQL", "GRID", "TAB", "CSV")

if opt.index_format.upper() not in PERMITTED_FORMATS:
    print "WARNING : '%s' is not a valid index format. Using default." % \
          opt.index_format
    opt.index_format = "TABLE"
else:
    opt.index_format = opt.index_format.upper()

# Parse source connection values
try:
    source_values = parse_connection(opt.server)
except:
    parser.error("Source connection values invalid or cannot be parsed.")

# Check first, last for validity
first = None
if opt.first is not None:
    try:
        first = int(opt.first)
    except:
        first = -1
if first is not None and first < 0:
    parser.error("The --first parameter must be an integer > 1")
    
last = None
if opt.last is not None:
    try:
        last = int(opt.last)
    except:
        last = -1
if last is not None and last < 0:
    parser.error("The --last parameter must be an integer > 1")
        
if opt.stats and last is not None and first is not None:
    parser.error("You must specify either --first or --last but not both.")
    
# default to worst performing queries
if opt.stats and last is None and first is None:
    last = 5
    
# no stats specified
if (last is not None or first is not None) and not opt.stats:
    parser.error("You must specify --stats for --first or --last to take " \
                 "effect.")

# Parse source connection values
try:
    source_values = parse_connection(opt.server)
except:
    parser.error("Source connection values invalid or cannot be parsed.")
    
# Build dictionary of options
options = {
    "show-drops"    : opt.show_drops,
    "skip"          : opt.skip,
    "verbose"       : opt.verbose,
    "show-indexes"  : opt.show_indexes,
    "index-format"  : opt.index_format,
    "silent"        : opt.silent,
    "stats"         : opt.stats,
    "first"         : first,
    "last"          : last
}

try:
    res = indexcheck.check_index(source_values, args, options)
except MySQLUtilError, e:
    print "ERROR:", e.errmsg
    exit(1)
