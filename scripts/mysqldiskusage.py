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
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301 USA
#

"""
This file contains the disk usage utility for showing the estimated disk
storage of the databases and system files.
"""

import optparse
import os
import re
import sys
import time
from mysql.utilities import VERSION_FRM
from mysql.utilities.command import diskusage
from mysql.utilities.common.options import parse_connection
from mysql.utilities.common.options import setup_common_options
from mysql.utilities.common.options import add_verbosity
from mysql.utilities.common.options import add_format_option
from mysql.utilities.exception import UtilError

# Constants
NAME = "MySQL Utilities - mysqldiskusage "
DESCRIPTION = "mysqldiskusage - show disk usage for databases"
USAGE = "%prog --server=user:pass@host:port:socket db1 --all"

def print_elapsed_time(start_test):
    """Print the elapsed time to stdout (screen)

    start_test[in]      The starting time of the test
    """
    stop_test = time.time()
    display_time = int((stop_test - start_test) * 100)
    if display_time == 0:
        display_time = 1
    print("Time: %6d\n" % display_time)

# Setup the command parser and setup server, help
parser = setup_common_options(os.path.basename(sys.argv[0]),
                              DESCRIPTION, USAGE)

# Setup utility-specific options:

# Output format
add_format_option(parser, "display the output in either grid (default), "
                  "tab, csv, or vertical format", "grid")     

# Header row
parser.add_option("-h", "--no-headers", action="store_true", dest="no_headers",
                  default=False, help="do not show column headers")

# Binlogs option
parser.add_option("-b", "--binlog", action="store_true", dest="do_binlog",
                  default=False, help="include binary log usage")

# Relay logs option
parser.add_option("-r", "--relaylog", action="store_true", dest="do_relaylog",
                  default=False, help="include relay log usage")

# Logs option
parser.add_option("-l", "--logs", action="store_true", dest="do_logs",
                  default=False, help="include general and slow log usage")

# Innodb option
parser.add_option("-i", "--innodb", action="store_true", dest="do_innodb",
                  default=False, help="include InnoDB tablespace usage")

# Show empty databases option
parser.add_option("-m", "--empty", action="store_true", dest="do_empty",
                  default=False, help="include empty databases")

# all option
parser.add_option("-a", "--all", action="store_true", dest="do_all",
                  default=False, help="show all usage including empty "
                  "databases")


# Add verbosity mode
add_verbosity(parser, True)

# Now we process the rest of the arguments.
opt, args = parser.parse_args()

from mysql.utilities.common.server import connect_servers

# Parse source connection values
try:
    source_values = parse_connection(opt.server)
except:
    parser.error("Source connection values invalid or cannot be parsed.")

try:
    conn_options = {
        'version'   : "5.1.30",
    }
    servers = connect_servers(source_values, None, conn_options)
except UtilError, e:
    parser.error(e.errmsg)

try:
    res = servers[0].show_server_variable("datadir")
    datadir = res[0][1]
except UtilError, e:
    parser.error(e.errmsg)

if not os.access(datadir, os.R_OK):
    print "\nNOTICE: Your user account does not have read access to the " + \
          "datadir. Data sizes will be calculated and actual file sizes " + \
          "may be omitted. Some features may be unavailable.\n"

# Set options for database operations.
options = {
    "format"        : opt.format,
    "no_headers"    : opt.no_headers,
    "verbosity"     : opt.verbosity,
    "debug"         : opt.verbosity >= 3,
    "have_read"     : os.access(datadir, os.R_OK),
    "do_empty"      : opt.do_empty,
    "do_all"        : opt.do_all,
    "quiet"         : opt.quiet
}

# We do database disk usage by default.
try:
    diskusage.show_database_usage(servers[0], datadir, args, options)
except UtilError, e:
    print "ERROR:", e.errmsg
    exit(1)

# Look for the general and query logs and report
if opt.do_logs or opt.do_all:
    try:
        diskusage.show_logfile_usage(servers[0], options)
    except UtilError, e:
        print "ERROR:", e.errmsg
        exit(1)

# Look for the binary logs and report
if opt.do_binlog or opt.do_all:
    try:
        options["log_type"] = 'binary log'
        diskusage.show_log_usage(servers[0], datadir, options)
    except UtilError, e:
        print "ERROR:", e.errmsg
        exit(1)

# Look for the relay logs and report
if opt.do_relaylog or opt.do_all:
    try:
        options["log_type"] = 'relay log'
        diskusage.show_log_usage(servers[0], datadir, options)
    except UtilError, e:
        print "ERROR:", e.errmsg
        exit(1)

# Look at the inoodb tablespace information are report
if opt.do_innodb or opt.do_all:
    try:
        diskusage.show_innodb_usage(servers[0], datadir, options)
    except UtilError, e:
        print "ERROR:", e.errmsg
        exit(1)

if not opt.quiet:
    print "#...done."

exit()
