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
This file contains the clone user utility. It is used to clone an existing
MySQL user to one or more new user accounts copying all grant statements
to the new users.
"""

import optparse
from mysql.utilities.common import parse_connection
from mysql.utilities.common import MySQLUtilError
from mysql.utilities.command import userclone

# Constants
NAME = "MySQL Utilities - mysqluserclone "
VERSION = "1.0.0 alpha"
DESCRIPTION = "mysqluserclone - clone a MySQL user account to" + \
              " one or more new users"
USAGE = "%prog --source=user:pass@host:port:socket " \
        "--destination=user:pass@host:port:socket " \
        "joe@localhost sam@localhost:secret1"

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

# Connection information for the destination server
parser.add_option("--destination", action="store", dest="destination",
                  type = "string", 
                  help="connection information for destination server in " + \
                  "the form: <user>:<password>@<host>:<port>:<socket>")

# Copy directory
parser.add_option("--copy-dir", action="store", dest="copy_dir",
                  type = "string", default="", help="a path to use when "
                         "copying data (stores temporary files) - "
                         "default = current directory")

# Dump mode
parser.add_option("-d", "--dump", action="store_true",
                  dest="dump", help="dump GRANT statements for user")

# Overwrite mode
parser.add_option("-f", "--force", action="store_true", dest="overwrite",
                  help="drop the new user if it exists")

# Verbose mode
parser.add_option("--verbose", "-v", action="store_true", dest="verbose",
                  help="display additional information during operation")

# Silent mode
parser.add_option("--silent", action="store_true", dest="silent",
                  help="do not display feedback information during operation")

# Now we process the rest of the arguments where the first is the
# base user and the next N are the new users.
opt, args = parser.parse_args()

# Fail if dump and silent set
if opt.silent and opt.dump:
    print "ERROR: You cannot use --silent and --dump together."
    exit(1)

# Fail if no arguments and no options.
if len(args) == 0 or opt is None:
    print "ERROR: No arguments found. Use --help for available options."
    exit(1)

# Make sure we have the base user plus at least one new user
if len(args) < 2:
    print "ERROR: wrong parameter combination or no new users."
    exit(1)

base_user = args[0]
new_user_list = args[1:]

# Parse source connection values
source_values = parse_connection(opt.source)
if source_values is None:
    print "ERROR: Source connection values invalid or cannot be parsed."
    exit(1)

# Parse destination connection values
dest_values = parse_connection(opt.destination)
if dest_values is None:
    print "ERROR: Destination connection values invalid or cannot be parsed."
    exit(1)

try:
    res = userclone.clone_user(source_values, dest_values, base_user,
                               new_user_list, opt.dump, opt.copy_dir,
                               opt.overwrite, opt.verbose, opt.silent)
except MySQLUtilError, e:
    print "ERROR:", e.errmsg
    exit(1)
    
exit()
