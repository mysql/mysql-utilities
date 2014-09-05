#
# Copyright (c) 2014, Oracle and/or its affiliates. All rights reserved.
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
This file contains commands methods methods for working with binary log files.
For example: to relocate binary log files to a new location.
"""

import os.path
import shutil

from mysql.utilities.common.binary_log_file import (
    is_binary_log_filename, filter_binary_logs_by_sequence,
    filter_binary_logs_by_date, get_index_file, LOG_TYPE_ALL, LOG_TYPE_BIN,
    LOG_TYPE_RELAY, move_binary_log
)
from mysql.utilities.common.messages import ERROR_USER_WITHOUT_PRIVILEGES
from mysql.utilities.common.server import Server
from mysql.utilities.common.user import User
from mysql.utilities.exception import UtilError


_ACTION_DATADIR_USED = ("The 'datadir' will be used as base directory for "
                        "{file_type} files.")
_ACTION_SEARCH_INDEX = ("The utility will try to find the index file in the"
                        "base directory for {file_type} files.")
_ERR_MSG_MOVE_FILE = "Unable to move binary file: {filename}\n{error}"
_INFO_MSG_APPLY_FILTERS = ("# Applying {filter_type} filter to {file_type} "
                           "files...")
_INFO_MSG_FLUSH_LOGS = "# Flushing {log_type} logs..."
_INFO_MSG_INDEX_FILE = "# Index file found for {file_type}: {index_file}"
_INFO_MSG_MOVE_FILES = "# Moving {file_type} files..."
_INFO_MSG_NO_FILES_TO_MOVE = "# No {file_type} files will be moved."
_WARN_MSG_FLUSH_LOG_TYPE = (
    "# WARNING: Flush for {log_type} logs is not available for server "
    "'{host}:{port}' (operation skipped). Requires server version >= 5.5.3 ."
)
_WARN_MSG_VAL_NOT_REQ_FOR_SERVER = (
    "# WARNING: The {value} is not required for server versions >= "
    "{min_version} (value ignored). Replaced by value for variable "
    "'{var_name}'."
)
_WARN_MSG_VAR_NOT_AVAILABLE = (
    "# WARNING: Variable '{var_name}' is not available for server "
    "'{host}:{port}'. Requires server version >= {min_version}. {action}"
)
_WARN_MSG_NO_FILE = "# WARNING: No {file_type} files found to move."


def _move_binlogs(source, destination, log_type, options, basename=None,
                  index_file=None, skip_latest=False):
    """Move binary log files of the specified type.

    This auxiliary function moves the binary log files of a specific type
    (i.e., binary or relay) from the given source to the specified destination
    directory. It gets the files only for the specified binary log type and
    applies any filtering in accordance to the specified options. Resulting
    files are moved and the respective index file updated accordingly.

    source[in]          Source location of the binary log files to move.
    destination[in]     Destination directory for the binary log files.
    log_type[in]        Type of the binary log files ('bin' or 'relay').
    options[in]         Dictionary of options (modified_before, sequence,
                        verbosity).
    basename[in]        Base name for the binary log files, i.e. filename
                        without the extension (sequence number).
    index_file[in]      Path of the binary log index file. If not specified it
                        is assumed to be located in the source directory and
                        determined based on the basename of the first found
                        binary log file.
    skip_latest[in]     Bool value indication if the latest binary log file
                        (with the higher sequence value; in use by the
                        server) will be skipped or not. By default = False,
                        meaning that no binary log file is skipped.

    Returns the number of files moved.
    """
    verbosity = options['verbosity']
    binlog_files = []
    file_type = '{0}-log'.format(log_type)
    if basename:
        # Ignore path from basename if specified, source is used instead.
        _, basename = os.path.split(basename)
    # Get binary log files to move.
    for _, _, filenames in os.walk(source):
        for f_name in sorted(filenames):
            if is_binary_log_filename(f_name, log_type, basename):
                binlog_files.append(f_name)
        break
    if skip_latest:
        # Skip last file (with the highest sequence).
        # Note; filenames are sorted by ascending order.
        binlog_files = binlog_files[:-1]
    if not binlog_files:
        # No binary log files found to move.
        print(_WARN_MSG_NO_FILE.format(file_type=file_type))
    else:
        # Apply filters.
        sequence = options.get('sequence', None)
        if sequence:
            print("#")
            print(_INFO_MSG_APPLY_FILTERS.format(filter_type='sequence',
                                                 file_type=file_type))
            binlog_files = filter_binary_logs_by_sequence(binlog_files,
                                                          sequence)
        modified_before = options.get('modified_before', None)
        if modified_before:
            print("#")
            print(_INFO_MSG_APPLY_FILTERS.format(filter_type='modified date',
                                                 file_type=file_type))
            binlog_files = filter_binary_logs_by_date(binlog_files, source,
                                                      modified_before)
        # Move files.
        print("#")
        if binlog_files:
            if index_file is None:
                # Get binary log index file.
                index_file = get_index_file(source, binlog_files[0])
                if verbosity > 0:
                    print(_INFO_MSG_INDEX_FILE.format(file_type=file_type,
                                                      index_file=index_file))
                    print("#")
            print(_INFO_MSG_MOVE_FILES.format(file_type=file_type))
            for f_name in binlog_files:
                try:
                    print("# - {0}".format(f_name))
                    move_binary_log(source, destination, f_name, index_file)
                except (shutil.Error, IOError) as err:
                    raise UtilError(_ERR_MSG_MOVE_FILE.format(filename=f_name,
                                                              error=err))
            return len(binlog_files)
        else:
            print(_INFO_MSG_NO_FILES_TO_MOVE.format(file_type=file_type))
            return 0


def move_binlogs(binlog_dir, destination, options, bin_basename=None,
                 bin_index=None, relay_basename=None, relay_index=None):
    """Move binary logs from the given source to the specified destination.

    This function relocates the binary logs from the given source path to the
    specified destination directory according to the specified options.

    binlog_dir[in]      Path of the source directory for the binary log files
                        to move.
    destination[in]     Path of the destination directory for the binary log
                        files.
    options[in]         Dictionary of options (log_type, modified_before,
                        sequence, verbosity).
    bin_basename[in]    Base name for the binlog files, i.e. filename
                        without the extension (sequence number).
    bin_index[in]       Path of the binlog index file. If not specified it is
                        assumed to be located in the source directory.
    relay_basename[in]  Base name for the relay log files, i.e. filename
                        without the extension (sequence number).
    relay_index[in]     Path of the relay log index file. If not specified it
                        is assumed to be located in the source directory.
    skip_latest[in]     Bool value indication if the latest binary log file
                        (with the higher sequence value; in use by the
                        server) will be skipped or not. By default = False,
                        meaning that no binary log file is skipped.
    """
    log_type = options['log_type']
    # Move binlog files.
    if log_type in (LOG_TYPE_BIN, LOG_TYPE_ALL):
        _move_binlogs(binlog_dir, destination, LOG_TYPE_BIN, options,
                      basename=bin_basename, index_file=bin_index)
        print("#")
    # Move relay log files.
    if log_type in (LOG_TYPE_RELAY, LOG_TYPE_ALL):
        _move_binlogs(binlog_dir, destination, LOG_TYPE_RELAY, options,
                      basename=relay_basename, index_file=relay_index)
        print("#")
    print("#...done.\n#")


def _check_privileges(server, options):
    """Check required privileges to move binary logs from server.

    This method check if the used user possess the required privileges to
    relocate binary logs from the server. More specifically, the following
    privilege is required: RELOAD (to flush the binary logs).
    An exception is thrown if the user doesn't have enough privileges.

    server[in]      Server instance to check.
    options[in]     Dictionary of options (skip_flush_binlogs, verbosity).
    """
    skip_flush = options['skip_flush_binlogs']

    if not skip_flush:
        # Only need to check privileges if flush is not skipped.
        verbosity = options['verbosity']
        if verbosity > 0:
            print("# Checking user permission to move binary logs...\n"
                  "#")

        # Check privileges
        user_obj = User(server, "{0}@{1}".format(server.user, server.host))
        if not user_obj.has_privilege('*', '*', 'RELOAD'):
            raise UtilError(ERROR_USER_WITHOUT_PRIVILEGES.format(
                user=server.user, host=server.host, port=server.port,
                operation='perform binary log move', req_privileges='RELOAD'
            ))


def move_binlogs_from_server(server_cnx_val, destination, options,
                             bin_basename=None, bin_index=None,
                             relay_basename=None):
    """Relocate binary logs from the given server to a new location.

    This function relocate the binary logs from a MySQL server to the specified
    destination directory, attending to the specified options.

    server_cnx_val[in]  Dictionary with the connection values for the server.
    destination[in]     Path of the destination directory for the binary log
                        files.
    options[in]         Dictionary of options (log_type, skip_flush_binlogs,
                        modified_before, sequence, verbosity).
    bin_basename[in]    Base name for the binlog files, i.e., same as the
                        value for the server option --log-bin. It replaces
                        the server variable 'log_bin_basename' for versions
                        < 5.6.2, otherwise it is ignored.
    bin_index[in]       Path of the binlog index file. It replaces the server
                        variable 'log_bin_index' for versions < 5.6.4,
                        otherwise it is ignored.
    relay_basename[in]  Base name for the relay log files, i.e., filename
                        without the extension (sequence number). Same as the
                        value for the server option --relay-log. It replaces
                        the server variable 'relay_log_basename' for versions
                        < 5.6.2, otherwise it is ignored.
    """

    log_type = options.get('log_type', LOG_TYPE_BIN)
    skip_flush = options['skip_flush_binlogs']
    verbosity = options['verbosity']
    # Connect to server
    server_options = {
        'conn_info': server_cnx_val,
    }
    srv = Server(server_options)
    srv.connect()

    # Check if the server is running locally (not remote server).
    if not srv.is_alias('localhost'):
        raise UtilError("You are using a remote server. This utility must be "
                        "run on the local server. It does not support remote "
                        "access to the binary log files.")

    # Check privileges.
    _check_privileges(srv, options)

    # Process binlog files.
    if log_type in (LOG_TYPE_BIN, LOG_TYPE_ALL):
        # Get log_bin_basename (available since MySQL 5.6.2).
        if srv.check_version_compat(5, 6, 2):
            if bin_basename:
                print(_WARN_MSG_VAL_NOT_REQ_FOR_SERVER.format(
                    value='bin basename', min_version='5.6.2',
                    var_name='log_bin_basename'))
            binlog_basename = srv.select_variable('log_bin_basename')
            if verbosity > 0:
                print("#")
                print("# log_bin_basename: {0}".format(binlog_basename))
            binlog_source, binlog_file = os.path.split(binlog_basename)
            # Get log_bin_index (available since MySQL 5.6.4).
            if srv.check_version_compat(5, 6, 4):
                if bin_index:
                    print(_WARN_MSG_VAL_NOT_REQ_FOR_SERVER.format(
                        value='bin index', min_version='5.6.4',
                        var_name='log_bin_index'))
                binlog_index = srv.select_variable('log_bin_index')
            else:
                binlog_index = None
                action = _ACTION_SEARCH_INDEX.format(file_type='bin-log')
                print(_WARN_MSG_VAR_NOT_AVAILABLE.format(
                    var_name='log_bin_basename', host=srv.host, port=srv.port,
                    min_version='5.6.4', action=action))
            if verbosity > 0:
                print("# log_bin_index: {0}".format(binlog_index))
        else:
            if bin_basename:
                binlog_source, binlog_file = os.path.split(bin_basename)
            else:
                action = _ACTION_DATADIR_USED.format(file_type='bin-log')
                print(_WARN_MSG_VAR_NOT_AVAILABLE.format(
                    var_name='log_bin_basename', host=srv.host, port=srv.port,
                    min_version='5.6.2', action=action))
                # Get datadir value.
                binlog_source = srv.select_variable('datadir')
                binlog_file = None
                if verbosity > 0:
                    print("#")
                    print("# datadir: {0}".format(binlog_source))
            binlog_index = bin_index

        # Move binlog files.
        num_files = _move_binlogs(
            binlog_source, destination, LOG_TYPE_BIN, options,
            basename=binlog_file, index_file=binlog_index, skip_latest=True)
        print("#")

        # Flush binary logs to reload server's cache after move.
        if not skip_flush and num_files > 0:
            # Note: log_type for FLUSH available since MySQL 5.5.3.
            if srv.check_version_compat(5, 5, 3):
                print(_INFO_MSG_FLUSH_LOGS.format(log_type='binary'))
                srv.flush_logs(log_type='BINARY')
            else:
                print(_WARN_MSG_FLUSH_LOG_TYPE.format(log_type='binary',
                                                      host=srv.host,
                                                      port=srv.port))
            print("#")

    if log_type in (LOG_TYPE_RELAY, LOG_TYPE_ALL):
        # Get relay_log_basename (available since MySQL 5.6.2).
        if srv.check_version_compat(5, 6, 2):
            if relay_basename:
                print(_WARN_MSG_VAL_NOT_REQ_FOR_SERVER.format(
                    value='relay basename', min_version='5.6.2',
                    var_name='relay_log_basename'))
            relay_log_basename = srv.select_variable('relay_log_basename')
            if verbosity > 0:
                print("#")
                print("# relay_log_basename: {0}".format(relay_log_basename))
            relay_source, relay_file = os.path.split(relay_log_basename)
        else:
            if relay_basename:
                relay_source, relay_file = os.path.split(relay_basename)
            else:
                action = _ACTION_DATADIR_USED.format(file_type='relay-log')
                print(_WARN_MSG_VAR_NOT_AVAILABLE.format(
                    var_name='relay_log_basename', host=srv.host,
                    port=srv.port, min_version='5.6.2', action=action))
                # Get datadir value.
                relay_source = srv.select_variable('datadir')
                relay_file = None
                if verbosity > 0:
                    print("#")
                    print("# datadir: {0}".format(relay_source))
        # Get relay_log_index (available for all supported versions).
        relay_log_index = srv.select_variable('relay_log_index')
        if verbosity > 0:
            print("# relay_log_index: {0}".format(relay_log_index))

        # Move relay log files.
        num_files = _move_binlogs(
            relay_source, destination, LOG_TYPE_RELAY, options,
            basename=relay_file, index_file=relay_log_index, skip_latest=True)
        print("#")

        # Flush relay logs to reload server's cache after move.
        if not skip_flush and num_files > 0:
            # Note: log_type for FLUSH available since MySQL 5.5.3.
            if srv.check_version_compat(5, 5, 3):
                print(_INFO_MSG_FLUSH_LOGS.format(log_type='relay'))
                srv.flush_logs(log_type='RELAY')
            else:
                print(_WARN_MSG_FLUSH_LOG_TYPE.format(log_type='relay',
                                                      host=srv.host,
                                                      port=srv.port))
            print("#")

    print("#...done.\n#")
