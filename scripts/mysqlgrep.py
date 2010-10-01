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
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307 USA
#

import optparse
import re

from mysql.utilities.command import ObjectGrep, OBJECT_TYPES

parser = optparse.OptionParser(version="0.1",
                               usage="usage: %prog [options] pattern server ...")

parser.add_option("-b", "--body",
                  dest="check_body", action="store_true", default=False,
                  help="Search the body of routines, triggers, and events as well")

def quote(string):
    return "'" + string + "'"

# Add some more advanced parsing here to handle types better.
parser.add_option(
    '--type',
    dest="types", default=','.join(OBJECT_TYPES),
    help="Types to search: a comma-separated list of one or more of: "
         + ', '.join(map(quote, OBJECT_TYPES)))
parser.add_option(
    "-G", "--basic-regexp", "--regexp",
    dest="use_regexp", action="store_true", default=False,
    help="Use 'REGEXP' operator to match pattern. Default is to use 'LIKE'.")

parser.add_option(
    "-p", "--print-sql", "--sql",
    dest="print_sql", action="store_true", default=False,
    help="Print the statement instead of sending it to the server")
                  
options, args = parser.parse_args()

try:
    pattern = args.pop(0)
except IndexError:
    parser.error("No pattern supplied")

if len(args) == 0 and not options.print_sql:
    parser.error("You need at least one server if you're not using the --sql option")

types = re.split(r"\s*,\s*", options.types)
command = ObjectGrep(pattern, types, options.check_body, options.use_regexp)
if options.print_sql:
    print command.sql()
else:
    command.execute(args)
