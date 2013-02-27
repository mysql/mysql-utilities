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
This file contains the replicate utility. It is used to establish a
master/slave replication topology among two servers.
"""

from mysql.utilities.common.tools import check_python_version

# Check Python version compatibility
check_python_version()

import os.path
import sys

from mysql.utilities.exception import UtilError
from mysql.utilities.common.options import setup_common_options
from mysql.utilities.common.options import parse_connection
from mysql.utilities.common.options import add_verbosity
from mysql.utilities.common.server import check_hostname_alias
from mysql.utilities.command.check_rpl import check_replication
from mysql.utilities.exception import FormatError

# Constants
NAME = "MySQL Utilities - mysqlrplcheck "
DESCRIPTION = "mysqlrplcheck - check replication"
USAGE = "%prog --master=root@localhost:3306 --slave=root@localhost:3310 "

PRINT_WIDTH = 75

# Setup the command parser
parser = setup_common_options(os.path.basename(sys.argv[0]),
                              DESCRIPTION, USAGE, True, False)

# Setup utility-specific options:

# Connection information for the source server
parser.add_option("--master", action="store", dest="master",
                  type = "string", default="root@localhost:3306",
                  help="connection information for master server in " + \
                  "the form: <user>[:<password>]@<host>[:<port>][:<socket>]"
                  " or <login-path>[:<port>][:<socket>].")

# Connection information for the destination server
parser.add_option("--slave", action="store", dest="slave",
                  type = "string", default=None,
                  help="connection information for slave server in " + \
                  "the form: <user>[:<password>]@<host>[:<port>][:<socket>]"
                  " or <login-path>[:<port>][:<socket>]")

# Add --master-info-file
parser.add_option("--master-info-file", action="store", dest="master_info",
                  type="string", default="master.info",
                  help="the name of the master information file on the slave."
                       "default = 'master.info' read from the data directory."
                       " Note: this option requires that the utility run on "
                       "the slave with appropriate file read access to the "
                       "data directory.")

# Add --show-slave-status
parser.add_option("--show-slave-status", "-s", action="store_true",
                  dest="slave_status", default=False, help="show slave status")

# Add display width option
parser.add_option("--width", action="store", dest="width",
                  type = "int", help="display width",
                  default=PRINT_WIDTH)

# Add suppress to suppress warning messages
parser.add_option("--suppress", action="store_true", dest="suppress",
                  default=False, help="suppress warning messages")

# Add verbosity
add_verbosity(parser, True)

# Now we process the rest of the arguments.
opt, args = parser.parse_args()

# Parse source connection values
try:
    m_values = parse_connection(opt.master)
except FormatError:
    _, err, _ = sys.exc_info()
    parser.error("Master connection values invalid: %s." % err)
except UtilError:
    _, err, _ = sys.exc_info()
    parser.error("Master connection values invalid: %s." % err.errmsg)

# Parse source connection values
try:
    s_values = parse_connection(opt.slave)
except FormatError:
    _, err, _ = sys.exc_info()
    parser.error("Slave connection values invalid: %s." % err)
except UtilError:
    _, err, _ = sys.exc_info()
    parser.error("Slave connection values invalid: %s." % err.errmsg)

# Check hostname alias
if check_hostname_alias(m_values, s_values):
    parser.error("The master and slave are the same host and port.")
    
# Create dictionary of options
options = {
    'verbosity'    : opt.verbosity,
    'pedantic'     : False,
    'quiet'        : opt.quiet,
    'suppress'     : opt.suppress,
    'master_info'  : opt.master_info,
    'slave_status' : opt.slave_status,
    'width'        : opt.width
}
  
try:
    res = check_replication(m_values, s_values, options)
    if res:
        sys.exit(1)
except UtilError:
    _, e, _ = sys.exc_info()
    print("ERROR: %s" % e.errmsg)
    sys.exit(1)

sys.exit()
