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
This file contains the replicate utility. It is used to establish a
master/slave replication topology among two servers.
"""

import optparse
from mysql.utilities.common import MySQLUtilError
from mysql.utilities.common import parse_connection
from mysql.utilities.command import rpl

# Constants
NAME = "MySQL Utilities - mysqlreplicate "
VERSION = "1.0.0 alpha"
DESCRIPTION = "mysqlreplicate - establish replication with a master"
USAGE = "%prog --master=root@localhost:3306 --slave=root@localhost:3310 " \
        "--server-id=3 --rpl_user=rpl:passwd "

# Setup the command parser
parser = optparse.OptionParser(version=NAME+VERSION,
                               description=DESCRIPTION,
                               usage=USAGE,
                               add_help_option=False)
parser.add_option("--help", action="help")

# Setup utility-specific options:

# Connection information for the source server
parser.add_option("--master", action="store", dest="master",
                  type = "string", default="root@localhost:3306",
                  help="connection information for master server in " + \
                  "the form: <user>:<password>@<host>:<port>:<socket>")

# Connection information for the destination server
parser.add_option("--slave", action="store", dest="slave",
                  type = "string", default=None,
                  help="connection information for slave server in " + \
                  "the form: <user>:<password>@<host>:<port>:<socket>")

# Server id
parser.add_option("--server-id", action="store", dest="server_id",
                  type = "string", default="",
                  help="the server_id for the slave")

# Replication user and password
parser.add_option("--rpl-user", action="store", dest="rpl_user",
                  type = "string", default="rpl:rpl",
                  help="the user and password for the replication " 
                       "user requirement - e.g. rpl:passwd " 
                       "- default = %default")

# Test replication option
parser.add_option("--test-db", action="store", dest="test_db",
                  type = "string", help="database name to use in testing "
                         " replication setup (optional)")

# Verbose mode
parser.add_option("--verbose", "-v", action="store_true", dest="verbose",
                  help="display additional information during operation")

# Now we process the rest of the arguments.
opt, args = parser.parse_args()

# Parse source connection values
try:
    m_values = parse_connection(opt.master)
except:
    parser.error("Master connection values invalid or cannot be parsed.")

# Parse source connection values
try:
    s_values = parse_connection(opt.slave)
except:
    parser.error("Slave connection values invalid or cannot be parsed.")
        
try:
    res = rpl.replicate(m_values, s_values, opt.server_id, opt.rpl_user,
                        opt.test_db, opt.verbose)
except MySQLUtilError, e:
    print "ERROR:", e.errmsg
    exit(1)

