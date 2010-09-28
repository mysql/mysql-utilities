#!/usr/bin/env python
#
# Copyright (c) 2010, Oracle and/or its affiliates. All rights reserved.
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
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307 USA
#

"""
This file contains the check index utility. It is used to check for
duplicate or redundant indexes for a list of database (operates on
all tables in each database), a list of tables in the for db.table,
or all tables in all databases except internal databases.
"""

import MySQLdb
from mysql.utilities.common import MySQLUtilError

def check_index(src_val, table_args, options):
    """ Check for duplicate or redundant indexes for one or more tables
    
    This method will examine the indexes for one or more tables and identify
    any indexes that are potential duplicates or redundant. It prints the
    equivalent DROP statements if selected.
    
    src_val[in]        a dictionary containing connection information for the
                       source including:
                       (user, password, host, port, socket)
    table_args[in]     list of tables in the form 'db.table' or 'db'
    options[in]        dictionary of options to include:
                         show-drops   : show drop statements for dupe indexes
                         skip         : skip non-existant tables
                         verbose      : print extra information
                         show-indexes : show all indexes for each table
                         index-format : index format = SQL, TABLE, TAB, CSV
                         silent       : do not print informational messages
                         worst        : show worst performing indexes
                         best         : show best performing indexes
    
    Returns bool True = success, raises MySQLUtilError if error
    """
    
    # Get options
    show_drops = options["show-drops"]
    skip = options["skip"]
    verbose = options["verbose"]
    show_indexes = options["show-indexes"]
    index_format = options["index-format"]
    silent = options["silent"]
    stats = False
    if "stats" in options:
        stats = options["stats"]
    first_indexes = None
    if "first" in options:
        first_indexes = options["first"]        
    last_indexes = None
    if "last" in options:
        last_indexes = options["last"]

    from mysql.utilities.common import connect_servers
    from mysql.utilities.common import Table

    # Try to connect to the MySQL database server.
    try:
        servers = connect_servers(src_val, None, silent, "5.0.0")
    except MySQLUtilError, e:
        raise e

    source = servers[0]

    db_list = []     # list of databases
    table_list = []  # list of all tables to process
    
    # Build a list of objects to process
    # 1. start with db_list if no obects present on command line
    # 2. process command line options.
    # 3. loop through database list and add all tables
    # 4. check indexes
        
    # Perform the options check here. Loop through objects presented.
    for obj in table_args:
        # If a . appears, we are operating on a specific table
        idx = obj.count(".")
        if (idx == 1):
            table_list.append(obj)
        # Else we are operating on a specific database.
        else:
            db_list.append(obj)
    
    # Loop through database list adding tables
    for db in db_list:
        tables = source.get_db_objects(db, "TABLE")
        if not tables and verbose:
            print "# Warning: database %s does not exist. Skipping." % (db)
        for table in tables:
            table_list.append(db + "." + table[0])
    
    # Fail if no tables to check
    if not table_list:
        raise MySQLUtilError("No tables to check.")

    if not silent:
        print "# Checking indexes..."
    # Check indexes for each table in the list
    for table_name in table_list:
        tbl = Table(source, table_name, verbose)
        exists = tbl.exists()
        if not exists and not skip:
            raise MySQLUtilError("Table %s does not exist. Use --skip "
                                 "to skip missing tables." % table_name)
        if exists:
            if not tbl.get_indexes():
                if not silent:
                    print "# Table %s is not indexed." % (table_name)
            else:
                if show_indexes:
                    tbl.print_indexes(index_format)
                    # Show if table has primary key
                if not tbl.has_primary_key():
                    if not silent:
                        print "#   Table %s does not contain a PRIMARY key."
                tbl.check_indexes(show_drops, silent)
                
            # Show best and/or worst indexes
            if stats:
                if first_indexes is not None:
                    tbl.show_special_indexes(index_format, first_indexes, True)
                if last_indexes is not None:
                    tbl.show_special_indexes(index_format, last_indexes)
                
        if not silent:
            print "#"

    if not silent:    
        print "# ...done."
    
