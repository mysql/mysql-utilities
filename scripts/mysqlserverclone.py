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
This file contains the clone server utility which launches a new instance
of an existing server.
"""

import os.path
import sys

from mysql.utilities.common.options import parse_connection
from mysql.utilities.common.options import setup_common_options
from mysql.utilities.common.options import add_verbosity
from mysql.utilities import exception
from mysql.utilities.command import serverclone

# Constants
NAME = "MySQL Utilities - mysqlserverclone "
DESCRIPTION = "mysqlserverclone - start another instance of a running server"
USAGE = "%prog --server=user:pass@host:port:socket --new-data=/tmp/data2 " \
        "--new-port=3310 --new-id=12 --root-password=root"

# Setup the command parser and setup server, help
parser = setup_common_options(os.path.basename(sys.argv[0]),
                              DESCRIPTION, USAGE)

# Setup utility-specific options:

# Data directory for new instance
parser.add_option("--new-data", action="store", dest="new_data",
                  type = "string", help="the full path to the location "
                  "of the data directory for the new instance")

# Port for the new instance
parser.add_option("--new-port", action="store", dest="new_port",
                  type = "string", default="3307", help="the new port "
                         "for the new instance - default=%default")

# Server id for the new instance
parser.add_option("--new-id", action="store", dest="new_id",
                  type = "string", default="2", help="the server_id for "
                         "the new instance - default=%default")

# Root password for the new instance
parser.add_option("--root-password", action="store", dest="root_pass",
                  type="string", help="password for the root user")

# Optional additional command-line options
parser.add_option("--mysqld", action="store", dest="mysqld",
                  type="string", help="additional options for mysqld")

# Option to write command to file
parser.add_option("--write-command", "-w", action="store", dest='cmd_file',
                  default=None, type="string", help="path to file for writing"
                  " startup command. For example: start_server1.sh")

# Add verbosity and quiet mode
add_verbosity(parser, True)

# Now we process the rest of the arguments.
opt, args = parser.parse_args()

# Fail if no database path specified.
if opt.new_data is None:
    parser.error("No new database path. Use --help for available options.")

# Warn if root-password is left off.
if opt.root_pass is None or opt.root_pass == '':
    print "# WARNING: Root password for new instance has not been set."

# Build options
options = {
    'new_data'       : opt.new_data,
    'new_port'       : opt.new_port,
    'new_id'         : opt.new_id,
    'root_pass'      : opt.root_pass,
    'mysqld_options' : opt.mysqld,
    'verbosity'      : opt.verbosity,
    'quiet'          : opt.quiet,
    'cmd_file'       : opt.cmd_file,
}

# Parse source connection values
try:
    conn = parse_connection(opt.server)
except:
    parser.error("Source connection values invalid or cannot be parsed.")

try:
    res = serverclone.clone_server(conn, options)
except exception.UtilError, e:
    print "ERROR:", e.errmsg
    exit(1)
