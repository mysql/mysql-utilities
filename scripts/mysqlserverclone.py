#!/usr/bin/env python
#
# Copyright (c) 2010, 2013, Oracle and/or its affiliates. All rights reserved.
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

from mysql.utilities.common.tools import check_python_version

# Check Python version compatibility
check_python_version()

import os.path
import sys

from mysql.utilities.common.options import add_basedir_option
from mysql.utilities.common.options import check_basedir_option
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
                              DESCRIPTION, USAGE, False, True, None)

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

# Add --basedir option
add_basedir_option(parser)

# Add --delete-data
parser.add_option("--delete-data", action="store_true", dest="delete",
                  help="delete the folder specified by --new-data if it "
                  "exists and is not empty.")

# Now we process the rest of the arguments.
opt, args = parser.parse_args()

# Check the basedir option for errors (e.g., invalid path)
check_basedir_option(parser, opt.basedir)

# Can only use --basedir and --datadir if --server is missing
if opt.basedir is not None and opt.server is not None:
    parser.error("Cannot use the --basedir and --server options together.")

# Fail if no database path specified.
if opt.new_data is None:
    parser.error("No new database path. Use --help for available options.")

# Warn if root-password is left off.
if opt.root_pass is None or opt.root_pass == '':
    print("# WARNING: Root password for new instance has not been set.")

# Fail if user does not have access to new data dir.
if os.path.exists(opt.new_data):
    if not os.access(opt.new_data, os.R_OK|os.W_OK):
        parser.error("You do not have enough privileges to access the folder "
                     "specified by --new-data.")
    
    # Fail if new data is not empty and delete not specified
    if os.listdir(opt.new_data) and not opt.delete:
        parser.error("Target data directory exists and is not empty. Use "
                     "--delete-data option to delete folder before cloning.")

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
    'basedir'        : opt.basedir,
    'delete'         : opt.delete,
}

# Expand user paths and resolve relative paths
if opt.new_data and opt.new_data[0] == '~':
    options['new_data'] = os.path.expanduser(opt.new_data)
if opt.basedir and opt.basedir[0] == '~':
    options['basedir'] = os.path.expanduser(opt.basedir)
if opt.new_data and opt.new_data[0] == '.':
    options['new_data'] = os.path.abspath(opt.new_data)
if opt.basedir and opt.basedir[0] == '.':
    options['basedir'] = os.path.abspath(opt.basedir)

# Parse source connection values if we have a running server
if opt.basedir is None:
    try:
        conn = parse_connection(opt.server)
    except exception.FormatError:
        _, err, _ = sys.exc_info()
        parser.error("Server connection values invalid: %s." % err)
    except exception.UtilError:
        _, err, _ = sys.exc_info()
        parser.error("Server connection values invalid: %s." % err.errmsg)
else:
    conn = None

try:
    res = serverclone.clone_server(conn, options)
except exception.UtilError:
    _, e, _ = sys.exc_info()
    print("ERROR: %s" % e.errmsg)
    sys.exit(1)
    
sys.exit()
