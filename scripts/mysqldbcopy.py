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
This file contains the copy database utility which ensures a database
is exactly the same among two servers.
"""

import optparse
import os
import re
import sys
import time

from mysql.utilities import VERSION_FRM
from mysql.utilities.command import dbcopy
from mysql.utilities.common.options import setup_common_options
from mysql.utilities.common.options import parse_connection, add_skip_options
from mysql.utilities.common.options import add_verbosity, check_verbosity
from mysql.utilities.common.options import check_skip_options, add_engines
from mysql.utilities.common.options import add_all, check_all, add_locking
from mysql.utilities.common.options import add_regexp, add_rpl_mode
from mysql.utilities.common.options import check_rpl_options, add_rpl_user
from mysql.utilities.exception import UtilError

# Constants
NAME = "MySQL Utilities - mysqldbcopy "
DESCRIPTION = "mysqldbcopy - copy databases from one server to another"
USAGE = "%prog --source=user:pass@host:port:socket " \
        "--destination=user:pass@host:port:socket orig_db:new_db"

def print_elapsed_time(start_test):
    """Print the elapsed time to stdout (screen)

    start_test[in]      The starting time of the test
    """
    stop_test = time.time()
    display_time = int((stop_test - start_test) * 100)
    if display_time == 0:
        display_time = 1
    print("Time: %6d\n" % display_time)

# Setup the command parser
parser = setup_common_options(os.path.basename(sys.argv[0]),
                              DESCRIPTION, USAGE, True, False)

# Setup utility-specific options:

# Connection information for the source server
parser.add_option("--source", action="store", dest="source",
                  type = "string", default="root@localhost:3306",
                  help="connection information for source server in " + \
                  "the form: <user>:<password>@<host>:<port>:<socket>")

# Connection information for the destination server
parser.add_option("--destination", action="store", dest="destination",
                  type = "string",
                  help="connection information for destination server in " + \
                  "the form: <user>:<password>@<host>:<port>:<socket>")

# Overwrite mode
parser.add_option("-f", "--force", action="store_true", dest="force",
                  help="drop the new database or object if it exists",
                  default=False)

# Threaded/connection mode
parser.add_option("--threads", action="store", dest="threads",
                  default=1, help="use multiple threads (connections) "
                  "for insert")

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

# Add engine options
add_engines(parser)

# Add locking options
add_locking(parser)

# Add regexp
add_regexp(parser)

# Replication user and password
add_rpl_user(parser, None)

# Add replication options but don't include 'both'
add_rpl_mode(parser, False, False)

# Now we process the rest of the arguments.
opt, args = parser.parse_args()

try:
    skips = check_skip_options(opt.skip_objects)
except UtilError, e:
    print "ERROR: %s" % e.errmsg
    exit(1)

# Fail if no options listed.
if opt.destination is None:
    parser.error("No destination server specified.")

# Fail if no db arguments or all
if len(args) == 0 and not opt.all:
    parser.error("You must specify at least one database to copy or "
                 "use the --all option to copy all databases.")
    
# Fail if we have arguments and all databases option listed.
check_all(parser, opt, args, "databases")

# Warn if quiet and verbosity are both specified
check_verbosity(opt)

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
    "force"            : opt.force,
    "verbose"          : opt.verbosity >= 1,
    "quiet"            : opt.quiet,
    "threads"          : opt.threads,
    "debug"            : opt.verbosity == 3,
    "exclude_patterns" : opt.exclude,
    "new_engine"       : opt.new_engine,
    "def_engine"       : opt.def_engine,
    "all"              : opt.all,
    "locking"          : opt.locking,
    "use_regexp"       : opt.use_regexp,
    "rpl_user"         : opt.rpl_user,
    "rpl_mode"         : opt.rpl_mode,
    "verbosity"        : opt.verbosity,
}

# Parse source connection values
try:
    source_values = parse_connection(opt.source)
except:
    parser.error("Source connection values invalid or cannot be parsed.")

# Parse destination connection values
try:
    dest_values = parse_connection(opt.destination)
except:
    parser.error("Destination connection values invalid or cannot be parsed.")

# Check to see if attempting to use --rpl on the same server
if (opt.rpl_mode or opt.rpl_user) and source_values == dest_values:
    parser.error("You cannot use the --rpl option for copying on the "
                 "same server.")

# Check replication options
check_rpl_options(parser, opt)
    
# Build list of databases to copy
db_list = []
for db in args:
    grp = re.match("(\w+)(?:\:(\w+))?", db)
    if not grp:
        parser.error("Cannot parse database list. Error on '%s'." % db)
    db_entry = grp.groups()
    db_list.append(db_entry)

try:
    # record start time
    if opt.verbosity >= 3:
        start_test = time.time()
    dbcopy.copy_db(source_values, dest_values, db_list, options)
    if opt.verbosity >= 3:
        print_elapsed_time(start_test)
except UtilError, e:
    print "ERROR:", e.errmsg
    exit(1)

exit()
