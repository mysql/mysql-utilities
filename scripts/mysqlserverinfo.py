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
This file contains the server information utility.
"""
from mysql.utilities.common.tools import check_python_version

# Check Python version compatibility
check_python_version()

import os
import sys

from mysql.utilities.command.serverinfo import show_server_info
from mysql.utilities.common.options import add_basedir_option
from mysql.utilities.common.options import check_basedir_option
from mysql.utilities.common.options import setup_common_options
from mysql.utilities.common.options import add_format_option
from mysql.utilities.common.options import add_verbosity

from mysql.utilities.exception import UtilError

# Constants
NAME = "MySQL Utilities - mysqlserverinfo "
DESCRIPTION = "mysqlserverinfo - show server information"
USAGE = "%prog --server=user:pass@host:port:socket --format=grid"

# Setup the command parser and setup server, help
parser = setup_common_options(os.path.basename(sys.argv[0]),
                              DESCRIPTION, USAGE, True)

# Setup utility-specific options:

# Input format
add_format_option(parser, "display the output in either grid (default), "
                  "tab, csv, or vertical format", "grid")     

# Header row
parser.add_option("-h", "--no-headers", action="store_true", dest="no_headers",
                  default=False, help="do not show column headers")

# Show my.cnf values
parser.add_option("-d", "--show-defaults", action="store_true",
                  dest="show_defaults", default=False,
                  help="show defaults from the config file per server")

# Add --start option
parser.add_option("-s", "--start", action="store_true", dest="start",
                  help="start server in read only mode if offline")

# Add --basedir option
add_basedir_option(parser)

# Add --datadir option
parser.add_option("--datadir", action="store", dest="datadir", default=None,
                  type="string", help="the data directory for the server")

# Add --search-port
parser.add_option("--port-range", action="store", dest="ports",
                  default="3306:3333",
                  type="string", help="the port range to search for running"
                  " mysql servers on Windows systems")

# Add --show-servers option
parser.add_option("--show-servers", action="store_true", dest="show_servers",
                  help="show any known MySQL servers running on this host")

# Add verbosity mode
add_verbosity(parser, False)

# Now we process the rest of the arguments.
opt, args = parser.parse_args()

# Check the basedir option for errors (e.g., invalid path)
check_basedir_option(parser, opt.basedir)

# Check port range
if os.name == 'nt':
    parts = opt.ports.split(":")
    if len(parts) != 2:
        print("# WARNING : %s is not a valid port range. Using default." % 
              opt.ports)
        opt.ports = "3306:3333"

# Set options for database operations.
options = {
    "format"        : opt.format,
    "no_headers"    : opt.no_headers,
    "verbosity"     : opt.verbosity,
    "debug"         : opt.verbosity >= 3,
    "show_defaults" : opt.show_defaults,
    "start"         : opt.start,
    "basedir"       : opt.basedir,
    "datadir"       : opt.datadir,
    "ports"         : opt.ports,
    "show_servers"  : opt.show_servers
}

if opt.server is None:
    parser.error("You must specify at least one server.")

try:
    show_server_info(opt.server, options)
except UtilError:
    _, e, _ = sys.exc_info()
    print("ERROR: %s" % e.errmsg)
    sys.exit(1)
except Exception:
    _, e, _ = sys.exc_info()
    print("ERROR: %s" % e)
    sys.exit(1)

print("#...done.")

sys.exit()
