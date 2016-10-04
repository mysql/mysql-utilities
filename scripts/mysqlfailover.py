#!/usr/bin/env python
#
# Copyright (c) 2012, 2016, Oracle and/or its affiliates. All rights reserved.
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

import logging
import os
import signal
import sys

from mysql.utilities.common.tools import check_python_version
from mysql.utilities import VERSION_FRM, VERSION_STRING
from mysql.utilities.exception import UtilError, UtilRplError
from mysql.utilities.command.rpl_admin import RplCommands, purge_log
from mysql.utilities.common.messages import (SCRIPT_THRESHOLD_WARNING,
                                             MSG_UTILITIES_VERSION)
from mysql.utilities.common.server import check_hostname_alias
from mysql.utilities.common.tools import check_connector_python
from mysql.utilities.common.topology import parse_topology_connections
from mysql.utilities.common.options import (add_failover_options,
                                            add_verbosity, add_rpl_user,
                                            add_ssl_options,
                                            check_server_lists,
                                            license_callback,
                                            UtilitiesParser,
                                            check_password_security,
                                            check_script_option)

# Check Python version compatibility
check_python_version()

# Constants
NAME = "MySQL Utilities - mysqlfailover "
DESCRIPTION = ("mysqlfailover - automatic replication health monitoring and "
               "failover")
USAGE = "%prog --master=root@localhost --discover-slaves-login=root " + \
        "--candidates=root@host123:3306,root@host456:3306 "
_DATE_FORMAT = '%Y-%m-%d %H:%M:%S %p'
_DATE_LEN = 22

# Check for connector/python
if not check_connector_python():
    sys.exit(1)

