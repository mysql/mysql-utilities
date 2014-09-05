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
This file contains common features to manage and handle binary log files.
"""
import io
import errno
import os
import shutil
import time

from datetime import datetime

from mysql.utilities.exception import UtilError

LOG_TYPES = ['bin', 'relay', 'all']
LOG_TYPE_BIN = LOG_TYPES[0]
LOG_TYPE_RELAY = LOG_TYPES[1]
LOG_TYPE_ALL = LOG_TYPES[2]

_DAY_IN_SECONDS = 86400


def is_binary_log_filename(filename, log_type=LOG_TYPE_ALL, basename=None):
    """Check if the filename matches the name format for binary log files.

    This function checks if the given filename corresponds to the filename
    format of known binary log files, according to the specified log_type and
    optional basename. The file extension is a sequence number (.nnnnnn). If
    a basename is given then the filename for the binary log file must have
    the format 'basename.nnnnnn'. Otherwise the default filename is assumed,
    depending on the log_type: '*-bin.nnnnnn' for the 'bin' log type,
    '*-relay-bin.nnnnnn' for the 'relay' log type, and both for the 'all' type.

    filename[in]    Filename to check.
    log_type[in]    Type of the binary log, must be one of the following
                    values: 'bin' for binlog files, 'relay' for relay log
                    files, 'all' for both binary log files. By default = 'all'.
    basename[in]    Basename defined for the binary log file. None by default,
                    meaning that the default server name formats are assumed
                    (according to the given log type).
    """
    # Split file basename and extension.
    f_base, f_ext = os.path.splitext(filename)
    f_ext = f_ext[1:]  # remove starting dot '.'

    # Check file basename.
    if basename:
        if f_base != basename:
            # Defined basename does not match.
            return False
    else:
        # Check default serve basename for the given log_type.
        if log_type == LOG_TYPE_BIN:
            # *-bin.nnnnnn (excluding *-relay-bin.nnnnnn)
            if not f_base.endswith('-bin') or f_base.endswith('-relay-bin'):
                return False
        elif log_type == LOG_TYPE_RELAY:
            # *-relay-bin.nnnnnn
            if not f_base.endswith('-relay-bin'):
                return False
        elif log_type == LOG_TYPE_ALL:
            # *-bin.nnnnnn (including *-relay-bin.nnnnnn)
            if not f_base.endswith('-bin'):
                return False
        else:
            raise UtilError("Unsupported log-type: {0}".format(log_type))

    # Check file extension.
    try:
        int(f_ext)
    except ValueError:
        # Extension is not a sequence number (error converting to integer).
        return False

    # Return true if basename and extension checks passed.
    return True


def get_index_file(source, binary_log_file):
    """ Find the binary log index file.

    Search the index file in the specified source directory for the given
    binary log file and retrieve its location (i.e., full path).

    source[in]              Source directory to search for the index file.
    binary_log_file[in]     Binary log file associated to the index file.

    Return the location (full path) of the binary log index file.
    """
    f_base, _ = os.path.splitext(binary_log_file)
    index_filename = '{0}.index'.format(f_base)
    index_file = os.path.join(source, index_filename)
    if os.path.isfile(index_file):
        return index_file
    else:
        raise UtilError("Unable to find the index file associated to file "
                        "'{0}'.".format(binary_log_file))


def filter_binary_logs_by_sequence(filenames, seq_list):
    """Filter filenames according to the given sequence number list.

    This function filters the given list of filenames according to the given
    sequence number list, excluding the filenames that do not match.

    Note: It is assumed that given filenames are valid binary log files.
    Use is_binary_log_filename() to check each filenames.

    filenames[in]   List of binary log filenames to check.
    seq_list[in]    List of allowed sequence numbers or intervals.
                    For example: 3,5-12,16,21.

    Returns a list of the filenames matching the given sequence number filter.
    """
    res_list = []
    for filename in filenames:
        # Split file basename and extension.
        _, f_ext = os.path.splitext(filename)
        f_ext = int(f_ext[1:])  # remove starting dot '.' and convert to int
        for seq_value in seq_list:
            # Check if the sequence value is an interval (tuple) or int.
            if isinstance(seq_value, tuple):
                # It is an interval; Check if it contains the file sequence
                # number.
                if seq_value[0] <= f_ext <= seq_value[1]:
                    res_list.append(filename)
                    break
            else:
                # Directly check if the sequence numbers match (are equal).
                if f_ext == seq_value:
                    res_list.append(filename)
                    break

    # Retrieve the resulting filename list (filtered by sequence number).
    return res_list


def filter_binary_logs_by_date(filenames, source, max_date):
    """Filter filenames according their last modification date.

    This function filters the given list of files according to their last
    modification date, excluding those with the last change before the given
    max_date.

    Note: It is assumed that given filenames are valid binary log files.
    Use is_binary_log_filename() to check each filename.

    filenames[in]   List of binary log filenames to check.
    source[in]      Source directory where the files are located.
    max_date[in]    Maximum modification date, in the format 'yyyy-mm-dd' or
                    'yyyy-mm-ddThh:mm:ss', or number of days since the last
                    modification.

    Returns a list of the filenames not changed within the given elapsed days
    (i.e., recently changed files will be excluded).
    """
    res_list = []
    # Compute maximum modified date/time, according to supported formats.
    try:
        elapsed_days = int(max_date)
    except ValueError:
        # Max date is not a valid integer (i.e., number of days).
        elapsed_days = None
    if elapsed_days:  # Process the specified number fo days
        if elapsed_days < 1:
            raise UtilError(
                "Invalid number of days (must be an integer greater than "
                "zero): {0}".format(max_date)
            )
        # Get current local time.
        ct_tuple = time.localtime()
        # Set time to 00:00:00.
        ct_list = list(ct_tuple)
        ct_list[3] = 0  # hours
        ct_list[4] = 0  # minutes
        ct_list[5] = 0  # seconds
        ct_tuple_0000 = tuple(ct_list)
        # Get seconds since epoch for the current day at 00:00.
        day_start_time = time.mktime(ct_tuple_0000)
        # Compute max modified date based on elapsed days ignoring time, i.e.,
        # 00:00 is used as reference to count days. Current day count as one.
        max_time = day_start_time - (_DAY_IN_SECONDS * (elapsed_days - 1))
        max_date = time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(max_time))
    else:  # Process the specified date
        # Check the date format.
        _, _, time_val = max_date.partition('T')
        if time_val:
            try:
                dt_max_date = datetime.strptime(max_date, '%Y-%m-%dT%H:%M:%S')
            except ValueError:
                raise UtilError(
                    "Invalid date/time format (yyyy-mm-ddThh:mm:ss): "
                    "{0}".format(max_date)
                )
        else:
            try:
                dt_max_date = datetime.strptime(max_date, '%Y-%m-%d')
            except ValueError:
                raise UtilError(
                    "Invalid date format (yyyy-mm-dd): {0}".format(max_date)
                )
        max_date = dt_max_date.strftime('%Y-%m-%dT%H:%M:%S')

    # Check modified date for each file.
    for filename in filenames:
        source_file = os.path.join(source, filename)
        modified_time = os.path.getmtime(source_file)
        modified_date = time.strftime('%Y-%m-%dT%H:%M:%S',
                                      time.localtime(modified_time))
        if modified_date < max_date:
            res_list.append(filename)

    # Retrieve the resulting filename list (filtered by modified date).
    return res_list


def move_binary_log(source, destination, filename, log_index,
                    undo_on_error=True):
    """Move a binary log file to a specific destination.

    This method move the given binary log file (filename), located in the
    source directory, to the specified destination directory and updates the
    respective index file accordingly.

    Note: An error is raised if any issue occurs during the process.
    Additionally, if the undo_on_error=True (default) then the file is moved
    back to the source directory if an error occurred while updating the index
    file (keeping the file in the original location and the index file
    unchanged). Otherwise the file might be moved and the index file not
    correctly updated. In either cases an error is issued.

    source[in]          Source directory where the binary log file is located.
    destination[in]     Destination directory to move the binary log.
    filename[in]        Name of the binary log file to move.
    log_index[in]       Location (full path) of the binary log index file.
    undo_on_error[in]   Flag to undo the file move if an error occurs (when
                        updating the index file) or not. By default = True,
                        meaning that the move operation is reverted ().
    """
    def _move_file_back():
        """Try to move the file back to its original source directory.
        Returns a warning message indicating if the file was moved back
        successfully or not.
        """
        try:
            # Move file back to source directory.
            destination_file = os.path.join(destination, filename)
            shutil.move(destination_file, source)
        except (IOError, shutil.Error) as move_err:
            # Warn the user that an error occurred while trying to
            # move the file back.
            return ("\nWARNING: Failed to move file back to source directory: "
                    "{0}").format(move_err)
        else:
            # Notify user that the file was successfully moved back.
            return "\nWARNING: File move aborted."

    # Move file to destination directory.
    source_file = os.path.join(source, filename)
    if os.path.isdir(destination):
        shutil.move(source_file, destination)
    else:
        # Raise an error if the destination dir does not exist.
        # Note: To be consistent with the IOError raised by shutil.move() if
        # the source file does not exist.
        raise IOError(errno.ENOENT, "No such destination directory",
                      destination)

    # Update index file.
    found_pos = None
    try:
        with io.open(log_index, 'r') as index_file:
            # Read all data from index file.
            data = index_file.readlines()
            # Search for the binary log file entry.
            for pos, line in enumerate(data):
                if line.strip().endswith(filename):
                    found_pos = pos
                    break
            if found_pos is not None:
                # Replace binary file entry with absolute destination path.
                data[found_pos] = u'{0}\n'.format(
                    os.path.join(destination, filename)
                )
            else:
                warning = ""  # No warning if undo_on_error = False.
                if undo_on_error:
                    warning = _move_file_back()
                # Raise error (including cause).
                raise UtilError("Entry for file '{0}' not found in index "
                                "file: {1}{2}".format(filename, log_index,
                                                      warning))
            # Create a new temporary index_file with the update entry.
            # Note: original file is safe is something goes wrong during write.
            tmp_file = '{0}.tmp'.format(log_index)
            try:
                with io.open(tmp_file, 'w', newline='\n') as tmp_index_file:
                    tmp_index_file.writelines(data)
            except IOError as err:
                warning = ""  # No warning if undo_on_error = False.
                if undo_on_error:
                    warning = _move_file_back()
                # Raise error (including cause).
                raise UtilError('Unable to write temporary index file: '
                                '{0}{1}'.format(err, warning))
    except IOError as err:
        warning = ""  # No warning if undo_on_error = False.
        if undo_on_error:
            warning = _move_file_back()
        # Raise error (including cause).
        raise UtilError('Failed to update index file: '
                        '{0}{1}'.format(err, warning))
    # Replace the original index file with the new one.
    if os.name == 'posix':
        os.rename(tmp_file, log_index)
    else:
        # On windows, rename does not work if the target file already exists.
        shutil.move(tmp_file, log_index)
