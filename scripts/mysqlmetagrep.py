#!/usr/bin/python

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

import optparse
import os.path
import re
import sys

from mysql.utilities import VERSION_FRM
from mysql.utilities.command.grep import ObjectGrep, OBJECT_TYPES
from mysql.utilities.common.options import parse_connection
from mysql.utilities.common.options import setup_common_options
from mysql.utilities.common.options import check_format_option
from mysql.utilities.exception import UtilError

# Setup the command parser and setup server, help
parser = setup_common_options(os.path.basename(sys.argv[0]),
                              "mysqlmetagrep - search metadata",
                              "%prog --server=user:pass@host:port:socket "
                              "[options] pattern", True)

# Setup utility-specific options:
parser.add_option("-b", "--body",
                  dest="check_body", action="store_true", default=False,
                  help="Search the body of routines, triggers, and events as well")

def quote(string):
    return "'" + string + "'"

# Add some more advanced parsing here to handle types better.
parser.add_option(
    '--search-objects', '--object-types', 
    dest="object_types", default=','.join(OBJECT_TYPES),
    help="The object type to search in: a comma-separated list"
    " of one or more of: " + ', '.join(map(quote, OBJECT_TYPES)))
parser.add_option(
    "-G", "--basic-regexp", "--regexp",
    dest="use_regexp", action="store_true", default=False,
    help="Use 'REGEXP' operator to match pattern. Default is to use 'LIKE'.")
parser.add_option(
    "-p", "--print-sql", "--sql",
    dest="print_sql", action="store_true", default=False,
    help="Print the statement instead of sending it to the server")
parser.add_option(
    "-e", "--pattern",
    dest="pattern",
    help="Pattern to use when matching. Required if the pattern looks like a connection specification.")
parser.add_option(
    "--database",
    dest="database_pattern", default=None,
    help="Only look at objects in databases matching this pattern")

# Output format
parser.add_option(
    "-f", "--format", 
    action="store", dest="format", default="GRID",
    help="display the output in either GRID (default), "
    "TAB, CSV, or VERTICAL format")

options, args = parser.parse_args()

# Fail if format specified is invalid
try:
    options.format = check_format_option(options.format).upper()
except UtilError, e:
    parser.error(e.errmsg)

_LOOKS_LIKE_CONNECTION_MSG = """Pattern '{pattern}' looks like a
connection specification. Use --pattern if this is really what you
want"""

_AT_LEAST_ONE_SERVER_MSG = """You need at least one server if you're
not using the --sql option"""

_NO_SERVERS_ALLOWED_MSG = """You should not include servers in the
call if you are using the --sql option"""

# A --pattern is required.
if not options.pattern:
    parser.error("No pattern supplied.")

# Check that --sql option is not used with --server, and --server are
# supplied if --sql is not used.
if options.print_sql:
    if options.server is not None and len(options.server) > 0:
        parser.error(_NO_SERVERS_ALLOWED_MSG)
else:        
    if options.server is None or len(options.server) == 0:
        parser.error(_AT_LEAST_ONE_SERVER_MSG)

object_types = re.split(r"\s*,\s*", options.object_types)
command = ObjectGrep(options.pattern, options.database_pattern, object_types,
                     options.check_body, options.use_regexp)

try:
    if options.print_sql:
        print command.sql()
    else:
        command.execute(options.server, format=options.format)
except Exception as details:
    print >>sys.stderr, 'ERROR:', details
