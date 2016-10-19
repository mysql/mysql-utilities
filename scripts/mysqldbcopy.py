#!/usr/bin/env python
#
# Copyright (c) 2010, 2016, Oracle and/or its affiliates. All rights reserved.
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
This file contains the copy database utility which ensures a database
is exactly the same among two servers.
"""

import multiprocessing
import os
import re
import sys
import time

from mysql.utilities.common.tools import check_python_version
from mysql.utilities.exception import FormatError, UtilError
from mysql.utilities.command import dbcopy
from mysql.utilities.common.ip_parser import parse_connection
from mysql.utilities.common.messages import (PARSE_ERR_DB_PAIR,
                                             PARSE_ERR_DB_PAIR_EXT)
from mysql.utilities.common.my_print_defaults import MyDefaultsReader
from mysql.utilities.common.options import (add_skip_options, add_verbosity,
                                            check_verbosity, check_rpl_options,
                                            check_skip_options, add_engines,
                                            add_all, check_all, add_locking,
                                            add_regexp, add_rpl_mode,
                                            add_rpl_user, add_ssl_options,
                                            get_ssl_dict, setup_common_options,
                                            add_character_set_option,
                                            check_password_security,
                                            add_exclude, check_exclude_pattern)
from mysql.utilities.common.server import connect_servers
from mysql.utilities.common.sql_transform import (is_quoted_with_backticks,
                                                  remove_backtick_quoting)
from mysql.utilities.common.tools import (check_connector_python,
                                          print_elapsed_time)

# Check Python version compatibility
check_python_version()

# Constants
NAME = "MySQL Utilities - mysqldbcopy "
DESCRIPTION = "mysqldbcopy - copy databases from one server to another"
USAGE = "%prog --source=user:pass@host:port:socket " \
        "--destination=user:pass@host:port:socket orig_db:new_db"

# Check for connector/python
if not check_connector_python():
    sys.exit(1)

if __name__ == '__main__':
    # Needed for freeze support to avoid RuntimeError when running as a Windows
    # executable, otherwise ignored.
    multiprocessing.freeze_support()

    # Setup the command parser
    parser = setup_common_options(os.path.basename(sys.argv[0]),
                                  DESCRIPTION, USAGE, True, False)

    # Setup utility-specific options:

    # Connection information for the source server
    parser.add_option("--source", action="store", dest="source",
                      type="string", default="root@localhost:3306",
                      help="connection information for source server in the "
                      "form: <user>[:<password>]@<host>[:<port>][:<socket>]"
                      " or <login-path>[:<port>][:<socket>]"
                      " or <config-path>[<[group]>].")

    # Connection information for the destination server
    parser.add_option("--destination", action="store", dest="destination",
                      type="string",
                      help="connection information for destination server in "
                      "the form: <user>[:<password>]@<host>[:<port>]"
                      "[:<socket>] or <login-path>[:<port>][:<socket>]"
                      " or <config-path>[<[group]>].")

    # Add character set option
    add_character_set_option(parser)

    # Overwrite mode
    parser.add_option("-d", "--drop-first", action="store_true", default=False,
                      help="drop the new database or object if it exists",
                      dest="do_drop")

    # Add the exclude database option
    add_exclude(parser)

    # Add the all database options
    add_all(parser, "databases")

    # Add the skip common options
    add_skip_options(parser)

    # Add verbosity and quiet (silent) mode
    add_verbosity(parser, True)

    # Add engine options
    add_engines(parser)

    # Add locking options
    add_locking(parser)

    # Add regexp
    add_regexp(parser)

    # Replication user and password
    add_rpl_user(parser)

    # Add replication options but don't include 'both'
    add_rpl_mode(parser, False, False)

    # Add ssl options
    add_ssl_options(parser)

    # Add option to skip GTID generation
    parser.add_option("--skip-gtid", action="store_true", default=False,
                      dest="skip_gtid", help="skip creation and execution of "
                      "GTID statements during copy.")

    # Add multiprocessing option.
    parser.add_option("--multiprocess", action="store", dest="multiprocess",
                      type="int", default="1", help="use multiprocessing, "
                      "number of processes to use for concurrent execution. "
                      "Special values: 0 (number of processes equal to the "
                      "CPUs detected) and 1 (default - no concurrency).")

    # Add override for blob not null test
    parser.add_option("--not-null-blobs", action="store_true",
                      dest="not_null_blobs", default=False,
                      help="Allow conversion of blob fields marked as NOT "
                      "NULL to NULL before copy then restore NOT NULL "
                      "after the copy. May cause indexes to be rebuilt if "
                      "the affected blob fields are used in indexes.")

    # Now we process the rest of the arguments.
    opt, args = parser.parse_args()

    # Check security settings
    check_password_security(opt, args)

    try:
        skips = check_skip_options(opt.skip_objects)
    except UtilError:
        _, err, _ = sys.exc_info()
        print("ERROR: {0}".format(err.errmsg))
        sys.exit(1)

    # Fail if no options listed.
    if opt.destination is None:
        parser.error("No destination server specified.")

    # Fail if no db arguments or all
    if len(args) == 0 and not opt.all:
        parser.error("You must specify at least one database to copy or "
                     "use the --all option to copy all databases.")

    # Fail if we have arguments and all databases option listed.
    check_all(parser, opt, args, "databases")

    # Warn if quiet and verbosity are both specified
    check_verbosity(opt)

    # Process --exclude values to remove unnecessary quotes (when used) in
    # order to avoid further matching issues.
    if opt.exclude:
        # Remove unnecessary outer quotes.
        exclude_list = [pattern.strip("'\"") for pattern in opt.exclude]
    else:
        exclude_list = opt.exclude

    # Check for regexp symbols
    check_exclude_pattern(exclude_list, opt.use_regexp)

    # Check multiprocessing options.
    if opt.multiprocess < 0:
        parser.error("Number of processes '{0}' must be greater or equal than "
                     "zero.".format(opt.multiprocess))
    num_cpu = multiprocessing.cpu_count()
    if opt.multiprocess > num_cpu and not opt.quiet:
        print("# WARNING: Number of processes '{0}' is greater than the "
              "number of CPUs '{1}'.".format(opt.multiprocess, num_cpu))

    # Warning for non-posix (windows) systems if too many process are used.
    num_db = len(args)
    if (os.name != 'posix' and num_db and opt.multiprocess > num_db and
            not opt.quiet):
        print("# WARNING: Number of processes '{0}' is greater than the "
              "number of databases to copy '{1}'.".format(opt.multiprocess,
                                                          num_db))

    # Set options for database operations.
    options = {
        "skip_tables": "tables" in skips,
        "skip_views": "views" in skips,
        "skip_triggers": "triggers" in skips,
        "skip_procs": "procedures" in skips,
        "skip_funcs": "functions" in skips,
        "skip_events": "events" in skips,
        "skip_grants": "grants" in skips,
        "skip_create": "create_db" in skips,
        "skip_data": "data" in skips,
        "do_drop": opt.do_drop,
        "verbose": opt.verbosity >= 1,
        "quiet": opt.quiet,
        "debug": opt.verbosity == 3,
        "exclude_patterns": exclude_list,
        "new_engine": opt.new_engine,
        "def_engine": opt.def_engine,
        "all": opt.all,
        "locking": opt.locking,
        "use_regexp": opt.use_regexp,
        "rpl_user": opt.rpl_user,
        "rpl_mode": opt.rpl_mode,
        "verbosity": opt.verbosity,
        "skip_gtid": opt.skip_gtid,
        "charset": opt.charset,
        "multiprocess": num_cpu if opt.multiprocess == 0 else opt.multiprocess,
        "before_alter": [],
        "after_alter": [],
    }

    options.update(get_ssl_dict(opt))

    # Parse source connection values
    try:
        # Create a basic configuration reader first for optimization purposes.
        # I.e., to avoid repeating the execution of some methods in further
        # parse_connection methods (like, searching my_print_defaults tool).
        config_reader = MyDefaultsReader(options, False)
        source_values = parse_connection(opt.source, config_reader, options)
    except FormatError:
        _, err, _ = sys.exc_info()
        parser.error("Source connection values invalid: {0}.".format(err))
    except UtilError:
        _, err, _ = sys.exc_info()
        parser.error("Source connection values invalid: "
                     "{0}.".format(err.errmsg))

    # Parse destination connection values
    try:
        dest_values = parse_connection(opt.destination, config_reader, options)
    except FormatError:
        _, err, _ = sys.exc_info()
        parser.error("Destination connection values invalid: "
                     "{0}.".format(err))
    except UtilError:
        _, err, _ = sys.exc_info()
        parser.error("Destination connection values invalid: "
                     "{0}.".format(err.errmsg))

    # Check to see if attempting to use --rpl on the same server
    if (opt.rpl_mode or opt.rpl_user) and source_values == dest_values:
        parser.error("You cannot use the --rpl option for copying on the "
                     "same server.")

    # Check replication options
    check_rpl_options(parser, opt)

    # Get the sql_mode set on source and destination server
    conn_opts = {
        'quiet': True,
        'version': "5.1.30",
    }
    servers = None
    try:
        servers = connect_servers(source_values, dest_values, conn_opts)
        src_sql_mode = servers[0].select_variable("SQL_MODE")
        if servers[1] is not None:
            dest_sql_mode = servers[1].select_variable("SQL_MODE")
        else:
            dest_sql_mode = src_sql_mode
    except UtilError:
        # Set defaults in case of invalid connection values
        src_sql_mode = ''
        dest_sql_mode = ''

    # Form the regex to parse the database names
    db_name_regex = r'(`(?:[^`]|``)+`|\w+)'
    db_name_regex_aq = r'("(?:[^"]|"")+"|\w+)'
    arg_regex_src = db_name_regex
    if "ANSI_QUOTES" in src_sql_mode:
        arg_regex_src = db_name_regex_aq

    arg_regex_dest = db_name_regex
    if "ANSI_QUOTES" in dest_sql_mode:
        arg_regex_dest = db_name_regex_aq

    arg_regexp = re.compile(r"{0}(?:(?::){1})?".format(arg_regex_src,
                                                       arg_regex_dest))

    # Build list of databases to copy
    db_list = []
    for db in args:
        # Split the database names considering backtick quotes
        grp = arg_regexp.match(db)
        if not grp:
            parser.error(PARSE_ERR_DB_PAIR.format(db_pair=db,
                                                  db1_label='orig_db',
                                                  db2_label='new_db'))
        db_entry = grp.groups()
        orig_db, new_db = db_entry

        # Verify if the size of the databases matched by the REGEX is equal to
        # the initial specified string. In general, this identifies the missing
        # use of backticks.
        matched_size = len(orig_db)
        if new_db:
            # add 1 for the separator ':'
            matched_size += 1
            matched_size += len(new_db)
        if matched_size != len(db):
            parser.error(PARSE_ERR_DB_PAIR_EXT.format(db_pair=db,
                                                      db1_label='orig_db',
                                                      db2_label='new_db',
                                                      db1_value=orig_db,
                                                      db2_value=new_db))

        # Remove backtick quotes (handled later)
        orig_db = remove_backtick_quoting(orig_db, src_sql_mode) \
            if is_quoted_with_backticks(orig_db, src_sql_mode) else orig_db
        new_db = remove_backtick_quoting(new_db, dest_sql_mode) \
            if new_db and is_quoted_with_backticks(new_db, dest_sql_mode) \
            else new_db
        db_entry = (orig_db, new_db)
        db_list.append(db_entry)

    # Check databases for blob fields set to NOT NULL
    before_alter = []
    after_alter = []
    not_null_blob_cols = None
    if servers:
        not_null_blob_cols = dbcopy.check_blobs_not_null(servers[0], db_list,
                                                         opt.not_null_blobs)
    if servers and not_null_blob_cols:
        if not opt.not_null_blobs:
            sys.exit(1)
        # if --not-null-blobs, get the ALTER statements to execute before
        # the copy and after the copy
        alter_stmts = []
        for col in not_null_blob_cols:
            stmts = dbcopy.get_alter_table_col_not_null(servers[0], col[0],
                                                        col[3], col[1],
                                                        col[2])
            if stmts:
                before_alter.append(stmts[0])
                after_alter.append(stmts[1])
        options["before_alter"] = before_alter
        options["after_alter"] = after_alter

    try:
        # Record start time.
        if opt.verbosity >= 3:
            start_copy_time = time.time()

        # Copy databases concurrently for non posix systems (windows).
        if options['multiprocess'] > 1 and os.name != 'posix':
            # Create copy databases tasks.
            copy_db_tasks = []
            for db in db_list:
                copy_task = {
                    'source_srv': source_values,
                    'dest_srv': dest_values,
                    'db_list': [db],
                    'options': options
                }
                copy_db_tasks.append(copy_task)

            # Create process pool.
            workers_pool = multiprocessing.Pool(
                processes=options['multiprocess']
            )

            # Concurrently copy databases.
            workers_pool.map_async(dbcopy.multiprocess_db_copy_task,
                                   copy_db_tasks)
            workers_pool.close()
            workers_pool.join()
        else:
            # Copy all specified databases (no database level concurrency).
            # Note: on POSIX systems multiprocessing is applied at the object
            # level (not database).
            dbcopy.copy_db(source_values, dest_values, db_list, options)

        # Print elapsed time.
        if opt.verbosity >= 3:
            print_elapsed_time(start_copy_time)
    except UtilError:
        _, err, _ = sys.exc_info()
        print("ERROR: {0}".format(err.errmsg))
        sys.exit(1)

    sys.exit()
