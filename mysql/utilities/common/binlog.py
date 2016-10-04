#
# Copyright (c) 2014, 2016 Oracle and/or its affiliates. All rights
# reserved.
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
This file contains the binary log administrative operations purge and rotate
operations.
"""

import os

from mysql.utilities.exception import UtilDBError, UtilError


def get_binlog_info(server, reporter=None, server_name="server", verbosity=0):
    """Get binlog information from the server.

    This method queries the server for binary log information as the binlog
    base name, binlog file name and the active binlog file index.
    Note: An error is raised in case the binlog information can not be retried.

    server[in]       Source instance server to obtain information from.
    reporter[in]     Method to invoke to report messages.
    server_name[in]  Name of server to use when reporting. Default "server".
    verbosity[in]    Level of verbosity for report purposes.

    Returns a tuple with the active binlog base name, file name and index.
    """

    res = server.show_server_variable('log_bin_basename')
    binlog_b_name = None
    if res and res[0][1]:
        binlog_basename_path = res[0][1]
        if reporter is not None and verbosity >= 3:
            reporter("# Binary log basename path: {0}"
                     "".format(binlog_basename_path))
        binlog_b_name = os.path.basename(binlog_basename_path)
        if reporter is not None and verbosity >= 3:
            reporter("# Binary log basename: {0}"
                     "".format(binlog_b_name))

    res = server.exec_query("SHOW MASTER STATUS")

    if not res:
        raise UtilError("Unable to get binlog information from {0} at {1}:{2}"
                        "".format(server_name, server.host, server.port))
    else:
        master_active_binlog_file = res[0][0]

        master_active_binlog_index = int(res[0][0].split('.')[1])

        if binlog_b_name is None:
            binlog_b_name = res[0][0].split('.')[0]
            if reporter is not None and verbosity >= 3:
                reporter("# Binary log basename: {0}"
                         "".format(binlog_b_name))

        if reporter is not None and verbosity > 0:
            reporter("# {server_name} active binlog file: {act_log}"
                     "".format(server_name=server_name.capitalize(),
                               act_log=master_active_binlog_file))

    return (binlog_b_name, master_active_binlog_file,
            master_active_binlog_index)


def determine_purgeable_binlogs(active_binlog_index, slaves, reporter,
                                verbosity=0):
    """Determine the purgeable binary logs.

    This method will look at each slave given and will determinate the lowest
    binary log file that is being in use.

    active_binlog_index[in]    Index of binlog currently in use by the
                               master server or the higher binlog index value
                               it wants to be purged.
    slaves[in]                 Slaves list.
    reporter[in]               Method to call to report.
    verbosity[in]              The verbosity level for reporting information.

    Returns the last index in use by the slaves, that is the newest binlog
    index that has between read by all the slave servers.
    """
    # Determine old no needed binlogs
    master_log_file_in_use = []
    index_last_in_use = active_binlog_index
    # pylint: disable=R0101
    if slaves:
        for slave in slaves:
            if reporter is not None and verbosity >= 1:
                reporter("# Checking slave: {0}@{1}"
                         "".format(slave['host'], slave['port']))

            res = slave['instance'].get_status()

            if res:
                master_log_file = res[0][5]

                if reporter is not None and verbosity >= 1:
                    reporter("# I/O thread is currently reading: {0}"
                             "".format(master_log_file))
                master_log_file_in_use.append(master_log_file)
                reading_index_file = int(master_log_file.split('.')[1])

                if index_last_in_use > reading_index_file:
                    index_last_in_use = reading_index_file

                if reporter is not None and verbosity >= 2:
                    reporter("# File position of the I/O thread: {0}"
                             "".format(res[0][6]))
                    reporter("# Master binlog file with last event executed "
                             "by the SQL thread: {0}".format(res[0][9]))
                    reporter("# I/O thread running: {0}".format(res[0][10]))
                    reporter("# SQL thread running: {0}".format(res[0][11]))
                    if len(res[0]) > 52:
                        if res[0][51]:
                            reporter("# Retrieved GTid_Set: {0}"
                                     "".format(res[0][51]))
                        if res[0][52]:
                            reporter("# Executed GTid_Set: {0}"
                                     "".format(res[0][52]))
        return index_last_in_use
    else:
        raise UtilError("None Slave is connected to master")


def purge(server, purge_to_binlog, server_binlogs_list=None,
          reporter=None, dryrun=False, verbosity=0):
    """Purge the binary log for the given server.

    This method purges all the binary logs from the given server that are older
    than the given binlog file name specified by purge_to_binlog. The method
    can receive a list of the binary logs listed on the server to avoid
    querying the server again for this list. If The given purge_to_binlog is
    not listed on the server_binlogs_list the purge will not occur. For
    reporting capabilities if given the method report will be invoked to
    report messages and the server name that appears on the messages can be
    change with server_name.

    server[in]                server instance where to purge binlogs on
    purge_to_binlog[in]       purge binlog files older than this binlog file
                              name.
    server_binlogs_list[in]   A list of binlog files available on the given
                              server, if not given, the list will be retrieved
                              from the given server (default None).
    server_name[in]           This name will appear when reporting (default
                              'Server').
    reporter[in]              A method to invoke with messages and warnings
                              (default None).
    dryrun[in]                boolean value that indicates if the purge query
                              should be run on the server or reported only
                              (default False).
    verbosity[in]             The verbosity level for report messages.
    """
    if server_binlogs_list is None:
        server_binlogs_list = server.get_server_binlogs_list()

    # The PURGE BINARY LOGS statement deletes all the binary log files listed
    # in the log index file, prior to the specified log file name.
    # Verify purge_to_binlog is listed on server binlog list and if not is the
    # first in the list continue the purge, else there is no binlogs to purge
    if (purge_to_binlog in server_binlogs_list and
            purge_to_binlog != server_binlogs_list[0]):
        purge_query = (
            "PURGE BINARY LOGS TO '{0}'"
        ).format(purge_to_binlog)
        if dryrun:
            reporter("# To manually purge purge the binary logs Execute the "
                     "following query:")
            reporter(purge_query)
        else:
            if verbosity > 1:
                reporter("# Executing query {0}".format(purge_query))
            else:
                reporter("# Purging binary logs prior to '{0}'"
                         "".format(purge_to_binlog))
            try:
                server.exec_query(purge_query)
            except UtilDBError as err:
                raise UtilError("Unable to purge binary log, reason: {0}"
                                "".format(err.errmsg))

    else:
        reporter("# No binlog files can be purged.")


def get_active_binlog_and_size(server):
    """Retrieves the current active binlog file name and his size

    server[in]    server instance to query for the required info.

    Returns a tuple with two values, active binlog file name and his size
    """
    binlogs_list = server.get_server_binlogs_list(include_size=True)
    if binlogs_list:
        active_binlog_and_size = binlogs_list[-1]
        active_binlog = active_binlog_and_size[0]
        binlog_size = int(active_binlog_and_size[1])
        return active_binlog, binlog_size
    return None, None


def rotate(server, min_size=-1, reporter=None):
    """Rotates the binary log on the given server.

    This method rotates the active binary log from the given server, if
    min_size is given the size of the active binlog will be compared with this
    value, and rotation will only occur if the binlog size is greater than the
    given value. This method will execute the FLUSH BINARY LOGS on MySQL
    servers version 5.5.3 and greater and in older ones the FLUSH LOGS command
    to rotate the active binary log.

    server[in]      The source server instance where log rotation will occur
    min_size[in]    An integer value representing the minimum file size that
                    the active binlog must reach before rotate it. (default -1)
    reporter[in]    A method to invoke with messages and warnings.

    Returns True if the rotation command has been executed on the given server.
    """
    # Retrieve current active binlog and his file size.
    active_binlog, binlog_size = get_active_binlog_and_size(server)

    # Compare the active binlog size with the min_size
    # if the active binlog file size is greater than the min_size totate it
    # else show a Warning.
    if binlog_size >= min_size:
        if server.check_version_compat(5, 5, 3):
            type_log = "BINARY"
        else:
            type_log = ""
        server.exec_query("FLUSH {type_log} LOGS".format(type_log=type_log))
        return True
    else:
        if reporter:
            reporter("WARNING: The active binlog file '{0}' was not rotated "
                     "because it's size {1} is lower than the minimum "
                     "specified size: {2}".format(active_binlog, binlog_size,
                                                  min_size))
        return False