if __name__ == '__main__':
    # Setup a terminal signal handler for SIGNIT
    # Must use SetConsoleCtrlHandler function on Windows!
    # If posix, save old terminal settings so we can restore them on exit.
    try:
        # Only valid for *nix systems.
        # pylint: disable=C0413,C0411
        import termios
        old_terminal_settings = termios.tcgetattr(sys.stdin)
    except:
        # Ok to fail for Windows
        pass

    def set_signal_handler(func):
        """Set the signal handler.
        """
        # If posix, restore old terminal settings.
        if os.name == "nt":
            from ctypes import windll
            windll.kernel32.SetConsoleCtrlHandler(func, True)
        # Install SIGTERM signal handler
        else:
            signal.signal(signal.SIGTERM, func)

    # If ctypes present, we have Windows so define the exit with decorators
    try:
        # pylint: disable=C0413,C0411
        import ctypes

        @ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_uint)
        def on_exit(signal, func=None):
            """Override the on_exit callback.
            """
            logging.info("Failover console stopped with SIGTERM.")
            sys.exit(0)
    except:
        def on_exit(signal, func=None):
            """Override the on_exit callback.
            """
            if os.name == "posix":
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN,
                                  old_terminal_settings)
            logging.info("Failover console stopped with SIGTERM.")
            sys.exit(0)

    set_signal_handler(on_exit)

    # Setup the command parser
    program = os.path.basename(sys.argv[0]).replace(".py", "")
    parser = UtilitiesParser(
        version=VERSION_FRM.format(program=program),
        description=DESCRIPTION,
        usage=USAGE,
        add_help_option=False,
        prog=program
    )

    # Default option to provide help information
    parser.add_option("--help", action="help",
                      help="display this help message and exit")

    # Add --License option
    parser.add_option("--license", action='callback',
                      callback=license_callback,
                      help="display program's license and exit")

    # Setup utility-specific options:
    add_failover_options(parser)

    # Interval for continuous mode
    parser.add_option("--interval", "-i", action="store", dest="interval",
                      type="int", default="15",
                      help="interval in seconds for polling the master for "
                           "failure and reporting health. Default = 15 "
                           "seconds. Lowest value is 5 seconds.")

    # Add failover modes
    parser.add_option("--failover-mode", "-f", action="store",
                      dest="failover_mode", type="choice", default="auto",
                      choices=["auto", "elect", "fail"],
                      help="action to take when the master fails. 'auto' = "
                           "automatically fail to best slave, 'elect' = fail "
                           "to candidate list or if no candidate meets "
                           "criteria fail, 'fail' = take no action and stop "
                           "when master fails. Default = 'auto'.")

    # Add failover detection extension point
    parser.add_option("--exec-fail-check", action="store", dest="exec_fail",
                      type="string", default=None,
                      help="name of script to execute on each interval "
                           "to invoke failover")

    # Add force to override registry entry
    parser.add_option("--force", action="store_true", dest="force",
                      default=False,
                      help="override the registration check on master for "
                           "multiple instances of the console monitoring the "
                           "same master.")

    # Add refresh script external point
    parser.add_option("--exec-post-failover", action="store",
                      dest="exec_post_fail", type="string", default=None,
                      help="name of script to execute after failover is "
                           "complete and the utility has refreshed the "
                           "health report.")

    # Pedantic mode for failing if some inconsistencies are found
    parser.add_option("-p", "--pedantic", action="store_true", default=False,
                      dest="pedantic",
                      help="fail if some inconsistencies are found (e.g. "
                           "errant transactions on slaves).")

    # Add no keyboard input
    parser.add_option("--no-keyboard", action="store_true", default=False,
                      dest="no_keyboard",
                      help="start with no keyboard input support.")

    # Add option to run as daemon
    parser.add_option("--daemon", action="store", dest="daemon", default=None,
                      help="run on daemon mode. It can be start, stop, "
                           "restart or nodetach.",
                      type="choice",
                      choices=("start", "stop", "restart", "nodetach"))

    # Add pidfile for the daemon option
    parser.add_option("--pidfile", action="store", dest="pidfile",
                      type="string", default=None,
                      help="pidfile for running mysqlfailover as a daemon.")

    # Add report values for daemon mode
    parser.add_option("--report-values", action="store", dest="report_values",
                      type="string", default="health",
                      help="report values used in mysqlfailover running as a "
                           "daemon. It can be health, gtid or uuid. Multiple "
                           "values can be used separated by commas. The "
                           "default is health.")

    # Add connection timeout for C/Py connections
    #
    # Note: we do not set a default here as we want C/Py to host the
    # default. Utilities need not control the default, rather, we only
    # want to provide an option for the user to set it should she have
    # need to tune for a particular failover scenario. See BUG#22932375
    # for more details.
    parser.add_option("--connection-timeout", action="store", type="int",
                      dest="conn_timeout", default=None, help="set the "
                      "connection timeout for TCP and Unix socket "
                      "connections for all master, slaves, and candidate "
                      "slaves specified. Default is 10 as provided in the "
                      "Connector/Python module.")

    # Add master failover delay check
    parser.add_option("--master-fail-retry", action="store", dest="fail_retry",
                      type="int", default=None, help="time in seconds to wait "
                      "to determine master is down. The failover check will "
                      "be run again when the retry delay expires. Can be used "
                      "to introduce a longer period between when master is "
                      "detected as unavailable to declaring it down. This "
                      "option is not used with --exec-fail-check. ")

    # Add verbosity mode
    add_verbosity(parser, False)

    # Replication user and password
    add_rpl_user(parser)

    # Add ssl options
    add_ssl_options(parser)

    # Now we process the rest of the arguments.
    opt, args = parser.parse_args()

    # Check security settings
    check_password_security(opt, args)

    # Check slaves list
    if opt.daemon != "stop":
        check_server_lists(parser, opt.master, opt.slaves)

    # Check for errors
    if int(opt.interval) < 5:
        parser.error("The --interval option requires a value greater than or "
                     "equal to 5.")

    # The value for --timeout needs to be an integer > 0.
    try:
        if int(opt.timeout) <= 0:
            parser.error("The --timeout option requires a value greater "
                         "than 0.")
    except ValueError:
        parser.error("The --timeout option requires an integer value.")

    # if opt.master is None and opt.daemon and opt.daemon != "stop":
    if opt.master is None and opt.daemon != "stop":
        parser.error("You must specify a master to monitor.")

    if opt.slaves is None and opt.discover is None and opt.daemon != "stop":
        parser.error("You must supply a list of slaves or the "
                     "--discover-slaves-login option.")

    if opt.failover_mode == 'elect' and opt.candidates is None:
        parser.error("Failover mode = 'elect' requires at least one "
                     "candidate.")

    if opt.fail_retry and opt.exec_fail:
        parser.error("The --master-fail-retry option cannot be used "
                     "with --exec-fail-check.")

    if opt.fail_retry and opt.fail_retry < 1:
        parser.error("The --master-fail-retry option must be a positive "
                     "integer > 0.")

    # Parse the master, slaves, and candidates connection parameters
    try:
        master_val, slaves_val, candidates_val = parse_topology_connections(
            opt)
    except UtilRplError:
        _, e, _ = sys.exc_info()
        print("ERROR: {0}".format(e.errmsg))
        sys.exit(1)

    # Check hostname alias
    for slave_val in slaves_val:
        if check_hostname_alias(master_val, slave_val):
            parser.error("The master and one of the slaves are the same "
                         "host and port.")
    for cand_val in candidates_val:
        if check_hostname_alias(master_val, cand_val):
            parser.error("The master and one of the candidates are the same "
                         "host and port.")

    # Create dictionary of options
    options = {
        'candidates': candidates_val,
        'ping': 3 if opt.ping is None else opt.ping,
        'verbosity': 0 if opt.verbosity is None else opt.verbosity,
        'before': opt.exec_before,
        'after': opt.exec_after,
        'exec_fail': opt.exec_fail,
        'max_position': opt.max_position,
        'max_delay': opt.max_delay,
        'discover': opt.discover,
        'timeout': int(opt.timeout),
        'interval': opt.interval,
        'failover_mode': opt.failover_mode,
        'logging': opt.log_file is not None,
        'log_file': opt.log_file,
        'force': opt.force,
        'post_fail': opt.exec_post_fail,
        'rpl_user': opt.rpl_user,
        'pedantic': opt.pedantic,
        'no_keyboard': opt.no_keyboard,
        'daemon': opt.daemon,
        'pidfile': opt.pidfile,
        'report_values': opt.report_values,
        'script_threshold': opt.script_threshold,
        'fail_retry': opt.fail_retry,
    }

    # Purge log file of old data
    if opt.log_file is not None and not purge_log(opt.log_file, opt.log_age):
        parser.error("Error purging log file.")

    # Setup log file
    logging.basicConfig(filename=opt.log_file, level=logging.INFO,
                        format='%(asctime)s %(levelname)s %(message)s',
                        datefmt=_DATE_FORMAT)

    # Warn user about script threshold checking.
    if opt.script_threshold:
        print(SCRIPT_THRESHOLD_WARNING)

    # Check if script files exist and are executable and warn users if they
    # are not.
    script_opts = ['after', 'before', 'exec_fail', 'post_fail']
    for key in script_opts:
        parameter_val = options[key]
        check_script_option(parser, parameter_val)

    # Check if the values specified for the --report-values option are valid.
    for report in opt.report_values.split(','):
        if report.lower() not in ("health", "gtid", "uuid"):
            parser.error("The value for the option --report-values is not "
                         "valid: '{0}', the values allowed are 'health', "
                         "'gitd' or 'uuid'".format(opt.report_values))

    # Check the daemon options
    if opt.daemon:
        # Check if a POSIX system
        if os.name != "posix":
            parser.error("Running mysqlfailover with --daemon is only "
                         "available for POSIX systems.")

        # Check the presence of --log
        if opt.daemon != "stop" and not opt.log_file:
            parser.error("The option --log is required when using --daemon.")

        # Test pidfile
        if opt.daemon != "nodetach":
            pidfile = opt.pidfile or "./failover_daemon.pid"
            pidfile = os.path.realpath(os.path.normpath(pidfile))
            if opt.daemon == "start":
                # Test if pidfile exists
                if os.path.exists(pidfile):
                    parser.error("pidfile {0} already exists. The daemon is "
                                 "already running?".format(pidfile))
                # Test if pidfile is writable
                try:
                    with open(pidfile, "w") as f:
                        f.write("{0}\n".format(0))
                    # Delete temporary pidfile
                    os.remove(pidfile)
                except IOError as err:
                    parser.error("Unable to write pidfile: {0}"
                                 "".format(err.strerror))
            else:
                # opt.daemon == stop/restart, test if pidfile is readable
                pid = None
                try:
                    if not os.path.exists(pidfile):
                        parser.error("pidfile {0} does not exist.".format(
                            pidfile))
                    with open(pidfile, "r") as f:
                        pid = int(f.read().strip())
                except IOError:
                    pid = None
                except ValueError:
                    pid = None
                # Test pid presence
                if not pid:
                    parser.error("Can not read pid from pidfile.")

    if opt.pidfile and not opt.daemon:
        parser.error("The option --daemon is required when using --pidfile.")

    # Log MySQL Utilities version string
    if opt.log_file:
        logging.info(MSG_UTILITIES_VERSION.format(utility=program,
                                                  version=VERSION_STRING))
    try:
        rpl_cmds = RplCommands(master_val, slaves_val, options)
        if opt.daemon:
            rpl_cmds.auto_failover_as_daemon()
        else:
            rpl_cmds.auto_failover(opt.interval)
    except UtilError:
        _, e, _ = sys.exc_info()
        # log the error in case it was an usual exception
        logging.log(logging.CRITICAL, e.errmsg.strip(' '))
        print("ERROR: %s" % e.errmsg)
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(0)

    sys.exit(0)
