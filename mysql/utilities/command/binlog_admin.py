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
This file contains commands methods methods for working with binary log files.
For example: to relocate binary log files to a new location.
"""

import logging
import os.path
import shutil

from mysql.utilities.common.binary_log_file import (
    is_binary_log_filename, filter_binary_logs_by_sequence,
    filter_binary_logs_by_date, get_index_file, LOG_TYPE_ALL, LOG_TYPE_BIN,
    LOG_TYPE_RELAY, move_binary_log
)
from mysql.utilities.common.binlog import (
    determine_purgeable_binlogs,
    get_active_binlog_and_size,
    get_binlog_info,
    purge,
    rotate,
)
from mysql.utilities.common.server import Server
from mysql.utilities.common.topology import Topology
from mysql.utilities.common.user import check_privileges
from mysql.utilities.exception import UtilError


BINLOG_OP_MOVE = "perform binary log move"
BINLOG_OP_MOVE_DESC = "move binary logs"
BINLOG_OP_PURGE = "perform binary log purge"
BINLOG_OP_PURGE_DESC = "purge binary logs"
BINLOG_OP_ROTATE = "perform binary log rotation"
BINLOG_OP_ROTATE_DESC = "rotate binary logs"
_ACTION_DATADIR_USED = ("The 'datadir' will be used as base directory for "
                        "{file_type} files.")
_ACTION_SEARCH_INDEX = ("The utility will try to find the index file in the"
                        "base directory for {file_type} files.")
_CAN_NOT_VERIFY_SLAVES_STATUS = (
    "Can not verify the slaves status for the given master {host}:{port}. "
    "Make sure the slaves are active and accessible."
)
_CAN_NOT_VERIFY_SLAVE_STATUS = (
    "Can not verify the status for slave {host}:{port}. "
    "Make sure the slave are active and accessible."
)
_COULD_NOT_FIND_BINLOG = (
    "WARNING: Could not find the given binlog name: '{bin_name}' "
    "in the binlog files listed in the {server_name}: {host}:{port}"
)
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


def _check_privileges_to_move_binlogs(server, options):
    """Check required privileges to move binary logs from server.

    This method check if the used user possess the required privileges to
    relocate binary logs from the server. More specifically, the following
    privilege is required: RELOAD (to flush the binary logs).
    An exception is thrown if the user doesn't have enough privileges.

    server[in]      Server instance to check.
    options[in]     Dictionary of options (skip_flush_binlogs, verbosity).
    """
    skip_flush = options['skip_flush_binlogs']
    verbosity = options['verbosity']
    if not skip_flush:
        check_privileges(server, BINLOG_OP_MOVE, ['RELOAD'],
                         BINLOG_OP_MOVE_DESC, verbosity)


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
    _check_privileges_to_move_binlogs(srv, options)

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


def _report_binlogs(binlog_list, reporter, removed=False):
    """Reports the binary files available and removed.

    binlog_list[in]    A list of binlog file names.
    reporter[in]       A reporter that receives the messages as parameter
    removed[in]        The given list of binlog file names are removed files.
                       Default is False, meaning files are available.

    Uses the reporter to reports the binary files available and removed.
    """
    if removed:
        msg = ("binlog file", "purged")
    else:
        msg = ("binlog file", "available")

    if len(binlog_list) == 1:
        reporter("# {0} {1}: {2}"
                 "".format(msg[0].capitalize(), msg[1], binlog_list[0]))

    if len(binlog_list) > 1:
        end_range = "from {0} to {1}".format(binlog_list[0], binlog_list[-1])
        reporter("# Range of {0}s {1}: {2}"
                 "".format(msg[0], msg[1], end_range))


def binlog_purge(server_cnx_val, master_cnx_val, slaves_cnx_val, options):
    """Purge binary log.

    Purges the binary logs from a server, it will purge all of the binlogs
    older than the active binlog file or the given target binlog index.
    For a master server determines the latest log file to purge among all the
    slaves, which becomes the target file to purge binary logs to, in case no
    other file is specified.

    server_cnx_val[in]    Server connection dictionary.
    master_cnx_val[in]    Master server connection dictionary.
    slaves_cnx_val[in]    Slave server connection dictionary.
    options[in]           Options dictionary.
        to_binlog_name    The target binlog index, in case doesn't want
                          to use the active binlog file or the index last in
                          use in a replication scenario.
        verbosity         print extra data during operations default level
                          value = 0
        discover          discover the list of slaves associated to the
                          specified login (user and password).
        dry_run           Don't actually rotate the active binlog, instead
                          it will print information about file name and size.

    """
    assert not (server_cnx_val is None and master_cnx_val is None), \
        "At least one of server_cnx_val or master_cnx_val must be a valid"\
        " dictionary with server connection values"

    if master_cnx_val is not None:
        rpl_purger = RPLBinaryLogPurge(master_cnx_val, slaves_cnx_val, options)
        rpl_purger.purge()
    else:
        binlog_purger = BinaryLogPurge(server_cnx_val, options)
        binlog_purger.purge()


class BinaryLogPurge(object):
    """BinaryLogPurge
    """

    def __init__(self, server_cnx_val, options):
        """Initiator.

        server_cnx_val[in]    Server connection dictionary.
        options[in]        Options dictionary.
        """

        self.server_cnx_val = server_cnx_val
        self.server = None
        self.options = options
        self.verbosity = self.options.get("verbosity", 0)
        self.quiet = self.options.get("quiet", False)
        self.logging = self.options.get("logging", False)
        self.dry_run = self.options.get("dry_run", 0)
        self.to_binlog_name = self.options.get("to_binlog_name", False)

    def _report(self, message, level=logging.INFO, print_msg=True):
        """Log message if logging is on.

        This method will log the message presented if the log is turned on.
        Specifically, if options['log_file'] is not None. It will also
        print the message to stdout.

        message[in]      Message to be printed.
        level[in]        Level of message to log. Default = INFO.
        print_msg[in]    If True, print the message to stdout. Default = True.
        """
        # First, print the message.
        if print_msg and not self.quiet:
            print(message)
        # Now log message if logging turned on
        if self.logging:
            logging.log(int(level), message.strip("#").strip(" "))

    def get_target_binlog_index(self, binlog_file_name):
        """Retrieves the target binlog file index.

        Retrieves the target binlog file index that will used in the purge
        query, by the fault the latest log not in use unless the user
        specifies a different target which is validated against the server's
        binlog base name.

        binlog_file_name[in]    the binlog base file name used by the server.

        Returns the target index binlog file
        """
        if self.to_binlog_name:
            to_binlog_name = self.to_binlog_name.split('.')[0]
            if to_binlog_name != binlog_file_name:
                raise UtilError(
                    "The given binlog file name: '{0}' differs "
                    "from the used by the server: '{1}'"
                    "".
                    format(to_binlog_name, binlog_file_name))
            else:
                to_binlog_index = int(self.to_binlog_name.split('.')[1])
            return to_binlog_index
        return None

    def _purge(self, index_last_in_use, active_binlog_file, binlog_file_name,
               target_binlog_index=None, server=None, server_is_master=False):
        """The inner purge method.

        Purges the binary logs from the given server, it will purge all of the
        binlogs older than the active_binlog_file ot to target_binlog_index.

        index_last_in_use[in]    The index of the latest binary log not in
                                 use. in case of a Master, must be the latest
                                 binlog caought by all the slaves.
        active_binlog_file[in]   Current active binlog file.
        binlog_file_name[in]     Binlog base file name.
        target_binlog_index[in]  The target binlog index, in case doesn't want
                                 to use the index_last_in_use by default None.
        server[in]               Server object where to purge the binlogs from,
                                 by default self.server is used.
        server_is_master[in]     Indicates if the given server is a Master,
                                 used for report purposes by default False.
        """
        if server is None:
            server = self.server
        if server_is_master:
            server_name = "master"
        else:
            server_name = "server"

        # The purge_to_binlog file used to purge query based on earliest log
        # not in use
        z_len = len(active_binlog_file.split('.')[1])
        purge_to_binlog = (
            "{0}.{1}".format(binlog_file_name,
                             repr(index_last_in_use).zfill(z_len))
        )

        server_binlogs_list = server.get_server_binlogs_list()
        if self.verbosity >= 1:
            _report_binlogs(server_binlogs_list, self._report)

        # The last_binlog_not_in_use used for information purposes
        index_last_not_in_use = index_last_in_use - 1
        last_binlog_not_in_use = (
            "{0}.{1}".format(binlog_file_name,
                             repr(index_last_not_in_use).zfill(z_len))
        )

        if server_is_master:
            self._report("# Latest binlog file replicated by all slaves: "
                         "{0}".format(last_binlog_not_in_use))

        if target_binlog_index is None:
            # Purge to latest binlog not in use
            if self.verbosity > 0:
                self._report("# Latest not active binlog"
                             " file: {0}".format(last_binlog_not_in_use))

            # last_binlog_not_in_use
            purge(server, purge_to_binlog, server_binlogs_list,
                  reporter=self._report, dryrun=self.dry_run,
                  verbosity=self.verbosity)
        else:
            purge_to_binlog = (
                "{0}.{1}".format(binlog_file_name,
                                 repr(target_binlog_index).zfill(z_len))
            )
            if purge_to_binlog not in server_binlogs_list:
                self._report(
                    _COULD_NOT_FIND_BINLOG.format(bin_name=self.to_binlog_name,
                                                  server_name=server_name,
                                                  host=server.host,
                                                  port=server.port))
                return

            if target_binlog_index > index_last_in_use:
                self._report("WARNING: The given binlog name: '{0}' is "
                             "required for one or more slaves, the Utilitiy "
                             "will purge to binlog '{1}' instead."
                             "".format(self.to_binlog_name,
                                       last_binlog_not_in_use))
                target_binlog_index = last_binlog_not_in_use

            # last_binlog_not_in_use
            purge(server, purge_to_binlog, server_binlogs_list,
                  reporter=self._report, dryrun=self.dry_run,
                  verbosity=self.verbosity)

        server_binlogs_list_after = server.get_server_binlogs_list()
        if self.verbosity >= 1:
            _report_binlogs(server_binlogs_list_after, self._report)
        for binlog in server_binlogs_list_after:
            if binlog in server_binlogs_list:
                server_binlogs_list.remove(binlog)
        if self.verbosity >= 1 and server_binlogs_list:
            _report_binlogs(server_binlogs_list, self._report, removed=True)

    def purge(self):
        """The purge method for a standalone server.

        Determines the latest log file to purge, which becomes the target
        file to purge binary logs to in case no other file is specified.
        """
        # Connect to server
        self.server = Server({'conn_info': self.server_cnx_val})
        self.server.connect()

        # Check required privileges
        check_privileges(self.server, BINLOG_OP_PURGE,
                         ["SUPER", "REPLICATION SLAVE"],
                         BINLOG_OP_PURGE_DESC, self.verbosity, self._report)

        # retrieve active binlog info
        binlog_file_name, active_binlog_file, index_last_in_use = (
            get_binlog_info(self.server, reporter=self._report,
                            server_name="server", verbosity=self.verbosity)
        )

        # Verify this server is not a Master.
        processes = self.server.exec_query("SHOW PROCESSLIST")
        binlog_dump = False
        for process in processes:
            if process[4] == "Binlog Dump":
                binlog_dump = True
                break
        hosts = self.server.exec_query("SHOW SLAVE HOSTS")
        if binlog_dump or hosts:
            if hosts and not self.verbosity:
                msg_v = " For more info use verbose option."
            else:
                msg_v = ""
            if self.verbosity >= 1:
                for host in hosts:
                    self._report("# WARNING: Slave with id:{0} at {1}:{2} "
                                 "is connected to this server."
                                 "".format(host[0], host[1], host[2]))
            raise UtilError("The given server is acting as a master and has "
                            "slaves connected to it. To proceed please use the"
                            " --master option.{0}".format(msg_v))

        target_binlog_index = self.get_target_binlog_index(binlog_file_name)

        self._purge(index_last_in_use, active_binlog_file, binlog_file_name,
                    target_binlog_index)


class RPLBinaryLogPurge(BinaryLogPurge):
    """RPLBinaryLogPurge class
    """

    def __init__(self, master_cnx_val, slaves_cnx_val, options):
        """Initiator.

        master_cnx_val[in]    Master server connection dictionary.
        slaves_cnx_val[in]    Slave server connection dictionary.
        options[in]           Options dictionary.
        """
        super(RPLBinaryLogPurge, self).__init__(None, options)

        self.master_cnx_val = master_cnx_val
        self.slaves_cnx_val = slaves_cnx_val

        self.topology = None
        self.master = None
        self.slaves = None

    def purge(self):
        """The Purge Method

        Determines the latest log file to purge among all the slaves, which
        becomes the target file to purge binary logs to, in case no other
        file is specified.
        """
        # Create a topology object to verify the connection between master and
        # slaves servers.
        self.topology = Topology(self.master_cnx_val, self.slaves_cnx_val,
                                 self.options, skip_conn_err=False)

        self.master = self.topology.master
        self.slaves = self.topology.slaves

        # Check required privileges
        check_privileges(self.master, BINLOG_OP_PURGE,
                         ["SUPER", "REPLICATION SLAVE"],
                         BINLOG_OP_PURGE_DESC, self.verbosity, self._report)

        # Get binlog info
        binlog_file_name, active_binlog_file, active_binlog_index = (
            get_binlog_info(self.master, reporter=self._report,
                            server_name="master", verbosity=self.verbosity)
        )

        # Verify this Master has at least one slave.
        if not self.slaves:
            errormsg = (
                _CAN_NOT_VERIFY_SLAVES_STATUS.format(host=self.master.host,
                                                     port=self.master.port))
            raise UtilError(errormsg)

        # verify the given slaves are connected to this Master.
        if self.slaves_cnx_val and self.slaves:
            for slave in self.slaves:
                slave['instance'].is_configured_for_master(self.master,
                                                           verify_state=False,
                                                           raise_error=True)

                # IO running verification for --slaves option
                if not slave['instance'].is_connected():
                    if self.verbosity:
                        self._report("# Slave '{0}:{1}' IO not running"
                                     "".format(slave['host'], slave['port']))
                    raise UtilError(
                        _CAN_NOT_VERIFY_SLAVE_STATUS.format(host=slave['host'],
                                                            port=slave['port'])
                    )

        target_binlog_index = self.get_target_binlog_index(binlog_file_name)

        index_last_in_use = determine_purgeable_binlogs(
            active_binlog_index,
            self.slaves,
            reporter=self._report,
            verbosity=self.verbosity
        )

        self._purge(index_last_in_use, active_binlog_file, binlog_file_name,
                    target_binlog_index, server=self.master,
                    server_is_master=True)


def binlog_rotate(server_val, options):
    """Rotate binary log.

    This function creates a BinaryLogRotate task.

    server_cnx_val[in] Dictionary with the connection values for the server.
    options[in]        options for controlling behavior:
        logging        If logging is active or not.
        verbose        print extra data during operations (optional)
                       default value = False
        min_size       minimum size that the active binlog must have prior
                       to rotate it.
        dry_run        Don't actually rotate the active binlog, instead
                       it will print information about file name and size.
    """
    binlog_rotate = BinaryLogRotate(server_val, options)
    binlog_rotate.rotate()


class BinaryLogRotate(object):
    """The BinaryLogRotate Class, it represents a binary log rotation task.
    The rotate method performs the following tasks:
        - Retrieves the active binary log and file size.
        - If the minimum size is given, evaluate active binlog file size, and
          if this is greater than the minimum size rotation will occur.
          rotation occurs.
    """

    def __init__(self, server_cnx_val, options):
        """Initiator.

        server_cnx_val[in] Dictionary with the connection values for the
                           server.
        options[in]        options for controlling behavior:
            logging        If logging is active or not.
            verbose        print extra data during operations (optional)
                           default value = False
            min_size       minimum size that the active binlog must have prior
                           to rotate it.
            dry_run        Don't actually rotate the active binlog, instead
                           it will print information about file name and size.
        """

        # Connect to server
        self.server = Server({'conn_info': server_cnx_val})
        self.server.connect()
        self.options = options
        self.verbosity = self.options.get("verbosity", 0)
        self.quiet = self.options.get("quiet", False)
        self.logging = self.options.get("logging", False)
        self.dry_run = self.options.get("dry_run", 0)
        self.binlog_min_size = self.options.get("min_size", False)

    def _report(self, message, level=logging.INFO, print_msg=True):
        """Log message if logging is on.

        This method will log the message presented if the log is turned on.
        Specifically, if options['log_file'] is not None. It will also
        print the message to stdout.

        message[in]      Message to be printed.
        level[in]        Level of message to log. Default = INFO.
        print_msg[in]    If True, print the message to stdout. Default = True.
        """
        # First, print the message.
        if print_msg and not self.quiet:
            print(message)
        # Now log message if logging turned on
        if self.logging:
            msg = message.strip("#").strip(" ")
            logging.log(int(level), msg)

    def rotate(self):
        """This Method runs the rotation.

        This method will use the methods from the common library to rotate the
        binary log.
        """

        # Check required privileges
        check_privileges(self.server, BINLOG_OP_ROTATE,
                         ["RELOAD", "REPLICATION CLIENT"],
                         BINLOG_OP_ROTATE_DESC, self.verbosity, self._report)

        active_binlog, binlog_size = get_active_binlog_and_size(self.server)
        if self.verbosity:
            self._report("# Active binlog file: '{0}' (size: {1} bytes)'"
                         "".format(active_binlog, binlog_size))

        if self.binlog_min_size:
            rotated = rotate(self.server, self.binlog_min_size,
                             reporter=self._report)
        else:
            rotated = rotate(self.server, reporter=self._report)

        if rotated:
            new_active_binlog, _ = get_active_binlog_and_size(self.server)
            if active_binlog == new_active_binlog:
                raise UtilError("Unable to rotate binlog file.")
            else:
                self._report("# The binlog file has been rotated.")
                if self.verbosity:
                    self._report("# New active binlog file: '{0}'"
                                 "".format(new_active_binlog))
