#
# Copyright (c) 2010, 2012 Oracle and/or its affiliates. All rights reserved.
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

from mysql.utilities.exception import UtilError

_RPL_COMMANDS, _RPL_FILE = 0, 1

_GTID_WARNING = "# WARNING: The server supports GTIDs but you have " + \
    "elected to skip exexcuting the GTID_EXECUTED statement. Please refer " + \
    "to the MySQL online reference manual for more information about how " + \
    "to handle GTID enabled servers with backup and restore operations."
_GTID_BACKUP_WARNING = "# WARNING: A partial copy from a server that has " + \
    "GTIDs enabled will by default include the GTIDs of all transactions, " + \
    "even those that changed suppressed parts of the database. If you " + \
    "don't want to generate the GTID statement, use the --skip-gtid " + \
    "option. To export all databases, use the --all option and do not " + \
    "specify a list of databases."
_NON_GTID_WARNING = "# WARNING: The %s server does not support " + \
    "GTIDs yet the %s server does support GTIDs. To suppress this " + \
    "warning, use the --skip-gtid option when copying %s a non-GTID " + \
    "enabled server."

def get_copy_lock(server, db_list, options, include_mysql=False,
                  cloning=False):
    """Get an instance of the Lock class with a standard copy (read) lock
    
    This method creates an instance of the Lock class using the lock type
    specified in the options. It is used to initiate the locks for the copy
    and related operations.
    
    server[in]             Server instance for locking calls
    db_list[in]            list of database names
    options[in]            option dictionary
                           Must include the skip_* options for copy and export
    include_mysql[in]      if True, include the mysql tables for copy operation
    cloning[in]            if True, create lock tables with WRITE on dest db
                           Default = False
    
    Returns Lock - Lock class instance
    """

    from mysql.utilities.common.database import Database
    from mysql.utilities.common.lock import Lock

    rpl_mode = options.get("rpl_mode", None)
    locking = options.get('locking', 'snapshot')
    table_lock_list = []
    
    # Determine if we need to use FTWRL. There are two conditions:
    #  - running on master (rpl_mode = 'master')
    #  - using locking = 'lock-all' and rpl_mode present
    if (rpl_mode in ["master", "both"]) or (rpl_mode and locking == 'lock-all'):
        new_opts = options.copy()
        new_opts['locking'] = 'flush'
        lock = Lock(server, [], new_opts)

    # if this is a lock-all type and not replication operation,
    # find all tables and lock them
    elif locking == 'lock-all':
        table_lock_list = []

        # Build table lock list
        for db_name in db_list:
            db = db_name[0] if type(db_name) == tuple else db_name
            source_db = Database(server, db)
            tables = source_db.get_db_objects("TABLE")
            for table in tables:
                table_lock_list.append(("%s.%s" % (db, table[0]),
                                        'READ'))
                # Cloning requires issuing WRITE locks because we use same conn.
                # Non-cloning will issue WRITE lock on a new destination conn.
                if cloning:
                    if db_name[1] is None:
                        db_clone = db_name[0]
                    else:
                        db_clone = db_name[1]
                    # For cloning, we use the same connection so we need to
                    # lock the destination tables with WRITE.
                    table_lock_list.append(("%s.%s" % (db_clone, table[0]),
                                            'WRITE'))
            # We must include views for server version 5.5.3 and higher
            if server.check_version_compat(5, 5, 3):
                tables = source_db.get_db_objects("VIEW")
                for table in tables:
                    table_lock_list.append(("%s.%s" % (db, table[0]),
                                            'READ'))
                    # Cloning requires issuing WRITE locks because we use same conn.
                    # Non-cloning will issue WRITE lock on a new destination conn.
                    if cloning:
                        if db_name[1] is None:
                            db_clone = db_name[0]
                        else:
                            db_clone = db_name[1]
                        # For cloning, we use the same connection so we need to
                        # lock the destination tables with WRITE.
                        table_lock_list.append(("%s.%s" % (db_clone, table[0]),
                                                'WRITE'))
                
                    
        # Now add mysql tables
        if include_mysql:
            # Don't lock proc tables if no procs of funcs are being read
            if not options.get('skip_procs', False) and \
               not options.get('skip_funcs', False):
                table_lock_list.append(("mysql.proc", 'READ'))
                table_lock_list.append(("mysql.procs_priv", 'READ'))
            # Don't lock event table if events are skipped
            if not options.get('skip_events', False):
                table_lock_list.append(("mysql.event", 'READ'))
        lock = Lock(server, table_lock_list, options)

    # Use default or no locking option
    else:
        lock = Lock(server, [], options)
       
    return lock


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
    
    from mysql.utilities.common.database import Database

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


