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
USAGE = "%prog --server=user:pass@host:port:socket --new-data=<dir> " \
        "--new-port=3307 --new-id=2"
                        
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
parser.add_option("--root-password", action="store", dest="rootpass",
                  type="string", help="password for the root user")

# Optional additional command-line options
parser.add_option("--mysqld", action="store", dest="mysqld",
                  type="string", help="Additional options for mysqld")

# Add verbosity mode
add_verbosity(parser, False)

# Now we process the rest of the arguments.
opt, args = parser.parse_args()

# Fail if no database path specified.
if opt.new_data is None:
    parser.error("No new database path. Use --help for available options.")

# Parse source connection values
try:
    conn = parse_connection(opt.server)
except:
    parser.error("Source connection values invalid or cannot be parsed.")

try:
    res = serverclone.clone_server(conn, opt.new_data, opt.new_port,
                                    opt.new_id, opt.rootpass, opt.mysqld,
                                    opt.verbosity >= 1)
except exception.MySQLUtilError, e:
    print "ERROR:", e.errmsg
    exit(1)
    
