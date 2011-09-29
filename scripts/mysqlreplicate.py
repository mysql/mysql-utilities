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
This file contains the replicate utility. It is used to establish a
master/slave replication topology among two servers.
"""

import optparse
import os.path
import sys

from mysql.utilities.exception import UtilError
from mysql.utilities.common.options import parse_connection
from mysql.utilities.common.options import add_verbosity, check_verbosity
from mysql.utilities.command import rpl
from mysql.utilities import VERSION_FRM

# Constants
NAME = "MySQL Utilities - mysqlreplicate "
DESCRIPTION = "mysqlreplicate - establish replication with a master"
USAGE = "%prog --master=root@localhost:3306 --slave=root@localhost:3310 " \
        "--server-id=3 --rpl_user=rpl:passwd "

# Setup the command parser
parser = optparse.OptionParser(
    version=VERSION_FRM.format(program=os.path.basename(sys.argv[0])),
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

# Replication user and password
parser.add_option("--rpl-user", action="store", dest="rpl_user",
                  type = "string", default="rpl:rpl",
                  help="the user and password for the replication " 
                       "user requirement - e.g. rpl:passwd " 
                       "- default = %default")

# Pedantic mode for failing if storage engines differ
parser.add_option("-p", "--pedantic", action="store_true", default=False,
                  dest="pedantic", help="Fail if storage engines differ "
                  "among master and slave.")

# Test replication option
parser.add_option("--test-db", action="store", dest="test_db",
                  type = "string", help="database name to use in testing "
                         " replication setup (optional)")

# Add master log file option
parser.add_option("--master-log-file", action="store", dest="master_log_file",
                  type="string", help="Use this master log file to initiate "
                  "the slave.", default=None)

# Add master log position option
parser.add_option("--master-log-pos", action="store", dest="master_log_pos",
                  type="int", help="Use this position in the master log file "
                  "to initiate the slave.", default=-1)

# Add start from beginning option
parser.add_option("-b", "--start-from-beginning", action="store_true",
                  default=False, dest="from_beginning",
                  help="Start replication from the first event recorded in "
                  "the binary logging of the master."
                  "Not valid with --master-log-file or --master-log-pos.")

# Add verbosity
add_verbosity(parser)

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
    
# Check required --master-log-file for --master-log-pos
if (opt.master_log_pos >= 0 and opt.master_log_file is None):
    parser.error("You must specify a master log file to use the master "
                 "log file position option.")
    
if ((opt.master_log_pos >= 0) or (opt.master_log_file is not None)) and \
   opt.from_beginning:
    parser.error("The --start-from-beginning option is not valid in "
                 "combination with --master-log-file or --master-log-pos.")
    
# Create dictionary of options
options = {
    'verbosity'       : opt.verbosity,
    'pedantic'        : opt.pedantic,
    'quiet'           : False,
    'master_log_file' : opt.master_log_file,
    'master_log_pos'  : opt.master_log_pos,
    'from_beginning'  : opt.from_beginning,
}

try:
    res = rpl.replicate(m_values, s_values, opt.rpl_user,
                        options, opt.test_db)
except UtilError, e:
    print "ERROR:", e.errmsg
    exit(1)

