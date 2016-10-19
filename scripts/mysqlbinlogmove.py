#!/usr/bin/env python
#
# Copyright (c) 2014, 2016, Oracle and/or its affiliates. All rights reserved.
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
This file contains the binlog relocate utility. It is used to move binlog
files to a different location, updating the binlog index files accordingly.
"""

import os
import sys
import mysql.utilities.command.binlog_admin as binlog_admin

from mysql.utilities.common.tools import check_python_version
from mysql.utilities.common.binary_log_file import (LOG_TYPE_BIN,
                                                    LOG_TYPE_RELAY,
                                                    LOG_TYPES)
from mysql.utilities.common.ip_parser import parse_connection
from mysql.utilities.common.messages import (PARSE_ERR_OPTS_EXCLD,
                                             PARSE_ERR_OPTS_REQ,
                                             WARN_OPT_NOT_REQUIRED_FOR_TYPE,
                                             WARN_OPT_ONLY_USED_WITH)
from mysql.utilities.common.options import (add_verbosity, check_date_time,
                                            check_dir_option,
                                            get_absolute_path,
                                            get_value_intervals_list,
                                            setup_common_options)
from mysql.utilities.common.tools import check_connector_python
from mysql.utilities.exception import FormatError, UtilError

# Check Python version compatibility
check_python_version()

# Check for connector/python
if not check_connector_python():
    sys.exit(1)

# Constants
NAME = "MySQL Utilities - mysqlbinlogmove"
DESCRIPTION = "mysqlbinlogmove - binary log relocate utility"
USAGE = "%prog --server=user:pass@host:port <destination_directory>"
EXTENDED_HELP = """
Introduction
------------
The mysqlbinlogmove utility was designed to relocate binary log files to a new
location in a simple and easy way. The use of this utility is recommended when
you intend to change the base location for the binlog files (enabled with the
server option --log-bin) moving all binlog files to the target location and
updating all required index files. It is also useful to archive some binary
log files to a different location.

Note: In order to relocate all binary log files the mysql server must be
stopped. This requirement is not needed if only some of binary log files are
relocated.

The behaviour of the utility depends on the options specified. Use the
--binlog_dir option to relocate all binary logs. Use the --server option to
relocate all binary logs except the ones currently in use (with the higher
sequence number). The target destination directory must be specified as an
argument and other option can be used to restrict the binary log files that
will be moved, as shown in the following examples.

  # Move all binlog files to a new location (from /old/location
  # to /new/location).

  $ mysqlbinlogmove --binlog-dir=/old/location /new/location

  # Move all binlog files except the one currently in use to a new
  # location (from the server log_bin_basename directory to /new/location).

  $ mysqlbinlogmove --server=root:pass@host1:3306 /new/location

  # Move all binlog files within a specific sequence range (10-100),
  # except the one currently in use, to a new location (from the server
  # log_bin_basename directory to /new/location).

  $ mysqlbinlogmove --server=root:pass@host1:3306 --sequence=10-100 \\
                    /new/location

  # Move all binlog files not modified in the last two days, except the one
  # currently in use, to a new location (from the server log_bin_basename
  # directory to /new/location).

  $ mysqlbinlogmove --server=root:pass@host1:3306 --modified-before=2 \\
                    /new/location

  # Move all binlog files older than a specific date (not modified),
  # except the one currently in use, to a new location (from the server
  # log_bin_basename directory to /new/location).

  $ mysqlbinlogmove --server=root:pass@host1:3306 \\
                    --modified-before=2004-07-30 /new/location


Helpful Hints
-------------
  - By default only binlog files are moved. To move relay log files or both
    use the --log-type option with the desired value.
  - By default the utility will try to automatically determine the base name
    for the binary logs and index files by applying the default filename
    formats and files location. If custom file names are used, you can specify
    them using the options --bin-log-index, --bin-log-basename,
    --relay-log-index, and --relay-log-basename, respectively for binlog and
    relay log files.
  - When the --server option is used by default binary logs are flushed at the
    end of the relocate operation in order to update the server's info. Use
    --skip-flush-binlogs to skip this step.
