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
from mysql.utilities.common.options import parse_connection, add_skip_options
from mysql.utilities.common.options import check_skip_options
from mysql.utilities.exception import MySQLUtilError

# Constants
NAME = "MySQL Utilities - mysqldbcopy "
DESCRIPTION = "mysqldbcopy - copy databases from one server to another"
USAGE = "%prog --source=user:pass@host:port:socket " \
        "--destination=user:pass@host:port:socket orig_db:new_db"

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

# Copy directory
parser.add_option("--copy-dir", action="store", dest="copy_dir",
                  type = "string", default=None, help="a path to use when "
                         "copying data (stores temporary files) - "
                         "default = current directory")

# Overwrite mode
parser.add_option("-f", "--force", action="store_true", dest="force",
                  help="drop the new database or object if it exists",
                  default=False)

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

# Threaded/connection mode
parser.add_option("--connections", action="store", dest="connections",
                  default=1, help="use multiple connections for insert")

# Add the skip common options
add_skip_options(parser)

# Now we process the rest of the arguments.
opt, args = parser.parse_args()

try:
    skips = check_skip_options(opt.skip_objects)
except MySQLUtilError, e:
    print "ERROR: %s" % e.errmsg
    exit(1)

# Fail if no options listed.
if opt.destination is None:
    parser.error("No destination server specified.")

# Fail if no arguments
if len(args) == 0:
    parser.error("You must specify at least one database to copy.")
    
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
    "copy_dir"      : opt.copy_dir,
    "force"         : opt.force,
    "verbose"       : opt.verbose,
    "silent"        : opt.silent,
    "connections"   : opt.connections,
    "debug"         : opt.debug
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
    if opt.debug:
        start_test = time.time()
    dbcopy.copy_db(source_values, dest_values, db_list, options)
    if opt.debug:
        print_elapsed_time(start_test)
except MySQLUtilError, e:
    print "ERROR:", e.errmsg
    exit(1)

exit()
