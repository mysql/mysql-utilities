#!/usr/bin/env python
#
# Copyright (c) 2011, 2013, Oracle and/or its affiliates. All rights reserved.
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
This file contains the object diff utility which allows users to compare the
definitions of two objects and return the difference (like diff).
"""

from mysql.utilities.common.tools import check_python_version

# Check Python version compatibility
check_python_version()

import os
import re
import sys

from mysql.utilities.command.diff import object_diff, database_diff
from mysql.utilities.common.messages import PARSE_ERR_DB_OBJ_MISSING
from mysql.utilities.common.messages import PARSE_ERR_DB_OBJ_MISSING_MSG
from mysql.utilities.common.messages import PARSE_ERR_DB_OBJ_PAIR
from mysql.utilities.common.messages import PARSE_ERR_DB_OBJ_PAIR_EXT
from mysql.utilities.common.options import parse_connection, add_difftype
from mysql.utilities.common.options import add_verbosity, check_verbosity
from mysql.utilities.common.options import add_changes_for, add_reverse
from mysql.utilities.common.options import setup_common_options
from mysql.utilities.exception import FormatError
from mysql.utilities.exception import UtilError

# Constants
NAME = "MySQL Utilities - mysqldiff "
DESCRIPTION = "mysqldiff - compare object definitions among objects" + \
              " where the difference is how db1.obj1 differs from db2.obj2"
USAGE = "%prog --server1=user:pass@host:port:socket " + \
        "--server2=user:pass@host:port:socket db1.object1:db2.object1 db3:db4"
PRINT_WIDTH = 75

# Setup the command parser
parser = setup_common_options(os.path.basename(sys.argv[0]),
                              DESCRIPTION, USAGE, False, False)

# Connection information for the source server
parser.add_option("--server1", action="store", dest="server1",
                  type="string", default="root@localhost:3306",
                  help="connection information for first server in "
                  "the form: <user>[:<password>]@<host>[:<port>][:<socket>]"
                  " or <login-path>[:<port>][:<socket>].")

# Connection information for the destination server
parser.add_option("--server2", action="store", dest="server2",
                  type="string", default=None,
                  help="connection information for second server in "
                  "the form: <user>[:<password>]@<host>[:<port>][:<socket>]"
                  " or <login-path>[:<port>][:<socket>].")

# Add display width option
parser.add_option("--width", action="store", dest="width",
                  type = "int", help="display width",
                  default=PRINT_WIDTH)

# Force mode
parser.add_option("--force", action="store_true", dest="force",
                  help="do not abort when a diff test fails")

# Add verbosity and quiet (silent) mode
add_verbosity(parser, True)

# Add difftype option with SQL option
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
    "force"            : opt.force,
    "width"            : opt.width,
    "changes-for"      : opt.changes_for,
    "reverse"          : opt.reverse,
}

# Parse server connection values
try:
    server1_values = parse_connection(opt.server1, None, options)
except FormatError:
    _, err, _ = sys.exc_info()
    parser.error("Server1 connection values invalid: %s." % err)
except UtilError:
    _, err, _ = sys.exc_info()
    parser.error("Server1 connection values invalid: %s." % err.errmsg)
if opt.server2 is not None:
    try:
        server2_values = parse_connection(opt.server2, None, options)
    except FormatError:
        _, err, _ = sys.exc_info()
        parser.error("Server2 connection values invalid: %s." % err)
    except UtilError:
        _, err, _ = sys.exc_info()
        parser.error("Server2 connection values invalid: %s." % err.errmsg)
else:
    server2_values = None
    
# Check for arguments
if len(args) == 0:
    parser.error("No objects specified to compare.")

# run the diff
diff_failed = False
for argument in args:
    m_obj = re.match(r"(`(?:[^`]|``)+`|\w+)(?:(?:\.)(`(?:[^`]|``)+`|\w+))?"
                     "(?:\:)"
                     "(`(?:[^`]|``)+`|\w+)(?:(?:\.)(`(?:[^`]|``)+`|\w+))?",
                     argument)
    if not m_obj:
        parser.error(PARSE_ERR_DB_OBJ_PAIR.format(db_obj_pair=argument,
                                                  db1_label='db1',
                                                  obj1_label='object1',
                                                  db2_label='db2',
                                                  obj2_label='object2'))
    db1, obj1, db2, obj2 = m_obj.groups()

    # Verify if the size of the objects matched by the REGEX is equal to the
    # initial specified string. In general, this identifies the missing use
    # of backticks.
    matched_size = len(db1)
    if obj1:
        # add 1 for the separator '.'
        matched_size = matched_size + 1
        matched_size = matched_size + len(obj1)
    # add 1 for the separator ':'
    matched_size = matched_size + 1
    matched_size = matched_size + len(db2)
    if obj2:
        # add 1 for the separator '.'
        matched_size = matched_size + 1
        matched_size = matched_size + len(obj2)
    if matched_size != len(argument):
        parser.error(PARSE_ERR_DB_OBJ_PAIR_EXT.format(db_obj_pair=argument,
                                                      db1_label='db1',
                                                      obj1_label='object1',
                                                      db2_label='db2',
                                                      obj2_label='object2',
                                                      db1_value=db1,
                                                      obj1_value=obj1,
                                                      db2_value=db2,
                                                      obj2_value=obj2))

    if (obj1 and not obj2) or (not obj1 and obj2):
        if obj1:
            detail = PARSE_ERR_DB_OBJ_MISSING.format(db_no_obj_label='db2',
                                                     db_no_obj_value=db2,
                                                     only_obj_value=obj1,
                                                     db_obj_label='db1',
                                                     db_obj_value=db1)
        else:
            detail = PARSE_ERR_DB_OBJ_MISSING.format(db_no_obj_label='db1',
                                                     db_no_obj_value=db1,
                                                     only_obj_value=obj2,
                                                     db_obj_label='db2',
                                                     db_obj_value=db2)
        parser.error(PARSE_ERR_DB_OBJ_MISSING_MSG.format(detail=detail,
                                                         db1_label='db1',
                                                         obj1_label='object1',
                                                         db2_label='db2',
                                                         obj2_label='object2'))

    # We have db1.obj:db2.obj
    if obj1:
        try:
            diff = object_diff(server1_values, server2_values,
                               "%s.%s" % (db1, obj1),
                               "%s.%s" % (db2, obj2), options)
        except UtilError:
            _, e, _ = sys.exc_info()
            print("ERROR: %s" % e.errmsg)
            sys.exit(1)
        if diff is not None:
            diff_failed = True
            
    # We have db1:db2
    else:
        try:
            res = database_diff(server1_values, server2_values,
                                db1, db2, options)
        except UtilError:
            _, e, _ = sys.exc_info()
            print("ERROR: %s" % e.errmsg)
            sys.exit(1)
        if not res:
            diff_failed = True

if diff_failed:
    if not opt.quiet:
        print("Compare failed. One or more differences found.")
    sys.exit(1)            

if not opt.quiet:
    print("Success. All objects are the same.")
    
sys.exit()