"""

if __name__ == '__main__':
    # Setup the command parser (with common options including --server).
    parser = setup_common_options(os.path.basename(sys.argv[0]),
                                  DESCRIPTION, USAGE, server=True,
                                  server_default=None,
                                  extended_help=EXTENDED_HELP)

    # Source bin-log base directory (where files to move are located).
    parser.add_option("--binlog-dir", action="store", dest="binlog_dir",
                      type="string", default=None,
                      help="Source directory (full path) where the binary log "
                           "files to move are located.")

    # Basename for binlogs (filename without the extension).
    parser.add_option("--bin-log-basename", action="store",
                      dest="bin_log_basename", type="string", default=None,
                      help="Basename for the binlog files. "
                           "If not available it is assumed to be any name "
                           "ended with '-bin'.")

    # Basename for relay-logs (filename without the extension).
    parser.add_option("--relay-log-basename", action="store",
                      dest="relay_log_basename", type="string", default=None,
                      help="Basename for the relay log files. "
                           "If not available it is assumed to be any name "
                           "ended with '-relay-bin'.")

    # Index file for binlogs (full path).
    parser.add_option("--bin-log-index", action="store", dest="bin_log_index",
                      type="string", default=None,
                      help="Location (full path) of the binlogs index file. "
                           "If not specified it is assumed to be located in "
                           "the binary log directory.")

    # Index file for relay-logs (full path).
    parser.add_option("--relay-log-index", action="store",
                      dest="relay_log_index", type="string", default=None,
                      help="Location (full path) of the relay logs index "
                           "file. If not specified it is assumed to be "
                           "located in the binary log directory.")

    # Add verbose option (no --quiet option).
    add_verbosity(parser, False)

    # Add option to specify the type of the binary log files to process.
    parser.add_option("--log-type", action="store", dest="log_type",
                      type="choice", default=LOG_TYPE_BIN,
                      choices=LOG_TYPES,
                      help="type of the binary log files to relocate: "
                           "'bin' - bin-log files (default), "
                           "'relay' - relay-log files, "
                           "'all' - bin-log and relay-log files.")

    # Add option to filter the files by sequence number.
    parser.add_option("--sequence", action="store", dest="sequence",
                      type="string", default=None,
                      help="relocate files with the specified sequence "
                           "values. Accepts a comma-separated list of "
                           "non-negative integers (corresponding to the file "
                           "sequence number) or intervals marked with a dash. "
                           "For example: 3,5-12,16,21.")

    # Add option to filter the files by modified date.
    parser.add_option("--modified-before", action="store",
                      dest="modified_before", type="string", default=None,
                      help="relocate files with the modified date prior to "
                           "the specified date/time or number of days. "
                           "Accepts a date/time in the format: "
                           "yyyy-mm-ddThh:mm:ss or yyyy-mm-dd, or an integer "
                           "for the elapsed days.")

    # Add option to skip the flush binary/relay logs operation.
    parser.add_option("--skip-flush-binlogs", action="store_true",
                      dest="skip_flush_binlogs", default=False,
                      help="Skip the binary/relay flush operation to reload "
                           "server's cache after moving files.")

    # Parse the options and arguments.
    opt, args = parser.parse_args()

    # The --server and --binlog-dir options cannot be used simultaneously
    # (only one).
    if opt.server and opt.binlog_dir:
        parser.error(PARSE_ERR_OPTS_EXCLD.format(opt1='--server',
                                                 opt2='--binlog-dir'))

    # Check mandatory options: --server or --binlog-dir.
    if not opt.server and not opt.binlog_dir:
        parser.error(PARSE_ERR_OPTS_REQ.format(
            opt="--server' or '--binlog-dir"))

    # Check specified server.
    server_val = None
    if opt.server:
        # Parse server connection values
        try:
            server_val = parse_connection(opt.server, None, opt)
        except FormatError:
            _, err, _ = sys.exc_info()
            parser.error("Server connection values invalid: %s." % err)
        except UtilError:
            _, err, _ = sys.exc_info()
            parser.error("Server connection values invalid: %s." % err.errmsg)

    # Check specified source binlog directory.
    binlog_dir = None
    if opt.binlog_dir:
        # Check the access to the source binlog directory.
        binlog_dir = check_dir_option(parser, opt.binlog_dir, '--binlog-dir',
                                      check_access=True, read_only=True)

    # Check destination directory.
    num_args = len(args)
    if num_args < 1:
        parser.error("You must specify the destination directory as argument.")
    elif num_args > 1:
        parser.error("You can only specify one destination directory. "
                     "Multiple arguments found.")
    else:
        destination = get_absolute_path(args[0])
        if not os.path.isdir(destination):
            parser.error("The destination path specified as argument is not a "
                         "valid directory: {0}".format(args[0]))
        if not os.access(destination, os.R_OK | os.W_OK):
            parser.error("You do not have enough privileges to access the "
                         "specified destination directory: "
                         "{0}.".format(args[0]))

    # Check specified path for the binlog index file.
    bin_log_index_file = None
    if opt.bin_log_index:
        bin_log_index_file = get_absolute_path(opt.bin_log_index)
        if not os.path.isfile(bin_log_index_file):
            parser.error("The specified value for --bin-index is not a "
                         "file: {0}".format(opt.bin_log_index))
        if not os.access(bin_log_index_file, os.R_OK | os.W_OK):
            parser.error("You do not have enough privileges to access the "
                         "specified binlog index file: "
                         "{0}.".format(opt.bin_log_index))

    # Check specified path for the relay log index file.
    relay_log_index_file = None
    if opt.relay_log_index:
        relay_log_index_file = get_absolute_path(opt.relay_log_index)
        if not os.path.isfile(relay_log_index_file):
            parser.error("The specified value for --relay-index is not a "
                         "file: {0}".format(opt.relay_log_index))
        if not os.access(relay_log_index_file, os.R_OK | os.W_OK):
            parser.error("You do not have enough privileges to access the "
                         "specified relay log index file: "
                         "{0}.".format(opt.relay_log_index))

    # Check values specified for the --sequence option.
    sequence_list = []
    if opt.sequence:
        sequence_list = get_value_intervals_list(parser, opt.sequence,
                                                 '--sequence', 'sequence')

    # Check values specified for the --modified-before option.
    modified_before = None
    if opt.modified_before:
        modified_before = check_date_time(parser, opt.modified_before,
                                          'modified', allow_days=True)

    # Check options not required for specific log types.
    if opt.log_type == LOG_TYPE_BIN:
        if opt.relay_log_basename:
            print(WARN_OPT_NOT_REQUIRED_FOR_TYPE.format(
                opt='--relay-log-basename',
                type='{0}log'.format(LOG_TYPE_BIN)))
        if opt.relay_log_index:
            print(WARN_OPT_NOT_REQUIRED_FOR_TYPE.format(
                opt='--relay-log-index',
                type='{0}log'.format(LOG_TYPE_BIN)))
    if opt.log_type == LOG_TYPE_RELAY:
        if opt.bin_log_basename:
            print(WARN_OPT_NOT_REQUIRED_FOR_TYPE.format(
                opt='--bin-log-basename',
                type='{0} log'.format(LOG_TYPE_RELAY)))
        if opt.bin_log_index:
            print(WARN_OPT_NOT_REQUIRED_FOR_TYPE.format(
                opt='--bin-log-index',
                type='{0} log'.format(LOG_TYPE_RELAY)))

    # Check use of the --skip-flush-binlogs option.
    if not opt.server and opt.skip_flush_binlogs:
        print(WARN_OPT_ONLY_USED_WITH.format(opt='--skip-flush-binlogs',
                                             used_with='--server'))

    # Create dictionary of options
    options = {
        'verbosity': 0 if opt.verbosity is None else opt.verbosity,
        'log_type': opt.log_type,
        'sequence': sequence_list,
        'modified_before': modified_before,
        'skip_flush_binlogs': opt.skip_flush_binlogs,
    }

    # Relocate binary log files.
    try:
        # Relocate binary log files based for specified server.
        if server_val:
            binlog_admin.move_binlogs_from_server(
                server_val, destination, options,
                bin_basename=opt.bin_log_basename,
                bin_index=bin_log_index_file,
                relay_basename=opt.relay_log_basename
            )

        # Relocate binary log files from given source binlog directory.
        if binlog_dir:
            binlog_admin.move_binlogs(
                binlog_dir, destination, options,
                bin_basename=opt.bin_log_basename,
                bin_index=bin_log_index_file,
                relay_basename=opt.relay_log_basename,
                relay_index=relay_log_index_file
            )

    except UtilError:
        _, err, _ = sys.exc_info()
        sys.stderr.write("ERROR: {0}\n".format(err.errmsg))
        sys.exit(1)
