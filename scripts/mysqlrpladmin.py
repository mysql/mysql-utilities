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
import os.path
import sys

from mysql.utilities.common.tools import check_python_version
from mysql.utilities import VERSION_FRM, VERSION_STRING
from mysql.utilities.exception import UtilError, UtilRplError, FormatError
from mysql.utilities.common.ip_parser import parse_connection
from mysql.utilities.common.server import Server, check_hostname_alias
from mysql.utilities.common.tools import check_connector_python
from mysql.utilities.common.topology import parse_topology_connections
from mysql.utilities.common.options import (add_format_option, add_verbosity,
                                            add_failover_options, add_rpl_user,
                                            add_ssl_options,
                                            CaseInsensitiveChoicesOption,
                                            check_server_lists,
                                            get_ssl_dict,
                                            license_callback, UtilitiesParser,
                                            check_password_security,
                                            check_script_option)
from mysql.utilities.common.messages import (PARSE_ERR_OPT_INVALID_CMD_TIP,
                                             PARSE_ERR_OPTS_EXCLD,
                                             PARSE_ERR_OPTS_REQ_BY_CMD,
                                             PARSE_ERR_SLAVE_DISCO_REQ,
                                             WARN_OPT_NOT_REQUIRED,
                                             WARN_OPT_NOT_REQUIRED_ONLY_FOR,
                                             ERROR_SAME_MASTER,
                                             ERROR_MASTER_IN_SLAVES,
                                             SCRIPT_THRESHOLD_WARNING, SLAVES,
                                             CANDIDATES,
                                             MSG_UTILITIES_VERSION)
from mysql.utilities.command.rpl_admin import (RplCommands, purge_log,
                                               get_valid_rpl_commands,
                                               get_valid_rpl_command_text)

# Check Python version compatibility
check_python_version()


class MyParser(UtilitiesParser):
    """Custom class to set the epilog.
    """
    def format_epilog(self, formatter):
        return self.epilog

# Constants
NAME = "MySQL Utilities - mysqlrpladmin "
DESCRIPTION = "mysqlrpladmin - administration utility for MySQL replication"
USAGE = "%prog --slaves=root@localhost:3306 <command>"
_DATE_FORMAT = '%Y-%m-%d %H:%M:%S %p'

# Check for connector/python
if not check_connector_python():
    sys.exit(1)

