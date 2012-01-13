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
This file contains the clone user utility. It is used to clone an existing
MySQL user to one or more new user accounts copying all grant statements
to the new users.
"""

import optparse
import os.path
import sys

from mysql.utilities.common.options import setup_common_options
from mysql.utilities.common.options import parse_connection
from mysql.utilities.common.options import add_verbosity, check_verbosity
from mysql.utilities.common.options import add_format_option
from mysql.utilities.exception import UtilError
from mysql.utilities.command import userclone
from mysql.utilities import VERSION_FRM

# Constants
NAME = "MySQL Utilities - mysqluserclone "
DESCRIPTION = "mysqluserclone - clone a MySQL user account to" + \
              " one or more new users"
USAGE = "%prog --source=user:pass@host:port:socket " \
        "--destination=user:pass@host:port:socket " \
        "joe@localhost sam:secret1@localhost"

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

# Dump mode
parser.add_option("-d", "--dump", action="store_true",
                  dest="dump", help="dump GRANT statements for user - does "
                  "not require a destination")

# Overwrite mode
parser.add_option("--force", action="store_true", dest="overwrite",
                  help="drop the new user if it exists")

# Include globals mode
parser.add_option("--include-global-privileges", action="store_true",
                  dest="global_privs", help="include privileges that match "
                  "base_user@% as well as base_user@host", default=False)

# List mode
parser.add_option("--list", action="store_true", dest="list_users",
                  help="list all users on the source - does not require "
                  "a destination", default=False)

# format for list
add_format_option(parser, "display the list of users in either grid (default)"
                  ", tab, csv, or vertical format - valid only for --list "
                  "option", "grid")     

# Add verbosity and quiet (silent) mode
add_verbosity(parser, True)

# Now we process the rest of the arguments where the first is the
# base user and the next N are the new users.
opt, args = parser.parse_args()

# Fail if dump and quiet set
if opt.quiet and opt.dump:
    parser.error("You cannot use --quiet and --dump together.")

# Warn if quiet and verbosity are both specified
check_verbosity(opt)

# Fail if no arguments and no options.
if (len(args) == 0 or opt is None) and not opt.list_users:
    parser.error("No arguments found. Use --help for available options.")

# Parse source connection values
try:
    source_values = parse_connection(opt.source)
except:
    parser.error("Source connection values invalid or cannot be parsed.")

if opt.list_users:
    userclone.show_users(source_values, opt.verbosity, opt.format)
else:
    # Make sure we have the base user plus at least one new user
    if len(args) < 2 and not opt.dump:
        parser.error("Wrong parameter combination or no new users.")

    base_user = args[0]
    new_user_list = args[1:]

    # Parse destination connection values if not dumping
    if not opt.dump and opt.destination is not None:
        try:
            dest_values = parse_connection(opt.destination)
        except:
            parser.error("Destination connection values invalid or cannot "
                         "be parsed.")
    else:
        dest_values = None

    # Build dictionary of options
    options = {
        "dump"         : opt.dump,
        "overwrite"    : opt.overwrite,
        "quiet"        : opt.quiet,
        "verbosity"    : opt.verbosity,
        "global_privs" : opt.global_privs
    }

    try:
        res = userclone.clone_user(source_values, dest_values, base_user,
                                   new_user_list, options)
    except UtilError, e:
        print "ERROR:", e.errmsg
        exit(1)

exit()
