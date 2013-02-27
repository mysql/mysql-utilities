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
import signal
import sys

from mysql.utilities.exception import UtilError, UtilRplError
from mysql.utilities.common.options import add_verbosity
from mysql.utilities.common.options import add_failover_options, add_rpl_user
from mysql.utilities.common.options import check_server_lists
from mysql.utilities.common.server import check_hostname_alias
from mysql.utilities.common.topology import parse_failover_connections
from mysql.utilities.command.rpl_admin import RplCommands, purge_log
from mysql.utilities import VERSION_FRM

# Constants
NAME = "MySQL Utilities - mysqlfailover "
DESCRIPTION = "mysqlfailover - automatic replication health monitoring and failover"
USAGE = "%prog --master=root@localhost --discover-slaves-login=root " + \
        "--candidates=root@host123:3306,root@host456:3306 " 
_DATE_FORMAT = '%Y-%m-%d %H:%M:%S %p'
_DATE_LEN = 22

# Setup a terminal signal handler for SIGNIT
# Must use SetConsoleCtrlHandler function on Windows!
# If posix, save old terminal settings so we can restore them on exit.
try:
    # Only valid for *nix systems.
    import tty, termios
    old_terminal_settings = termios.tcgetattr(sys.stdin)
except:
    # Ok to fail for Windows
    pass

def set_signal_handler(func):
    # If posix, restore old terminal settings.
    if os.name == "nt":
        from ctypes import windll
        windll.kernel32.SetConsoleCtrlHandler(func, True)
    # Install SIGTERM signal handler
    else:
        signal.signal(signal.SIGTERM, func)

# If ctypes present, we have Windows so define the exit with decorators
try:
    import ctypes
    @ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_uint)
    def on_exit(signal, func=None):
        logging.info("Failover console stopped with SIGTERM.")
        sys.exit(0)
except:
    def on_exit(signal, func=None):
        if os.name == "posix":
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN,
                              old_terminal_settings)
        logging.info("Failover console stopped with SIGTERM.")
        sys.exit(0)

set_signal_handler(on_exit)

# Setup the command parser
parser = optparse.OptionParser(
    version=VERSION_FRM.format(program=os.path.basename(sys.argv[0])),
    description=DESCRIPTION,
    usage=USAGE,
    add_help_option=False)
parser.add_option("--help", action="help")

# Setup utility-specific options:
add_failover_options(parser)

# Interval for continuous mode
parser.add_option("--interval", "-i", action="store", dest="interval",
                  type="int", default="15", help="interval in seconds for "
                  "polling the master for failure and reporting health. "
                  "Default = 15 seconds. Lowest value is 5 seconds.")

# Add failover modes
parser.add_option("--failover-mode", "-f", action="store", dest="failover_mode",
                  type="choice", default="auto", choices=["auto", "elect",
                  "fail"], help="action to take when the master "
                  "fails. 'auto' = automatically fail to best slave, "
                  "'elect' = fail to candidate list or if no candidate meets "
                  "criteria fail, 'fail' = take no action and stop when master "
                  "fails. Default = 'auto'.")

# Add failover detection extension point
parser.add_option("--exec-fail-check", action="store", dest="exec_fail",
                  type="string", default=None, help="name of script to "
                      "execute on each interval to invoke failover")

# Add force to override registry entry
parser.add_option("--force", action="store_true", dest="force",
                  help="override the registration check on master for "
                  "multiple instances of the console monitoring the same "
                  "master.")

# Add refresh script external point
parser.add_option("--exec-post-failover", action="store", dest="exec_post_fail",
                  type="string", default=None, help="name of script to "
                  "execute after failover is complete and the utility has "
                  "refreshed the health report.")


# Add rediscover on interval
parser.add_option("--rediscover", action="store_true", dest="rediscover",
                  help="Rediscover slaves on interval. Allows console to "
                  "detect when slaves have been removed or added.")

# Add verbosity mode
add_verbosity(parser, False)

# Replication user and password
add_rpl_user(parser, None)

# Now we process the rest of the arguments.
opt, args = parser.parse_args()

# Check slaves list
check_server_lists(parser, opt.master, opt.slaves)

# Check for errors
if int(opt.interval) < 5:
    parser.error("The --interval option requires a value greater than or "
                 "equal to 5.")

# The value for --timeout needs to be an integer > 0.
try:
    if int(opt.timeout) <= 0:
        parser.error("The --timeout option requires a value greater than 0.")
except ValueError:
    parser.error("The --timeout option requires an integer value.")

if opt.master is None:
    parser.error("You must specify a master to monitor.")
    
if opt.slaves is None and opt.discover is None:
    parser.error("You must supply a list of slaves or the "
                 "--discover-slaves-login option.")
    
if opt.failover_mode == 'elect' and opt.candidates is None:
    parser.error("Failover mode = 'elect' reqiures at least one candidate.")
    
# Parse the master, slaves, and candidates connection parameters
try: 
    master_val, slaves_val, candidates_val = parse_failover_connections(opt)
except UtilRplError:
    _, e, _ = sys.exc_info()
    print("ERROR: %s" % e.errmsg)
    sys.exit(1)

# Check hostname alias
for slave_val in slaves_val:
    if check_hostname_alias(master_val, slave_val):
        parser.error("The master and one of the slaves are the same host and port.")
for cand_val in candidates_val:
    if check_hostname_alias(master_val, cand_val):
        parser.error("The master and one of the candidates are the same host and port.")

# Create dictionary of options
options = {
    'candidates'    : candidates_val,
    'ping'          : 3 if opt.ping is None else opt.ping,
    'verbosity'     : 0 if opt.verbosity is None else opt.verbosity,
    'before'        : opt.exec_before,
    'after'         : opt.exec_after,
    'fail_check'    : opt.exec_fail,
    'max_position'  : opt.max_position,
    'max_delay'     : opt.max_delay,
    'discover'      : opt.discover,
    'timeout'       : int(opt.timeout),
    'interval'      : opt.interval,
    'failover_mode' : opt.failover_mode,
    'logging'       : opt.log_file is not None,
    'log_file'      : opt.log_file,
    'force'         : opt.force,
    'post_fail'     : opt.exec_post_fail,
    'rpl_user'      : opt.rpl_user,
    'rediscover'    : opt.rediscover,
}

# Purge log file of old data
if opt.log_file is not None and not purge_log(opt.log_file, opt.log_age):
    parser.error("Error purging log file.")

# Setup log file
logging.basicConfig(filename=opt.log_file, level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(message)s',
                    datefmt=_DATE_FORMAT)

try:
    rpl_cmds = RplCommands(master_val, slaves_val, options)
    rpl_cmds.auto_failover(opt.interval)
except UtilError:
    _, e, _ = sys.exc_info()
    # log the error in case it was an usual exception
    logging.log(logging.CRITICAL, e.errmsg.strip(' '))  
    print("ERROR: %s" % e.errmsg)
    sys.exit(1)
    
sys.exit(0)