if __name__ == '__main__':
    # Setup the command parser
    program = os.path.basename(sys.argv[0]).replace(".py", "")
    parser = MyParser(
        version=VERSION_FRM.format(program=program),
        description=DESCRIPTION,
        usage=USAGE,
        add_help_option=False,
        option_class=CaseInsensitiveChoicesOption,
        epilog=get_valid_rpl_command_text(),
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

    # Connection information for the master
    # Connect information for candidate server for switchover
    parser.add_option("--new-master", action="store", dest="new_master",
                      default=None, type="string",
                      help="connection information for the slave to be used to"
                           " replace the master for switchover, in the form: "
                           "<user>[:<password>]@<host>[:<port>][:<socket>] or "
                           "<login-path>[:<port>][:<socket>] or "
                           "<config-path>[<[group]>]. Valid only with "
                           "switchover command.")

    # Force the execution of the command, ignoring some errors
    parser.add_option("--force", action="store_true", dest="force",
                      help="ignore prerequisite check results or some "
                           "inconsistencies found (e.g. errant transactions "
                           "on slaves) and execute action")

    # Output format
    add_format_option(parser, "display the output in either grid (default), "
                      "tab, csv, or vertical format", None)

    # Add demote option
    parser.add_option("--demote-master", action="store_true", dest="demote",
                      help="make master a slave after switchover.")

    # Add no-health option
    parser.add_option("--no-health", action="store_true", dest="no_health",
                      help="turn off health report after switchover or "
                           "failover.")

    # Add verbosity mode
    add_verbosity(parser, True)

    # Replication user and password
    add_rpl_user(parser)

    # Add ssl options
    add_ssl_options(parser)

    # Now we process the rest of the arguments.
    opt, args = parser.parse_args()

    # Check security settings
    check_password_security(opt, args)

    # Check for invalid command
    if len(args) > 1:
        parser.error("You can only specify one command to execute at a time.")
    elif len(args) == 0:
        parser.error("You must specify a command to execute.")

    command = args[0].lower()

    # At least one of the options --discover-slaves-login or --slaves is
    # required unless we are doing a health or failover command.
    if (not opt.discover and not opt.slaves and
            command not in ('health', 'failover')):
        parser.error(PARSE_ERR_SLAVE_DISCO_REQ)

    # --discover-slaves-login and --slaves cannot be used simultaneously
    # (only one)
    if opt.discover and opt.slaves:
        parser.error(PARSE_ERR_OPTS_EXCLD.format(
            opt1='--discover-slaves-login', opt2='--slaves'
        ))

    # Check slaves list
    check_server_lists(parser, opt.master, opt.slaves)

    # The value for --timeout needs to be an integer > 0.
    try:
        if int(opt.timeout) <= 0:
            parser.error("The --timeout option requires a value greater "
                         "than 0.")
    except ValueError:
        parser.error("The --timeout option requires an integer value.")

    # Check errors and warnings of options and combinations.

    if command not in get_valid_rpl_commands():
        parser.error("'{0}' is not a valid command.".format(command))

    # --master and --new-master options are required by 'switchover'
    if command == 'switchover' and (not opt.new_master or not opt.master):
        req_opts = '--master and --new-master'
        parser.error(PARSE_ERR_OPTS_REQ_BY_CMD.format(cmd=command,
                                                      opts=req_opts))

    # Allow health report for --master or --slaves
    if command == 'health' and not opt.master and not opt.slaves:
        req_opts = '--master or --slaves'
        parser.error(PARSE_ERR_OPTS_REQ_BY_CMD.format(cmd=command,
                                                      opts=req_opts))

    # --master and either --slaves or --discover-slaves-login options are
    # required by 'elect' and 'gtid'
    if (command in ['elect', 'gtid'] and not opt.master and
            (not opt.slaves or not opt.discover)):
        req_opts = '--master and either --slaves or --discover-slaves-login'
        parser.error(PARSE_ERR_OPTS_REQ_BY_CMD.format(cmd=command,
                                                      opts=req_opts))

    # --slaves options are required by 'start', 'stop' and 'reset'
    # --master is optional
    if command in ['start', 'stop', 'reset'] and not opt.slaves:
        req_opts = '--slaves'
        parser.error(PARSE_ERR_OPTS_REQ_BY_CMD.format(cmd=command,
                                                      opts=req_opts))

    # Validate the required options for the failover command
    if command == 'failover':
        # --discover-slaves-login is invalid (as it will require a master)
        # instead --slaves needs to be used.
        if opt.discover:
            invalid_opt = '--discover-slaves-login'
            parser.error(PARSE_ERR_OPT_INVALID_CMD_TIP.format(
                opt=invalid_opt, cmd=command, opt_tip='--slaves'))
        # --master will be ignored
        if opt.master:
            print(WARN_OPT_NOT_REQUIRED.format(opt='--master', cmd=command))
            opt.master = None
        if not opt.slaves:
            req_opts = '--slaves'
            parser.error(PARSE_ERR_OPTS_REQ_BY_CMD.format(cmd=command,
                                                          opts=req_opts))

    # --ping only used by 'health' command
    if opt.ping and command != 'health':
        print(WARN_OPT_NOT_REQUIRED_ONLY_FOR.format(opt='--ping', cmd=command,
                                                    only_cmd='health'))
        opt.ping = None

    # --exec-after only used by 'failover' or 'switchover' command
    if opt.exec_after and command not in ['switchover', 'failover']:
        only_used_cmds = 'failover or switchover'
        print(WARN_OPT_NOT_REQUIRED_ONLY_FOR.format(opt='--exec-after',
                                                    cmd=command,
                                                    only_cmd=only_used_cmds))
        opt.exec_after = None

    # --exec-before only used by 'failover' or 'switchover' command
    if opt.exec_before and command not in ['switchover', 'failover']:
        only_used_cmds = 'failover or switchover'
        print(WARN_OPT_NOT_REQUIRED_ONLY_FOR.format(opt='--exec-before',
                                                    cmd=command,
                                                    only_cmd=only_used_cmds))
        opt.exec_before = None

    # --new-master only required for 'switchover' command
    if opt.new_master and command != 'switchover':
        print(WARN_OPT_NOT_REQUIRED_ONLY_FOR.format(opt='--new-master',
                                                    cmd=command,
                                                    only_cmd='switchover'))
        opt.new_master = None

    # --candidates only used by 'failover' or 'elect' command
    if opt.candidates and command not in ['elect', 'failover']:
        only_used_cmds = 'failover or elect'
        print(WARN_OPT_NOT_REQUIRED_ONLY_FOR.format(opt='--candidates',
                                                    cmd=command,
                                                    only_cmd=only_used_cmds))
        opt.candidates = None

    # --format only used by 'health' or 'gtid' command
    if opt.format and command not in ['health', 'gtid']:
        only_used_cmds = 'health or gtid'
        print(WARN_OPT_NOT_REQUIRED_ONLY_FOR.format(opt='--format',
                                                    cmd=command,
                                                    only_cmd=only_used_cmds))
        opt.format = None

    # Parse the --new-master connection string
    if opt.new_master:
        try:
            new_master_val = parse_connection(opt.new_master, None, opt)
        except FormatError:
            _, err, _ = sys.exc_info()
            parser.error("New master connection values invalid: "
                         "{0}.".format(err))
        except UtilError:
            _, err, _ = sys.exc_info()
            parser.error("New master connection values invalid: "
                         "{0}.".format(err.errmsg))
    else:
        new_master_val = None

    # Parse the master, slaves, and candidates connection parameters
    try:
        master_val, slaves_val, candidates_val = parse_topology_connections(
            opt)
    except UtilRplError:
        _, e, _ = sys.exc_info()
        print("ERROR: {0}".format(e.errmsg))
        sys.exit(1)

    # Check hostname alias
    if new_master_val:
        if check_hostname_alias(master_val, new_master_val):
            master = Server({'conn_info': master_val})
            new_master = Server({'conn_info': new_master_val})
            parser.error(ERROR_SAME_MASTER.format(
                n_master_host=new_master.host,
                n_master_port=new_master.port,
                master_host=master.host,
                master_port=master.port))

    if master_val:
        for slave_val in slaves_val:
            if check_hostname_alias(master_val, slave_val):
                master = Server({'conn_info': master_val})
                slave = Server({'conn_info': slave_val})
                msg = ERROR_MASTER_IN_SLAVES.format(master_host=master.host,
                                                    master_port=master.port,
                                                    slaves_candidates=SLAVES,
                                                    slave_host=slave.host,
                                                    slave_port=slave.port)
                parser.error(msg)
        for cand_val in candidates_val:
            if check_hostname_alias(master_val, cand_val):
                master = Server({'conn_info': master_val})
                candidate = Server({'conn_info': cand_val})
                msg = ERROR_MASTER_IN_SLAVES.format(
                    master_host=master.host,
                    master_port=master.port,
                    slaves_candidates=CANDIDATES,
                    slave_host=candidate.host,
                    slave_port=candidate.port)
                parser.error(msg)

    # Create dictionary of options
    options = {
        'new_master': new_master_val,
        'candidates': candidates_val,
        'ping': 3 if opt.ping is None else opt.ping,
        'format': opt.format,
        'verbosity': 0 if opt.verbosity is None else opt.verbosity,
        'before': opt.exec_before,
        'after': opt.exec_after,
        'force': opt.force,
        'max_position': opt.max_position,
        'max_delay': opt.max_delay,
        'discover': opt.discover,
        'timeout': int(opt.timeout),
        'demote': opt.demote,
        'quiet': opt.quiet,
        'logging': opt.log_file is not None,
        'log_file': opt.log_file,
        'no_health': opt.no_health,
        'rpl_user': opt.rpl_user,
        'script_threshold': opt.script_threshold,
    }

    # Check if script files exist and are executable and warn users if they
    # are not.
    script_opts = ['after', 'before']
    for key in script_opts:
        parameter_val = options[key]
        check_script_option(parser, parameter_val)

    # Add ssl options to options instead of connection.
    options.update(get_ssl_dict(opt))

    # If command = HEALTH, turn on --force
    if command == 'health' or command == 'gtid':
        options['force'] = True

    # Purge log file of old data
    if opt.log_file is not None and not purge_log(opt.log_file, opt.log_age):
        parser.error("Error purging log file.")

    # Warn user about script threshold checking.
    if opt.script_threshold:
        print(SCRIPT_THRESHOLD_WARNING)

    # Setup log file
    try:
        logging.basicConfig(filename=opt.log_file, level=logging.INFO,
                            format='%(asctime)s %(levelname)s %(message)s',
                            datefmt=_DATE_FORMAT)
    except IOError:
        _, e, _ = sys.exc_info()
        parser.error("Error opening log file: %s" % str(e.args[1]))

    # Log MySQL Utilities version string
    if opt.log_file:
        logging.info(MSG_UTILITIES_VERSION.format(utility=program,
                                                  version=VERSION_STRING))

    try:
        rpl_cmds = RplCommands(master_val, slaves_val, options)
        rpl_cmds.execute_command(command, options)
    except UtilError:
        _, e, _ = sys.exc_info()
        print("ERROR: {0}".format(e.errmsg))
        sys.exit(1)

    sys.exit(0)
