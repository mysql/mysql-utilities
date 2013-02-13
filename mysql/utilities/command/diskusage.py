#
# Copyright (c) 2011, Oracle and/or its affiliates. All rights reserved.
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
This file contains the reporting mechanisms for reporting disk usage.
"""

import locale
import os
import sys

from mysql.utilities.exception import UtilError

# Constants
_KB = (1024)
_MB = (1024*_KB)
_GB = (1024*_MB)
_TB = (1024*_GB)

_QUERY_DATAFREE = """
    SELECT DISTINCT data_free
    FROM INFORMATION_SCHEMA.TABLES
    WHERE UPPER(engine) = 'INNODB'
"""

_QUERY_DBSIZE = """
    SELECT table_schema AS db_name, SUM(data_length + index_length) AS size
    FROM INFORMATION_SCHEMA.TABLES %s
    GROUP BY db_name
"""

def _print_size(prefix, total):
    """Print size formatted with commas and estimated to the largest XB.

    prefix[in]        The preamble to the size. e.g. "Total XXX ="
    total[in]         Integer value to format.
    """

    # Calculate largest XByte...
    if total > _TB:
        converted = total/_TB
        print prefix + "%s bytes or {0:.2f} TB".format(converted) % \
              locale.format("%d", total, grouping=True)
    elif total > _GB:
        converted = total/_GB
        print prefix + "%s bytes or {0:.2f} GB".format(converted) % \
              locale.format("%d", total, grouping=True)
    elif total > _MB:
        converted = total/_MB
        print prefix + "%s bytes or {0:.2f} MB".format(converted) % \
              locale.format("%d", total, grouping=True)
    elif total > _KB:
        converted = total/_KB
        print prefix + "%s bytes or {0:.2f} KB".format(converted) % \
              locale.format("%d", total, grouping=True)
    else:
        print prefix + "%s bytes" % locale.format("%d", total, grouping=True)


def _get_formatted_max_width(rows, columns, col):
    """Return the max width for a numeric column.

    list[in]          The list to search
    col[in]           Column number to search

    return (int) maximum width of character representation
    """
    width = 0
    if rows is None or rows == [] or col >= len(rows[0]):
        return width

    for row in rows:
        size = len(locale.format("%d", row[col], grouping=True))
        col_size = len(columns[col])
        if size > width:
            width = size
        if col_size > width:
            width = col_size
    return int(width)


def _get_folder_size(folder):
    """Get size of folder (directory) and all its contents

    folder[in]        Folder to calculate

    return (int) size of folder or 0 if empty or None if not exists or error
    """

    try:
        total_size = os.path.getsize(folder)
    except:
        return None
    for item in os.listdir(folder):
        itempath = os.path.join(folder, item)
        if os.path.isfile(itempath):
            total_size += os.path.getsize(itempath)
        elif os.path.isdir(itempath):
            total_size += _get_folder_size(itempath)
    return total_size


def _get_db_dir_size(folder):
    """Calculate total disk space used for a given directory.

    This method will sum all files in the directory except for the
    MyISAM files (.myd, .myi).

    folder[in]        The folder to sum

    returns (int) sum of files in directory or None if not exists
    """
    try:
        total_size = os.path.getsize(folder)
    except:
        return None
    for item in os.listdir(folder):
        name, ext = os.path.splitext(item)
        if ext.upper() not in (".MYD", ".MYI") and \
           name.upper() not in ('SLOW_LOG', 'GENERAL_LOG'):
            itemfolder = os.path.join(folder, item)
            if os.path.isfile(itemfolder):
                total_size += os.path.getsize(itemfolder)
            elif os.path.isdir(itemfolder):
                total_size += _get_db_dir_size(itemfolder)
    return total_size


def _find_tablespace_files(folder, verbosity=0):
    """Find all tablespace files located in the datadir.

    folder[in]        The folder to search

    return (tuple) (tablespaces[], total_size)
    """
    total = 0
    tablespaces = []
    # skip inaccessible files.
    try:
        for item in os.listdir(folder):
            itempath = os.path.join(folder, item)
            name, ext = os.path.splitext(item)
            if os.path.isfile(itempath):
                name, ext = os.path.splitext(item)
                if ext.upper() == "IBD":
                    size = os.path.getsize(itempath)
                    total += size
                    if verbosity > 0:
                        row = (item, size,'file tablespace', '')
                    else:
                        row = (item, size)
    
                    tablespaces.append(row)
            else:
                subdir, tot = _find_tablespace_files(itempath, verbosity)
                if subdir is not None:
                    total += tot
                    tablespaces.extend(subdir)
    except:
        return (None, None)

    return tablespaces, total


def _build_logfile_list(server, log_name, suffix='_file'):
    """Build a list of all log files based on the system variable by the
    same name as log_name.

    server[in]        Connected server
    log_name[in]      Name of log (e.g. slow_query_log)
    suffix[in]        Suffix of log variable name (e.g. slow_query_log_file)
                      default = '_file'

    return (tuple) (logfiles[], path to log files, total size)
    """
    log_path = None
    res = server.show_server_variable(log_name)
    if res != [] and res[0][1].upper() == 'OFF':
        print "# The %s is turned off on the server." % log_name
    else:
        res = server.show_server_variable(log_name+suffix)
        if res == []:
            raise UtilError("Cannot get %s_file setting." % log_name)
        log_path = res[0][1]

        if os.access(log_path, os.R_OK):
            parts = os.path.split(log_path)
            if len(parts) <= 1:
                log_file = log_path
            else:
                log_file = parts[1]
            log_path_size = os.path.getsize(log_path)
            return (log_file, log_path, int(log_path_size))
    return None, 0, 0


def _get_log_information(server, log_name, suffix='_file'):
    """Get information about a specific log.

    This method checks the system variable of the log_name passed to see if
    it is turned on. If turned on, the method returns a list of the log files
    and the total of the log files.

    server[in]        Connected server
    log_name[in]      Variable name for the log (e.g. slow_query_log)
    suffix[in]        Suffix of log variable name (e.g. slow_query_log_file)
                      default = '_file'

    returns (tuple) (log files, total size)
    """
    res = server.show_server_variable(log_name)
    if res != [] and res[0][1].upper() == 'OFF':
        print "# The %s is turned off on the server." % log_name
    else:
        log_file, log_path, log_size = _build_logfile_list(server, log_name,
                                                       suffix)
        if log_file is None or log_path is None or \
           not os.access(log_path, os.R_OK):
            print "# %s information is not accessible. " % log_name + \
                  "Check your permissions."
            return None, 0
        return log_file, log_size
    return None, 0


def _build_log_list(folder, prefix):
    """Build a list of all binary log files based on the prefix for the name.

    Return total size of all files found.

    folder[in]        Folder to search
    prefix[in]        Prefix of log name (e.g. mysql-bin)

    return (tuple) (binlogfiles[], total size)
    """
    total_size = 0
    binlogs = []
    if prefix is not None:
        for item in os.listdir(folder):
            name, ext = os.path.splitext(item)
            if name.upper() == prefix.upper():
                itempath = os.path.join(folder, item)
                if os.path.isfile(itempath):
                    size = os.path.getsize(itempath)
                    binlogs.append((item, size))
                    total_size += os.path.getsize(itempath)
    binlogs.sort()
    return binlogs, total_size


def _build_innodb_list(per_table, folder, datadir, specs, verbosity=0):
    """Build a list of all InnoDB files.

    This method builds a list of all InnoDB tablespace files and related
    files. It will search all database directories if per_table is True.
    Returns total size of all files found.

    The verbosity option controls how much data is shown:
          0 : no additional information
        > 0 : include type and specification (for shared tablespaces)

    per_table[in]     If True, look for individual tablespaces
    folder[in]        Folder to search
    datadir[in]       Data directory
    specs[in]         List of specifications
    verbosity[in]     Determines how much information to display

    return (tuple) (tablespacefiles[], total size)
    """
    total_size = 0
    tablespaces = []
    # Here, we want to capture log files as well as tablespace files.
    if specs is not None:
        for item in os.listdir(folder):
            name, ext = os.path.splitext(item)
            # Check specification list
            for spec in specs:
                parts = spec.split(":")
                if len(parts) < 1:
                    break
                if name.upper() == parts[0].upper():
                    itempath = os.path.join(folder, item)
                    if os.path.isfile(itempath):
                        size = os.path.getsize(itempath)
                        if verbosity > 0:
                            row = (item, size, 'shared tablespace', spec)
                        else:
                            row = (item, size)
                        tablespaces.append(row)
                        total_size += os.path.getsize(itempath)
                elif name[0:6].upper() == "IB_LOG":
                    itempath = os.path.join(folder, item)
                    if os.path.isfile(itempath):
                        size = os.path.getsize(itempath)
                        if verbosity > 0:
                            row = (item, size, 'log file', '')
                        else:
                            row = (item, size)
                        if row not in tablespaces:
                            tablespaces.append(row)
                        total_size += os.path.getsize(itempath)

    # Check to see if innodb_file_per_table is ON
    if per_table:
        tablespace_files, total = _find_tablespace_files(datadir, verbosity)
        tablespaces.extend(tablespace_files)
        total_size += total

    tablespaces.sort()
    return tablespaces, total_size


def _build_db_list(server, rows, include_list, datadir, format=False,
                   have_read=False, verbosity=0, include_empty=True):
    """Build a list of all databases and their totals.

    This method reads a list of databases and their calculated sizes
    and builds a new list of the databases searching the datadir provided
    and adds the size of the miscellaneous files.

    The size of the database is calculated based on the ability of the user
    to read the datadir. If user has read access to the datadir, the total
    returned will be the calculation of the data_length+index_length from
    INFORMATION_SCHEMA.TABLES plus the sum of all miscellaneous files (e.g.
    trigger files, .frm files, etc.). If the user does not have read access
    to the datadir, only the calculated size is returned.

    If format is True, the columns and rows returned will be formatted to a
    constant width using locale-specific options for printing numerals. For
    example, US locale formats 12345 as 12,345.

    The verbosity option controls how much data is shown:
           0 : no additional information
         > 0 : include data size (calculated) and size of misc files
        >= 2 : also include database directory actual size

    server[in]        Connected server
    rows[in]          A list of databases and their calculated sizes
    include_list[in]  A list of databases included on the command line
    datadir[in]       The data directory
    format[in]        If True, format columns and rows to standard sizes
    have_read[in]     If True, user has read access to datadir path
    verbosity[in]     Controls how much data is shown
    include_empty[in] Include empty databases in list

    return (tuple) (column headers, rows, total size)
    """

    total = 0
    results = []
    max_col = 0

    # build the list
    for row in rows:
        # If user can read the datadir, calculate actual and misc file totals
        if have_read:
            dbdir_size = _get_folder_size(os.path.join(datadir, row[0]))
            misc_files = _get_db_dir_size(os.path.join(datadir, row[0]))
        else:
            dbdir_size = 0
            misc_files = 0

        if row[1] is None:
            data_size = 0
            db_total = 0
        else:
            data_size = int(row[1])
            db_total = int(row[1]) + misc_files

        # Count total for all databases
        total += data_size + misc_files

        if have_read:
            if verbosity >= 2: # get all columns
                results.append((row[0], dbdir_size, data_size, misc_files,
                                db_total))
            elif verbosity > 0:
                results.append((row[0], data_size, misc_files, db_total))
            else:
                results.append((row[0], db_total))
        else:
            results.append((row[0], db_total))

    if have_read and verbosity > 0:
        num_cols = min(verbosity+2, 4)
    else:
        num_cols = 1

    # Build column list and format if necessary
    col_list = ['db_name']
    if num_cols == 4: # get all columns
        col_list.append('db_dir_size')
        col_list.append('data_size')
        col_list.append('misc_files')
        col_list.append('total')
    elif num_cols == 3:
        col_list.append('data_size')
        col_list.append('misc_files')
        col_list.append('total')
    else:
        col_list.append('total')

    fmt_cols = []
    max_col = [0,0,0,0]
    if format:
        fmt_cols.append(col_list[0])
        for i in range(0,num_cols):
            max_col[i] = _get_formatted_max_width(results, col_list, i+1)
            fmt_cols.append("{0:>{1}}".format(col_list[i+1], max_col[i]))
    else:
        fmt_cols = col_list

    # format the list if needed
    fmt_rows = []
    if format:
        for row in results:
            fmt_data = ['','','','','']
            # Put in commas and justify strings
            for i in range(0,num_cols):
                fmt_data[i] = locale.format("%d", row[i+1], grouping=True)
            if num_cols == 4: # get all columns
                fmt_rows.append((row[0], fmt_data[0], fmt_data[1],
                                 fmt_data[2], fmt_data[3]))
            elif num_cols == 3:
                fmt_rows.append((row[0], fmt_data[0], fmt_data[1],
                                 fmt_data[2]))
            else:
                fmt_rows.append((row[0], fmt_data[0]))
    else:
        fmt_rows = results

    if include_empty:
        dbs = server.exec_query("SHOW DATABASES")
        if len(fmt_rows) != len(dbs)-1:
            # We have orphaned database - databases not listed in IS.TABLES
            exclude_list = []
            for row in fmt_rows:
                exclude_list.append(row[0])
            for db in dbs:
                if db[0].upper() != "INFORMATION_SCHEMA" and \
                   db[0] not in exclude_list and \
                   (include_list is None or include_list == [] or \
                    db[0] in include_list):
                    if format:
                        fmt_data = ['','','','','']
                        for i in range(0,num_cols):
                            if type(row[i+1]) == type(int):
                                fmt_data[i] = locale.format("%s",
                                                            int(row[i+1]),
                                                            grouping=True)
                            else:
                                fmt_data[i] = locale.format("%s", row[i+1],
                                                            grouping=True)
                        if num_cols == 4: # get all columns
                            fmt_rows.insert(0, (db[0], fmt_data[0],
                                                fmt_data[1], fmt_data[2],
                                                fmt_data[3]))
                        elif num_cols == 3:
                            fmt_rows.insert(0, (db[0], fmt_data[0],
                                             fmt_data[1], fmt_data[2]))
                        else:
                            fmt_rows.insert(0, (db[0], fmt_data[0]))
                    else:
                        if num_cols == 4:
                            fmt_rows.insert(0, (db[0], 0, 0, 0, 0))
                        elif num_cols == 3:
                            fmt_rows.insert(0, (db[0], 0, 0, 0))
                        else:
                            fmt_rows.insert(0, (db[0], 0))

    return (fmt_cols, fmt_rows, total)


def show_database_usage(server, datadir, dblist, options):
    """Show database usage.

    Display a list of databases and their disk space usage. The method
    accepts a list of databases to list or None or [] for all databases.

    server[in]        Connected server to operate against
    datadir[in]       The datadir for the server
    dblist[in]        List of databases
    options[in]       Required options for operation: format, no_headers,
                      verbosity, have_read, include_empty

    returns True or exception on error
    """
    
    from mysql.utilities.common.format import print_list

    format = options.get("format", "grid")
    no_headers = options.get("no_headers", False)
    verbosity = options.get("verbosity", 0)
    have_read = options.get("have_read", False)
    include_empty = options.get("do_empty", True)
    do_all = options.get("do_all", True)
    quiet = options.get("quiet", False)

    if verbosity is None:
        verbosity = 0

    locale.setlocale(locale.LC_ALL, '')

    # Check to see if we're doing all databases.
    if len(dblist) > 0:
        include_list = "("
        stop = len(dblist)
        for i in range(0,stop):
            include_list += "'%s'" % dblist[i]
            if i < stop-1:
                include_list += ", "
        include_list += ")"
        where_clause = "WHERE table_schema IN %s" % include_list
        where_clause += " AND table_schema != 'INFORMATION_SCHEMA'"
    else:
        where_clause = "WHERE table_schema != 'INFORMATION_SCHEMA'"

    res = server.exec_query(_QUERY_DBSIZE % where_clause)

    # Get list of databases with sizes and formatted when necessary
    columns, rows, db_total = _build_db_list(server, res, dblist, datadir,
                                             format == "grid",
                                             have_read, verbosity,
                                             include_empty or do_all)

    if not quiet:
        print "# Database totals:"
    print_list(sys.stdout, format, columns, rows, no_headers)
    if not quiet:
        _print_size("\nTotal database disk usage = ", db_total)
        print

    return True


def show_logfile_usage(server, options):
    """Show log file disk space usage.

    Display log file information if logs are turned on.

    server[in]        Connected server to operate against
    datadir[in]       The datadir for the server
    options[in]       Required options for operation: format, no_headers

    return True or raise exception on error
    """
    from mysql.utilities.common.format import print_list

    format = options.get("format", "grid")
    no_headers = options.get("no_headers", False)
    verbosity = options.get("verbosity", 0)
    have_read = options.get("have_read", False)
    quiet = options.get("quiet", False)

    if not quiet:
        print "# Log information."
    total = 0
    
    _LOG_NAMES = [
        ('general_log', '_file'), ('slow_query_log', '_file'),
        ('log_error', '')
    ]
    logs = []
    for log_name in _LOG_NAMES:
        log, size = _get_log_information(server, log_name[0], log_name[1])
        if log is not None:
            logs.append((log, size))
        total += size
    
    fmt_logs = []
    columns = ['log_name', 'size']
    if len(logs) > 0:
        if format == 'grid':
            max_col = _get_formatted_max_width(logs, columns, 1)
            if max_col < len('size'):
                max_col = len('size')
            size = "{0:>{1}}".format('size', max_col)
            columns = ['log_name',size]
            for row in logs:
                # Add commas
                size = locale.format("%d", row[1], grouping=True)
                # Make justified strings
                size = "{0:>{1}}".format(size, max_col)
                fmt_logs.append((row[0], size))

        else:
            fmt_logs = logs

        print_list(sys.stdout, format, columns, fmt_logs, no_headers)
        if not quiet:
            _print_size("\nTotal size of logs = ", total)
            print

    return True


def show_log_usage(server, datadir, options):
    """Show binary or relay log disk space usage.

    Display binary log file information if binlog turned on if log_type =
    'binary log' (default) or show relay log file information is server is
    a slave and relay log is engaged.

    server[in]        Connected server to operate against
    datadir[in]       The datadir for the server
    options[in]       Required options for operation: format, no_headers.
                      log_type

    return True or raise exception on error
    """
    from mysql.utilities.common.format import print_list

    format = options.get("format", "grid")
    no_headers = options.get("no_headers", False)
    verbosity = options.get("verbosity", 0)
    have_read = options.get("have_read", False)
    log_type = options.get("log_type", "binary log")
    quiet = options.get("quiet", False)

    current_log = None

    # Check for binlog on first.
    if log_type == 'binary log':
        res = server.show_server_variable('log_bin')
        if res != [] and res[0][1].upper() == 'OFF':
            print "# Binary logging is turned off on the server."
            return True
    else:
        try:
            res = server.exec_query("SHOW SLAVE STATUS")
            if res != [] and res is not None:
                current_log = res[0][7]
        except:
            raise UtilError("Cannot get relay log information")
        if res == []:
            print "# Server is not an active slave - no relay log information."
            return True

    if os.access(datadir, os.R_OK):
        if not quiet:
            print "# %s information:" % log_type

        if log_type == 'binary log':
            try:
                res = server.exec_query("SHOW MASTER STATUS")
                if res != []:
                    current_log = res[0][0]
            except:
                raise UtilError("Cannot get binary log information.")

        if current_log is None:
            print "# Cannot access %s files.\n" % log_type
            return False
        
        if not quiet:
            print "Current %s file = %s" % (log_type, current_log)

        # As of 5.6.2, users can specify location of binlog and relaylog.
        if server.check_version_compat(5, 6, 2):
            if log_type == 'binary log':
                res = server.show_server_variable("log_bin_basename")[0]
            else:
                res = server.show_server_variable("relay_log_basename")[0]
            parts = os.path.split(res[1])
            log_path = os.path.join(parts[:len(parts) - 1])[0]
            log_prefix = parts[len(parts) - 1]
        else:
            log_path = datadir
            log_prefix = os.path.splitext(current_log)[0]
        if log_path == '':
            log_path = datadir
            
        logs, total = _build_log_list(log_path, log_prefix)
        if logs == []:
            raise UtilError("The %s are missing." % log_type)

        columns = ['log_file']
        size = 'size'
        fmt_logs = []
        if format == 'GRID':
            max_col = _get_formatted_max_width(logs, ('log_file', 'size'), 1)
            if max_col < len('size'):
                max_col = len('size')
            size = "{0:>{1}}".format('size', max_col)
            columns.append(size)

            for row in logs:
                # Add commas
                size = locale.format("%d", row[1], grouping=True)
                # Make justified strings
                size = "{0:>{1}}".format(size, max_col)
                fmt_logs.append((row[0], size))

        else:
            fmt_logs = logs
            columns.append('size')

        print_list(sys.stdout, format, columns, fmt_logs, no_headers)
        if not quiet:
            _print_size("\nTotal size of %ss = " % log_type, total)
            print

    else:
        print "# Binlog information not accessible. " + \
              "Check your permissions."

    return True


def show_innodb_usage(server, datadir, options):
    """Show InnoDB tablespace disk space usage.

    Display InnoDB tablespace information if InnoDB turned on.

    server[in]        Connected server to operate against
    datadir[in]       The datadir for the server
    options[in]       Required options for operation: format, no_headers

    return True or raise exception on error
    """
    from mysql.utilities.common.format import print_list

    format = options.get("format", "grid")
    no_headers = options.get("no_headers", False)
    verbosity = options.get("verbosity", 0)
    have_read = options.get("have_read", False)
    quiet = options.get("quiet", False)

    # Check to see if we have innodb
    res = server.show_server_variable('have_innodb')
    if res != [] and res[0][1].upper() in ("NO", "DISABLED"):
        print "# InnoDB is disabled on this server."
        return True

    # Modified check for version 5.5
    res = server.exec_query("USE INFORMATION_SCHEMA")
    res = server.exec_query("SELECT engine, support "
                            "FROM INFORMATION_SCHEMA.ENGINES "
                            "WHERE engine='InnoDB'")
    if res != [] and res[0][1].upper() == "NO":
        print "# InnoDB is disabled on this server."
        return True

    # Check to see if innodb_file_per_table is ON
    res = server.show_server_variable('innodb_file_per_table')
    if res != [] and res[0][1].upper() == "ON":
        innodb_file_per_table = True
    else:
        innodb_file_per_table = False

    # Get path
    res = server.show_server_variable('innodb_data_home_dir')
    if res != [] and len(res[0][1]) > 0:
        innodb_dir = res[0][1]
    else:
        innodb_dir = datadir

    if os.access(innodb_dir, os.R_OK):
        if not quiet:
            print "# InnoDB tablespace information:"

        res = server.show_server_variable('innodb_data_file_path')
        tablespaces = []
        if res != [] and len(res[0][1]) > 0:
            parts = res[0][1].split(";")
            for part in parts:
                tablespaces.append(part)

        innodb, total = _build_innodb_list(innodb_file_per_table, innodb_dir,
                                           datadir, tablespaces, verbosity)
        if innodb == []:
            raise UtilError("InnoDB is enabled but there is a problem "
                                 "reading the tablespace files.")

        columns = ['innodb_file', 'size']
        if verbosity > 0:
            columns.append('type')
            columns.append('specificaton')
        size = 'size'
        fmt_innodb = []
        if format == 'GRID':
            max_col = _get_formatted_max_width(innodb, columns, 1)
            if max_col < len('size'):
                max_col = len('size')
            size = "{0:>{1}}".format('size', max_col)
            columns = ['innodb_file']
            columns.append(size)
            if verbosity > 0:
                columns.append('type')
                columns.append('specificaton')

            for row in innodb:
                # Add commas
                size = locale.format("%d", row[1], grouping=True)
                # Make justified strings
                size = "{0:>{1}}".format(size, max_col)
                if verbosity > 0:
                    fmt_innodb.append((row[0], size, row[2], row[3]))
                else:
                    fmt_innodb.append((row[0], size))

        else:
            fmt_innodb = innodb

        print_list(sys.stdout, format, columns, fmt_innodb, no_headers)
        if not quiet:
            _print_size("\nTotal size of InnoDB files = ", total)
            print

        if verbosity > 0 and not innodb_file_per_table and not quiet:
            for tablespace in innodb:
                if tablespace[1] != 'log file':
                    parts = tablespace[3].split(":")
                    if len(parts) > 2:
                        size = int(tablespace[1]) / _MB
                        print "Tablespace %s can be " % tablespace[3] + \
                              "extended by using %s:%sM[...]\n" % \
                              (parts[0], size)


    else:
        print "# InnoDB data file information is not accessible. " + \
              "Check your permissions."

    if not innodb_file_per_table:
        res = server.exec_query(_QUERY_DATAFREE)
        if res != []:
            if len(res) > 1:
                raise UtilError("Found multiple rows for freespace.")
            else:
                size = int(res[0][0])
                if not quiet:
                    _print_size("InnoDB freespace = ", size)
                    print

    return True