def copy_db(src_val, dest_val, db_list, options):
    """Copy a database

    This method will copy a database and all of its objects and data from
    one server (source) to another (destination). Options are available to
    selectively ignore each type of object. The force parameter is
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
                       skip_data, verbose, force, quiet,
                       connections, debug, exclude_names, exclude_patterns)

    Notes:
        force    - if True, the database on the destination will be dropped
                   if it exists (default is False)
        quiet    - do not print any information during operation
                   (default is False)

    Returns bool True = success, False = error
    """

    from mysql.utilities.common.database import Database
    from mysql.utilities.common.options import check_engine_options
    from mysql.utilities.common.server import connect_servers
    from mysql.utilities.command.dbexport import get_change_master_command
    from mysql.utilities.command.dbexport import get_gtid_commands

    verbose = options.get("verbose", False)
    quiet = options.get("quiet", False)
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

    rpl_info = ([], None)

    conn_options = {
        'quiet'     : quiet,
        'version'   : "5.1.30",
    }
    servers = connect_servers(src_val, dest_val, conn_options)
    cloning = (src_val == dest_val) or dest_val is None
    
    source = servers[0]
    if cloning:
        destination = servers[0]
    else:
        destination = servers[1]
    
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
                db_list.append((row[0], None)) # Keep same name
        else:
            raise UtilError("Cannot copy all databases on the same server.")
    elif not skip_gtid and src_gtid:
        # Check to see if this is a full copy (complete backup)
        all_dbs = source.exec_query("SHOW DATABASES")
        dbs = [db[0] for db in db_list]
        for db in all_dbs:
            if db[0].upper() in ["MYSQL", "INFORMATION_SCHEMA",
                                 "PERFORMANCE_SCHEMA"]:
                continue
            if not db[0] in dbs:
                print _GTID_BACKUP_WARNING
                break

    # Do error checking and preliminary work:
    #  - Check user permissions on source and destination for all databases
    #  - Check to see if executing on same server but same db name (error)
    #  - Build list of tables to lock for copying data (if no skipping data)
    #  - Check storage engine compatibility
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
            'skip_views'  : skip_views,
            'skip_procs'  : skip_procs,
            'skip_funcs'  : skip_funcs,
            'skip_grants' : skip_grants,
            'skip_events' : skip_events,
        }

        source_db.check_read_access(src_val["user"], src_val["host"],
                                    access_options)
        
        dest_db.check_write_access(dest_val['user'], dest_val['host'],
                                   access_options)

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

    # Get replication commands if rpl_mode specified.
    # if --rpl specified, dump replication initial commands
    rpl_info = None

    # Turn off foreign keys if they were on at the start
    destination.disable_foreign_key_checks(True)

    # Get GTID commands
    new_opts = options.copy()
    if not skip_gtid:
        gtid_info = get_gtid_commands(source, new_opts)
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
            destination.exec_query(cmd)
    
    if options.get("rpl_mode", None):
        new_opts = options.copy()
        new_opts['multiline'] = False
        new_opts['strict'] = True
        rpl_info = get_change_master_command(src_val, new_opts)
        destination.exec_query("STOP SLAVE;")

    # Copy objects
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

    # Copy data
    if not skip_data and not skip_tables:
    
        # Copy tables
        for db_name in db_list:
    
            # Get a Database class instance
            db = Database(source, db_name[0], options)
    
            # Perform the copy
            db.init()
            db.copy_data(db_name[1], options, destination,
                         options.get("threads", False))
            
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

    if not quiet:
        print "#...done."
    return True
