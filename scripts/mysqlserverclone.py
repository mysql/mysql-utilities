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

from mysql.utilities.common import setup_common_options
from mysql.utilities.common import exception
from mysql.utilities.command import serverclone

# Constants
NAME = "MySQL Utilities - mysqlserverclone "
VERSION = "1.0.0 alpha"
DESCRIPTION = "mysqlserverclone - start another instance of a running server"
USAGE = "%prog -u=root -p=passwd --new-data=<dir> --new-port=3307 --new-id=2"
                        
# Setup the command parser and setup user, password, host, socket, port
parser = setup_common_options(NAME+VERSION, DESCRIPTION, USAGE)

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

# Verbose mode
parser.add_option("--verbose", "-v", action="store_true", dest="verbose",
                  help="display additional information during operation")

# Now we process the rest of the arguments.
opt, args = parser.parse_args()

# Fail if no options listed.
if opt.login_user is None:
    parser.error("No login user specified. Use --help for available options.")
    
# Fail if no database path specified.
if opt.new_data is None:
    parser.error("No new database path. Use --help for available options.")

conn = {
    "user"   : opt.login_user,
    "passwd" : opt.login_pass,
    "host"   : opt.host,
    "port"   : opt.port,
    "unix_socket" : opt.socket
}

try:
    res = serverclone.clone_server(conn, opt.new_data, opt.new_port,
                                    opt.new_id, opt.rootpass, opt.mysqld,
                                    opt.verbose)
except exception.MySQLUtilError, e:
    print "ERROR:", e.errmsg
    exit(1)
    
