#
# Copyright (c) 2010, 2017, Oracle and/or its affiliates. All rights reserved.
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
This file contains the copy database operation which ensures a database
is exactly the same among two servers.
"""

import sys

from mysql.utilities.exception import UtilError
from mysql.utilities.common.database import Database
from mysql.utilities.common.options import check_engine_options
from mysql.utilities.common.server import connect_servers
from mysql.utilities.command.dbexport import (get_change_master_command,
                                              get_copy_lock, get_gtid_commands)


_RPL_COMMANDS, _RPL_FILE = 0, 1

_GTID_WARNING = ("# WARNING: The server supports GTIDs but you have elected "
                 "to skip executing the GTID_EXECUTED statement. Please "
                 "refer to the MySQL online reference manual for more "
                 "information about how to handle GTID enabled servers with "
                 "backup and restore operations.")
_GTID_BACKUP_WARNING = ("# WARNING: A partial copy from a server that has "
                        "GTIDs enabled will by default include the GTIDs of "
                        "all transactions, even those that changed suppressed "
                        "parts of the database. If you don't want to generate "
                        "the GTID statement, use the --skip-gtid option. To "
                        "export all databases, use the --all option and do "
                        "not specify a list of databases.")
_NON_GTID_WARNING = ("# WARNING: The %s server does not support GTIDs yet the "
                     "%s server does support GTIDs. To suppress this warning, "
                     "use the --skip-gtid option when copying %s a non-GTID "
                     "enabled server.")
_CHECK_BLOBS_NOT_NULL = """
    SELECT DISTINCT TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE (COLUMN_TYPE LIKE '%BLOB%' OR COLUMN_TYPE LIKE '%TEXT%') AND
    IS_NULLABLE = 'NO' AND TABLE_SCHEMA = '{0}';
