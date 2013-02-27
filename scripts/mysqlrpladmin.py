#!/usr/bin/env python
#
# Copyright (c) 2012, 2013, Oracle and/or its affiliates. All rights reserved.
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
This file contains the replication slave administration utility. It is used to
perform replication operations on one or more slaves.
"""

from mysql.utilities.common.tools import check_python_version

# Check Python version compatibility
check_python_version()

import logging
import optparse
import os.path
import sys

from mysql.utilities.exception import UtilError, UtilRplError
from mysql.utilities.common.options import parse_connection, add_verbosity
from mysql.utilities.common.options import add_format_option
from mysql.utilities.common.options import add_failover_options, add_rpl_user
from mysql.utilities.common.options import check_server_lists
from mysql.utilities.common.options import CaseInsensitiveChoicesOption
from mysql.utilities.common.server import check_hostname_alias
from mysql.utilities.common.topology import parse_failover_connections
from mysql.utilities.command.rpl_admin import RplCommands, purge_log
from mysql.utilities.command.rpl_admin import get_valid_rpl_commands
from mysql.utilities.command.rpl_admin import get_valid_rpl_command_text
from mysql.utilities.exception import FormatError
from mysql.utilities import VERSION_FRM


class MyParser(optparse.OptionParser):
    def format_epilog(self, formatter):
        return self.epilog

# Constants
NAME = "MySQL Utilities - mysqlrpladmin "
DESCRIPTION = "mysqlrpladmin - administration utility for MySQL replication"
USAGE = "%prog --slaves=root@localhost:3306 <command>"
_DATE_FORMAT = '%Y-%m-%d %H:%M:%S %p'

# Setup the command parser
parser = MyParser(
    version=VERSION_FRM.format(program=os.path.basename(sys.argv[0])),
    description=DESCRIPTION,
    usage=USAGE,
    add_help_option=False,
    option_class=CaseInsensitiveChoicesOption,
    epilog=get_valid_rpl_command_text())
parser.add_option("--help", action="help")

# Setup utility-specific options:
add_failover_options(parser)

# Connection information for the master
# Connect information for candidate server for switchover
parser.add_option("--new-master", action="store", dest="new_master", default=None,
                  type="string", help="connection information for the "
                  "slave to be used to replace the master for switchover, "
                  "in the form: <user>[:<password>]@<host>[:<port>][:<socket>]"
                  " or <login-path>[:<port>][:<socket>]. Valid only with "
                  "switchover command.")

# Force
parser.add_option("--force", action="store_true", dest="force",
                  help="ignore prerequsite check results and execute action")

# Output format
add_format_option(parser, "display the output in either grid (default), "
                  "tab, csv, or vertical format", None)     

# Add demote option
parser.add_option("--demote-master", action="store_true", dest="demote",
                  help="make master a slave after switchover.")

# Add no-health option
parser.add_option("--no-health", action="store_true", dest="no_health",
                  help="turn off health report after switchover or failover.")

# Add verbosity mode
add_verbosity(parser, True)

# Replication user and password
add_rpl_user(parser, None)

# Now we process the rest of the arguments.
opt, args = parser.parse_args()

# At least one of the options --discover-slaves-login or --slaves is required.
if not opt.discover and not opt.slaves:
    parser.error("One of these options is required to use the utility: "
                 "--discover-slaves-login or --slaves.")

# Check slaves list
check_server_lists(parser, opt.master, opt.slaves)

# Check for invalid command
if len(args) > 1:
    parser.error("You can only specify one command to execute at a time.")
elif len(args) == 0:
    parser.error("You must specify a command to execute.")

# The value for --timeout needs to be an integer > 0.
try:
    if int(opt.timeout) <= 0:
        parser.error("The --timeout option requires a value greater than 0.")
except ValueError:
    parser.error("The --timeout option requires an integer value.")

# Check errors and warnings of options and combinations.
    
command = args[0].lower()
if not command in get_valid_rpl_commands():
    parser.error("'%s' is not a valid command." % command)

if command == 'switchover' and (opt.new_master is None or opt.master is None):
    parser.error("The switchover command requires the --master and "
                 "--new-master options.")
    
if command in ['health', 'gtid'] and opt.discover is None and \
   (opt.slaves is None or opt.master is None):
    parser.error("The health and gtid commands requires the --master and "
                 "--slaves options.")

if command in ['start', 'stop', 'reset'] and \
   (not opt.slaves or not opt.master):
    parser.error("The start, stop and reset commands require the --master "
                 "and --slaves options.")

if command in ['elect', 'failover', 'start', 'stop', 'reset'] and \
    not opt.discover and not opt.slaves:
    parser.error("You must supply a list of slaves or the "
                 "--discover-slaves-login option.")
    
if command == 'failover' and opt.force:
    parser.error("You cannot use the --force option with failover.")

if opt.ping and not command == 'health':
    print("WARNING: The --ping option is used only with the health command.")
    
if command not in ['switchover', 'failover'] and \
   (opt.exec_after or opt.exec_before):
    print("WARNING: The --exec-* options are used only with the failover"
          " and switchover commands.")

if opt.new_master and command != 'switchover':
    print("WARNING: The --new-master option is used only with the "
          "switchover command.")

if opt.candidates and command not in ['elect', 'failover']:
    print("WARNING: The --candidates option is used only with the "
          "failover and elect commands.")
    opt.candidates = None

if (opt.candidates or opt.new_master) and command in ['stop', 'start', 'reset']:
    print("WARNING: The --new-master and --candidates options are not "
          "used with the stop, start, and reset commands.")
    opt.candidates = None
    
if opt.format and command not in ['health', 'gtid']:
    print("WARNING: The --format option is used only with the health "
          "and gtid commands.")
        
if opt.new_master:
    try:
        new_master_val = parse_connection(opt.new_master, None, opt)
    except FormatError:
        _, err, _ = sys.exc_info()
        parser.error("New master connection values invalid: %s." % err)
    except UtilError:
        _, err, _ = sys.exc_info()
        parser.error("New master connection values invalid: %s." % err.errmsg)
else:
    new_master_val = None

# Parse the master, slaves, and candidates connection parameters
try: 
    master_val, slaves_val, candidates_val = parse_failover_connections(opt)
except UtilRplError:
    _, e, _ = sys.exc_info()
    print("ERROR: %s" % e.errmsg)
    sys.exit(1)

# Check hostname alias
if master_val:
    for slave_val in slaves_val:
        if check_hostname_alias(master_val, slave_val):
            parser.error("The master and one of the slaves are the same host and port.")
    for cand_val in candidates_val:
        if check_hostname_alias(master_val, cand_val):
            parser.error("The master and one of the candidates are the same host and port.")

# Create dictionary of options
options = {
    'new_master'   : new_master_val,
    'candidates'   : candidates_val,
    'ping'         : 3 if opt.ping is None else opt.ping,
    'format'       : opt.format,
    'verbosity'    : 0 if opt.verbosity is None else opt.verbosity,
    'before'       : opt.exec_before,
    'after'        : opt.exec_after,
    'force'        : opt.force,
    'max_position' : opt.max_position,
    'max_delay'    : opt.max_delay,
    'discover'     : opt.discover,
    'timeout'      : int(opt.timeout),
    'demote'       : opt.demote,
    'quiet'        : opt.quiet,
    'logging'      : opt.log_file is not None,
    'log_file'     : opt.log_file,
    'no_health'    : opt.no_health,
    'rpl_user'     : opt.rpl_user,
}
 
# If command = HEALTH, turn on --force
if command == 'health' or command == 'gtid':
    options['force'] = True
 
# Purge log file of old data
if opt.log_file is not None and not purge_log(opt.log_file, opt.log_age):
    parser.error("Error purging log file.")

# Setup log file
try:
    logging.basicConfig(filename=opt.log_file, level=logging.INFO,
                        format='%(asctime)s %(levelname)s %(message)s',
                        datefmt=_DATE_FORMAT)
except IOError:
    _, e, _ = sys.exc_info()
    parser.error("Error opening log file: %s" % str(e.args[1]))

try:
    rpl_cmds = RplCommands(master_val, slaves_val, options)
    rpl_cmds.execute_command(command)
except UtilError:
    _, e, _ = sys.exc_info()
    print("ERROR: %s" % e.errmsg)
    sys.exit(1)
    
sys.exit(0)


