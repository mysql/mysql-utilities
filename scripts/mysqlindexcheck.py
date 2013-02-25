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
This file contains the check index utility. It is used to check for
duplicate or redundant indexes for a list of database (operates on
all tables in each database), a list of tables in the for db.table,
or all tables in all databases except internal databases.
"""

from mysql.utilities.common.tools import check_python_version

# Check Python version compatibility
check_python_version()

import os.path
import sys

from mysql.utilities.command import indexcheck
from mysql.utilities.common.options import parse_connection
from mysql.utilities.common.options import setup_common_options
from mysql.utilities.common.options import add_verbosity
from mysql.utilities.common.options import add_format_option
from mysql.utilities.exception import FormatError
from mysql.utilities.exception import UtilError

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

# Index list format
add_format_option(parser, "display the list of indexes per table in either "
                  "sql, grid (default), tab, csv, or vertical format", "grid",
                  True)     

# Show index statistics
parser.add_option("--stats", action="store_true",
                  dest="stats", default=False,
                  help="show index performance statistics")

# Set limit for best
parser.add_option("--best", action="store",
                  dest="best", default=None,
                  help="limit index statistics to the best N indexes")

# Set limit for worst
parser.add_option("--worst", action="store",
                  dest="worst", default=None,
                  help="limit index statistics to the worst N indexes")

# Add verbosity mode
add_verbosity(parser, False)

# Now we process the rest of the arguments.
opt, args = parser.parse_args()

# Check to make sure at least one table specified.
if len(args) == 0:
    parser.error("You must specify at least one table or database to check.")

# Parse source connection values
try:
    source_values = parse_connection(opt.server)
except FormatError:
    _, err, _ = sys.exc_info()
    parser.error("Server connection values invalid: %s." % err)
except UtilError:
    _, err, _ = sys.exc_info()
    parser.error("Server connection values invalid: %s." % err.errmsg)

# Check best, worst for validity
best = None
if opt.best is not None:
    try:
        best = int(opt.best)
    except:
        best = -1
if best is not None and best < 0:
    parser.error("The --best parameter must be an integer > 1")
    
worst = None
if opt.worst is not None:
    try:
        worst = int(opt.worst)
    except:
        worst = -1
if worst is not None and worst < 0:
    parser.error("The --worst parameter must be an integer > 1")
        
if opt.stats and worst is not None and best is not None:
    parser.error("You must specify either --best or --worst but not both.")
    
# default to worst performing queries
if opt.stats and worst is None and best is None:
    worst = 5
    
# no stats specified
if (worst is not None or best is not None) and not opt.stats:
    parser.error("You must specify --stats for --best or --worst to take " \
                 "effect.")

# Build dictionary of options
options = {
    "show-drops"    : opt.show_drops,
    "skip"          : opt.skip,
    "verbosity"     : opt.verbosity,
    "show-indexes"  : opt.show_indexes,
    "index-format"  : opt.format,
    "stats"         : opt.stats,
    "best"          : best,
    "worst"         : worst
}

try:
    res = indexcheck.check_index(source_values, args, options)
except UtilError:
    _, e, _ = sys.exc_info()
    print("ERROR: %s" % e.errmsg)
    sys.exit(1)

sys.exit()
