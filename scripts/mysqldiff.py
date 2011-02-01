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
This file contains the object diff utility which allows users to compare the
definitions of two objects and return the difference (like diff).
"""

import optparse
import os
import sys
from mysql.utilities import VERSION_FRM
from mysql.utilities.command.diff import object_diff, database_diff
from mysql.utilities.common.options import parse_connection
from mysql.utilities.common.options import add_verbosity, check_verbosity
from mysql.utilities.exception import MySQLUtilError

# Constants
NAME = "MySQL Utilities - mysqldiff "
VERSION = "1.0.0 alpha"
DESCRIPTION = "mysqldiff - compare object definitions among objects" + \
              " where the difference is how db1.obj1 differs from db2.obj2"
USAGE = "%prog --server1=user:pass@host:port:socket " + \
        "--server2=user:pass@host:port:socket db1.object1:db2.object1 db3:db4"
PRINT_WIDTH = 75

# Setup the command parser
parser = optparse.OptionParser(
    version=VERSION_FRM.format(program=os.path.basename(sys.argv[0])),
    description=DESCRIPTION,
    usage=USAGE,
    add_help_option=False)
parser.add_option("--help", action="help")

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

# Add unified difference format
parser.add_option("-f", "--format", action="store", dest="difftype",
                  help="display differences using one of the following " + \
                       "formats: ('unified', 'context', 'differ') " + \
                       "default = unified", default='unified')
                        
# Add display width option
parser.add_option("--width", action="store", dest="width",
                  type = "int", help="display width",
                  default=PRINT_WIDTH)

# Force mode
parser.add_option("--force", action="store_true", dest="force",
                  help="do not abort when a diff test fails")

# Add verbosity and quiet (silent) mode
add_verbosity(parser, True)

# Now we process the rest of the arguments.
opt, args = parser.parse_args()

# Warn if quiet and verbosity are both specified
check_verbosity(opt)

# Check diff type
_DIFFTYPES = ['unified', 'context', 'differ']
if opt.difftype.lower() in _DIFFTYPES:
    difftype = opt.difftype.lower()
else:
    print "WARNING: you must specify a valid difference format. Using default."
    difftype = 'unified'

# Set options for database operations.
options = {
    "quiet"            : opt.quiet,
    "verbosity"        : opt.verbosity,
    "difftype"         : difftype,
    "force"            : opt.force,
    "width"            : opt.width
}

# Parse server connection values
try:
    server1_values = parse_connection(opt.server1)
except:
    parser.error("Server1 connection values invalid or cannot be parsed.")
if opt.server2 is not None:
    try:
        server2_values = parse_connection(opt.server2)
    except:
        parser.error("Server2 connection values invalid or cannot be parsed.")
else:
    server2_values = None

# run the diff
diff_failed = False
for argument in args:
    parts = argument.split(":")
    if len(parts) != 2 or len(parts[0].split('.')) != len(parts[1].split('.')):
        print "ERROR: invalid format for object compare argument. " + \
              "Format should be: db1.object:db2:object or db1:db2."
        exit(1)
    
    # We have db1.obj:db2.obj
    if len(parts[0].split('.')) > 1:
        try:
            diff = object_diff(server1_values, server2_values,
                               parts[0], parts[1], options)
        except MySQLUtilError, e:
            print "ERROR:", e.errmsg
            exit(1)
        if diff[1] is not None:
            diff_failed = True
            
    # We have db1:db2
    else:
        try:
            res = database_diff(server1_values, server2_values,
                                parts[0], parts[1], options)
        except MySQLUtilError, e:
            print "ERROR:", e.errmsg
            exit(1)
        if not res:
            diff_failed = True

if diff_failed:
    if not opt.quiet:
        print "Diff failed. One or more differences found."
    exit(1)            

if not opt.quiet:
    print "Success. All objects are the same."
    
exit()