"""
_BLOBS_NOT_NULL_MSG = ("{0}: The following tables have blob fields set to "
                       "NOT NULL.")
_BLOBS_NOT_NULL_ERROR = ("The copy operation cannot proceed unless "
                         "the blob fields permit NULL values.\nTo copy data "
                         "with NOT NULL blob fields, you can either:\na) "
                         "First remove the NOT NULL restriction, copy the "
                         "data, then add the NOT NULL restriction using "
                         "ALTER TABLE statements.\n  -or-\nb) Run the "
                         "command again with the --not-null-blobs "
                         "option and the utility will perform (a) for you.\n")
_AUTO_INC_WARNING = ("# WARNING: One or more tables were detected with a "
                     "value of 0 in an auto_increment column. To enable "
                     "copying of data, the code enabled the sql_mode "
                     "NO_AUTO_VALUE_ON_ZERO during the copy and disabled "
                     "it after the copy. Use -vvv to see the statements.")


def get_alter_table_col_not_null(server, db1, db2, table, col):
    """
    Get the ALTER TABLE statement for the column in a tuple stripping
    the NOT NULL option for the second item in the tuple. This allows
    the execution of the statements before and after to remove then
    reset the NOT NULL restriction.

    server[in]             Server class instance
    db1[in]                Source database name
    db2[in]                Destination database name
    table[in]              Table name
    col[in]                Column name

    Returns: before and after ALTER statement, None = col not found
    """
    alter_table = "ALTER TABLE {0}.{1} CHANGE COLUMN {2} {3}"
    res = server.exec_query("SHOW CREATE TABLE {0}.{1}".format(db1, table))
    if res:
        rows = res[0][1]
    else:
        return None
    for row in rows.split("\n"):
        if "`{0}`".format(col) in row:
            col_str = row.strip().strip(",")
            col_str_new = row.strip().strip(",").strip("NOT NULL")
            return (alter_table.format(db2, table, col, col_str_new),
                    alter_table.format(db2, table, col, col_str))


def check_blobs_not_null(server, db_list, warn=False):
    """
    Check for any blob fields that have NOT null set. Prints error message
    if any are encountered.

    server[in]             Server class instance
    db_list[in]            List of databases to be copied in form
                           (src, dst)
    warn[in]               If true, print WARNING instead of ERROR

    Returns: list - list of blobs with NOT NULL, None = none found
    """
    if not db_list:
        return None
    blob_fields = []
    for db in db_list:
        res = server.exec_query(_CHECK_BLOBS_NOT_NULL.format(db[0]))
        if res:
            if warn:
                print(_BLOBS_NOT_NULL_MSG.format("WARNING"))
            else:
                print("{0} {1}".format(_BLOBS_NOT_NULL_MSG.format("ERROR"),
                                       _BLOBS_NOT_NULL_ERROR))
            for row in res:
                print("    {0}.{1} Column {2}".format(row[0], row[1], row[2]))
                blob_fields.append((row[0], row[1], row[2], db[1]))
            print
    if blob_fields == []:
        return None
    return blob_fields


def _copy_objects(source, destination, db_list, options,
                  show_message=True, do_create=True):
    """Copy objects for a list of databases

    This method loops through a list of databases copying the objects as
    controlled by the skip options.

    source[in]             Server class instance for source
    destination[in]        Server class instance for destination
    options[in]            copy options
    show_message[in]       if True, display copy message
                           Default = True
    do_create[in]          if True, execute create statement for database
                           Default = True
    """
    # Copy objects
    for db_name in db_list:

        if show_message:
            # Display copy message
            if not options.get('quiet', False):
                msg = "# Copying database %s " % db_name[0]
                if db_name[1]:
                    msg += "renamed as %s" % (db_name[1])
                print msg

        # Get a Database class instance
        db = Database(source, db_name[0], options)

        # Perform the copy
        db.init()
        db.copy_objects(db_name[1], options, destination,
                        options.get("threads", False), do_create)


def multiprocess_db_copy_task(copy_db_task):
    """Multiprocess copy database method.

    This method wraps the copy_db method to allow its concurrent
    execution by a pool of processes.

    copy_db_task[in]    dictionary of values required by a process to perform
                        the database copy task, namely:
                        {'source_srv': <dict with source connect values>,
                         'dest_srv': <dict with destination connect values>,
                         'db_list': <list of databases to copy>,
                         'options': <dict of options>,
                        }
    """
    # Get input values to execute task.
    source_srv = copy_db_task.get('source_srv')
    dest_srv = copy_db_task.get('dest_srv')
    db_list = copy_db_task.get('db_list')
    options = copy_db_task.get('options')
    # Execute copy databases task.
    # NOTE: Must handle any exception here, because worker processes will not
    # propagate them to the main process.
    try:
        copy_db(source_srv, dest_srv, db_list, options)
    except UtilError:
        _, err, _ = sys.exc_info()
        print("ERROR: {0}".format(err.errmsg))


def copy_db(src_val, dest_val, db_list, options):
    """Copy a database

    This method will copy a database and all of its objects and data from
    one server (source) to another (destination). Options are available to
    selectively ignore each type of object. The do_drop parameter is
    used to permit the copy to overwrite an existing destination database
    (default is to not overwrite).

    src_val[in]        a dictionary containing connection information for the
                       source including:
                       (user, password, host, port, socket)
    dest_val[in]       a dictionary containing connection information for the
                       destination including:
                       (user, password, host, port, socket)
    options[in]        a dictionary containing the options for the copy:
                       (skip_tables, skip_views, skip_triggers, skip_procs,
                       skip_funcs, skip_events, skip_grants, skip_create,
                       skip_data, verbose, do_drop, quiet,
                       connections, debug, exclude_names, exclude_patterns)

    Notes:
        do_drop  - if True, the database on the destination will be dropped
                   if it exists (default is False)
        quiet    - do not print any information during operation
                   (default is False)

    Returns bool True = success, False = error
    """
    verbose = options.get("verbose", False)
    quiet = options.get("quiet", False)
    do_drop = options.get("do_drop", False)
    skip_views = options.get("skip_views", False)
    skip_procs = options.get("skip_procs", False)
    skip_funcs = options.get("skip_funcs", False)
    skip_events = options.get("skip_events", False)
    skip_grants = options.get("skip_grants", False)
    skip_data = options.get("skip_data", False)
    skip_triggers = options.get("skip_triggers", False)
    skip_tables = options.get("skip_tables", False)
    skip_gtid = options.get("skip_gtid", False)
    locking = options.get("locking", "snapshot")

    conn_options = {
        'quiet': quiet,
        'version': "5.1.30",
    }
    servers = connect_servers(src_val, dest_val, conn_options)
    cloning = (src_val == dest_val) or dest_val is None

    source = servers[0]
    if cloning:
        destination = servers[0]
    else:
        destination = servers[1]
        # Test if SQL_MODE is 'NO_BACKSLASH_ESCAPES' in the destination server
        if destination.select_variable("SQL_MODE") == "NO_BACKSLASH_ESCAPES":
            print("# WARNING: The SQL_MODE in the destination server is "
                  "'NO_BACKSLASH_ESCAPES', it will be changed temporarily "
                  "for data insertion.")

    src_gtid = source.supports_gtid() == 'ON'
    dest_gtid = destination.supports_gtid() == 'ON'if destination else False

    # Get list of all databases from source if --all is specified.
    # Ignore system databases.
    if options.get("all", False):
        # The --all option is valid only if not cloning.
        if not cloning:
            if not quiet:
                print "# Including all databases."
            rows = source.get_all_databases()
            for row in rows:
                db_list.append((row[0], None))  # Keep same name
        else:
            raise UtilError("Cannot copy all databases on the same server.")
    elif not skip_gtid and src_gtid:
        # Check to see if this is a full copy (complete backup)
        all_dbs = source.exec_query("SHOW DATABASES")
        dbs = [db[0] for db in db_list]
        for db in all_dbs:
            if db[0].upper() in ["MYSQL", "INFORMATION_SCHEMA",
                                 "PERFORMANCE_SCHEMA", "SYS"]:
                continue
            if db[0] not in dbs:
                print _GTID_BACKUP_WARNING
                break

    # Do error checking and preliminary work:
    #  - Check user permissions on source and destination for all databases
    #  - Check to see if executing on same server but same db name (error)
    #  - Build list of tables to lock for copying data (if no skipping data)
    #  - Check storage engine compatibility
    auto_increment_zero = False
    for db_name in db_list:
        source_db = Database(source, db_name[0])
        if destination is None:
            destination = source
        if db_name[1] is None:
            db = db_name[0]
        else:
            db = db_name[1]
        dest_db = Database(destination, db)

        # Make a dictionary of the options
        access_options = {
            'skip_views': skip_views,
            'skip_procs': skip_procs,
            'skip_funcs': skip_funcs,
            'skip_grants': skip_grants,
            'skip_events': skip_events,
            'skip_triggers': skip_triggers,
        }

        source_db.check_read_access(src_val["user"], src_val["host"],
                                    access_options)

        # Make a dictionary containing the list of objects from source db
        source_objects = {
            "views": source_db.get_db_objects("VIEW", columns="full"),
            "procs": source_db.get_db_objects("PROCEDURE", columns="full"),
            "funcs": source_db.get_db_objects("FUNCTION", columns="full"),
            "events": source_db.get_db_objects("EVENT", columns="full"),
            "triggers": source_db.get_db_objects("TRIGGER", columns="full"),
        }

        dest_db.check_write_access(dest_val['user'], dest_val['host'],
                                   access_options, source_objects, do_drop)

        # Error is source db and destination db are the same and we're cloning
        if destination == source and db_name[0] == db_name[1]:
            raise UtilError("Destination database name is same as "
                            "source - source = %s, destination = %s" %
                            (db_name[0], db_name[1]))

        # Error is source database does not exist
        if not source_db.exists():
            raise UtilError("Source database does not exist - %s" % db_name[0])

        # Check storage engines
        check_engine_options(destination,
                             options.get("new_engine", None),
                             options.get("def_engine", None),
                             False, options.get("quiet", False))

        # Checking auto increment. See if any tables have 0 in their auto
        # increment column.
        if source_db.check_auto_increment():
            auto_increment_zero = True

    # Get replication commands if rpl_mode specified.
    # if --rpl specified, dump replication initial commands
    rpl_info = None

    # Turn off foreign keys if they were on at the start
    destination.disable_foreign_key_checks(True)

    # Get GTID commands
    if not skip_gtid:
        gtid_info = get_gtid_commands(source)
        if src_gtid and not dest_gtid:
            print _NON_GTID_WARNING % ("destination", "source", "to")
        elif not src_gtid and dest_gtid:
            print _NON_GTID_WARNING % ("source", "destination", "from")
    else:
        gtid_info = None
        if src_gtid and not cloning:
            print _GTID_WARNING

    # If cloning, turn off gtid generation
    if gtid_info and cloning:
        gtid_info = None
    # if GTIDs enabled, write the GTID commands
    if gtid_info and dest_gtid:
        # Check GTID version for complete feature support
        destination.check_gtid_version()
        # Check the gtid_purged value too
        destination.check_gtid_executed()
        for cmd in gtid_info[0]:
            print "# GTID operation:", cmd
            destination.exec_query(cmd, {'fetch': False, 'commit': False})

    if options.get("rpl_mode", None):
        new_opts = options.copy()
        new_opts['multiline'] = False
        new_opts['strict'] = True
        rpl_info = get_change_master_command(src_val, new_opts)
        destination.exec_query("STOP SLAVE", {'fetch': False, 'commit': False})

    # Add sql_mode for copying 0 auto increment values
    if auto_increment_zero:
        sql_mode_str = destination.sql_mode("NO_AUTO_VALUE_ON_ZERO", True)
        if sql_mode_str:
            print(_AUTO_INC_WARNING)
            if verbose:
                print("# {0}".format(sql_mode_str))

    # Copy (create) objects.
    # We need to delay trigger and events to after data is loaded
    new_opts = options.copy()
    new_opts['skip_triggers'] = True
    new_opts['skip_events'] = True

    # Get the table locks unless we are cloning with lock-all
    if not (cloning and locking == 'lock-all'):
        my_lock = get_copy_lock(source, db_list, options, True)

    _copy_objects(source, destination, db_list, new_opts)

    # If we are cloning, take the write locks prior to copying data
    if cloning and locking == 'lock-all':
        my_lock = get_copy_lock(source, db_list, options, True, cloning)

    # Copy tables data
    if not skip_data and not skip_tables:

        # If there are statements to execute before the copy, execute them here
        before_stmts = options.get("before_alter", None)
        if before_stmts:
            for stmt in before_stmts:
                if not destination.exec_query(stmt):
                    print("WARNING: Statement did not execute: "
                          "{0}".format(stmt))

        # Copy tables
        for db_name in db_list:

            # Get a Database class instance
            db = Database(source, db_name[0], options)

            # Perform the copy
            # Note: No longer use threads, use multiprocessing instead.
            db.init()
            db.copy_data(db_name[1], options, destination, connections=1,
                         src_con_val=src_val, dest_con_val=dest_val)

        # If there are statements to execute after the copy, execute them here
        after_stmts = options.get("after_alter", None)
        if after_stmts:
            for stmt in after_stmts:
                if not destination.exec_query(stmt):
                    print("WARNING: Statement did not execute: "
                          "{0}".format(stmt))

    # if cloning with lock-all unlock here to avoid system table lock conflicts
    if cloning and locking == 'lock-all':
        my_lock.unlock()

    # Create triggers for all databases
    if not skip_triggers:
        new_opts = options.copy()
        new_opts['skip_tables'] = True
        new_opts['skip_views'] = True
        new_opts['skip_procs'] = True
        new_opts['skip_funcs'] = True
        new_opts['skip_events'] = True
        new_opts['skip_grants'] = True
        new_opts['skip_create'] = True
        _copy_objects(source, destination, db_list, new_opts, False, False)

    # Create events for all databases
    if not skip_events:
        new_opts = options.copy()
        new_opts['skip_tables'] = True
        new_opts['skip_views'] = True
        new_opts['skip_procs'] = True
        new_opts['skip_funcs'] = True
        new_opts['skip_triggers'] = True
        new_opts['skip_grants'] = True
        new_opts['skip_create'] = True
        _copy_objects(source, destination, db_list, new_opts, False, False)

    if not (cloning and locking == 'lock-all'):
        my_lock.unlock()

    # if GTIDs enabled, write the GTID-related commands
    if gtid_info and dest_gtid:
        print "# GTID operation:", gtid_info[1]
        destination.exec_query(gtid_info[1])

    if options.get("rpl_mode", None):
        for cmd in rpl_info[_RPL_COMMANDS]:
            if cmd[0] == '#' and not quiet:
                print cmd
            else:
                if verbose:
                    print cmd
                destination.exec_query(cmd)
        destination.exec_query("START SLAVE;")

    # Turn on foreign keys if they were on at the start
    destination.disable_foreign_key_checks(False)

    # Remove sql_mode for copying 0 auto increment values
    if auto_increment_zero:
        sql_mode_str = destination.sql_mode("NO_AUTO_VALUE_ON_ZERO", False)
        if sql_mode_str and verbose:
            print("# {0}".format(sql_mode_str))

    if not quiet:
        print "#...done."
    return True
