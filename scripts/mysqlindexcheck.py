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
from mysql.utilities.common import parse_connection
from mysql.utilities.common import MySQLUtilError
from mysql.utilities.command import indexcheck

# Constants
NAME = "MySQL Utilities - mysqlindexcheck "
VERSION = "1.0.0 alpha"
DESCRIPTION = "mysqlindexcheck - check for duplicate or redundant indexes"
USAGE = "%prog --source=user:pass@host:port:socket db1.table1"

# Setup the command parser
parser = optparse.OptionParser(version=NAME+VERSION,
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

# Display DROP statements
parser.add_option("--show-drops", "-d", action="store_true",
                  dest="show_drops", default=False,
                  help="display DROP statements for dropping indexes")

# Force mode
parser.add_option("-s", "--skip", action="store_true", dest="skip",
                  help="skip tables that do not exist",
                  default=False)

# Verbose mode
parser.add_option("--verbose", "-v", action="store_true",
                  dest="verbose", default=False,
                  help="display additional information during operation")

# Now we process the rest of the arguments.
opt, args = parser.parse_args()

# Fail if no options listed.
if opt.source is None:
    print "ERROR: No source connection specified. Use --help for " \
          "available options."
    exit(1)

# Parse source connection values
source_values = parse_connection(opt.source)
if source_values is None:
    print "ERROR: Source connection values invalid or cannot be parsed."
    exit(1)
    
# Check to make sure at least one table specified.
if len(args) == 0:
    print "ERROR: You must specify at least one table or database to check."
    exit(1)

try:
    res = indexcheck.check_index(source_values, args, opt.show_drops,
                                 opt.skip, opt.verbose)
except MySQLUtilError, e:
    print "ERROR:", e.errmsg
    exit(1)
    