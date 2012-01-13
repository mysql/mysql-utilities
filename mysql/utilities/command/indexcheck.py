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
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301 USA
#

"""
This file contains the check index utility. It is used to check for
duplicate or redundant indexes for a list of database (operates on
all tables in each database), a list of tables in the for db.table,
or all tables in all databases except internal databases.
"""

from mysql.utilities.exception import UtilError

def check_index(src_val, table_args, options):
    """Check for duplicate or redundant indexes for one or more tables
    
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
                         verbosity    : print extra information
                         show-indexes : show all indexes for each table
                         index-format : index format = sql, table, tab, csv
                         worst        : show worst performing indexes
                         best         : show best performing indexes
    
    Returns bool True = success, raises UtilError if error
    """
    
    # Get options
    show_drops = options.get("show-drops", False)
    skip = options.get("skip", False)
    verbosity = options.get("verbosity", False)
    show_indexes = options.get("show-indexes", False)
    index_format = options.get("index-format", False)
    stats = options.get("stats", False)
    first_indexes = options.get("best", None)        
    last_indexes = options.get("worst", None)

    from mysql.utilities.common.server import connect_servers
    from mysql.utilities.common.database import Database
    from mysql.utilities.common.table import Table

    # Try to connect to the MySQL database server.
    conn_options = {
        'quiet'     : verbosity == 1,
        'version'   : "5.0.0",
    }
    servers = connect_servers(src_val, None, conn_options)

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
        db_source = Database(source, db)
        db_source.init()
        tables = db_source.get_db_objects("TABLE")
        if not tables and verbosity >= 1:
            print "# Warning: database %s does not exist. Skipping." % (db)
        for table in tables:
            table_list.append(db + "." + table[0])

    # Fail if no tables to check
    if not table_list:
        raise UtilError("No tables to check.")

    if verbosity > 1:
        print "# Checking indexes..."
    # Check indexes for each table in the list
    for table_name in table_list:
        tbl_options = {
            'verbose'  : verbosity >= 1,
            'get_cols' : False,
            'quiet'    : verbosity is None or verbosity < 1
        }
        tbl = Table(source, table_name, tbl_options)
        exists = tbl.exists()
        if not exists and not skip:
            raise UtilError("Table %s does not exist. Use --skip "
                                 "to skip missing tables." % table_name)
        if exists:
            if not tbl.get_indexes():
                if verbosity > 1:
                    print "# Table %s is not indexed." % (table_name)
            else:
                if show_indexes:
                    tbl.print_indexes(index_format)
                    # Show if table has primary key
                if not tbl.has_primary_key():
                    if verbosity > 1:
                        print "#   Table %s does not contain a PRIMARY key."
                tbl.check_indexes(show_drops)
                
            # Show best and/or worst indexes
            if stats:
                if first_indexes is not None:
                    tbl.show_special_indexes(index_format, first_indexes, True)
                if last_indexes is not None:
                    tbl.show_special_indexes(index_format, last_indexes)
                
        if verbosity > 1:
            print "#"

    if verbosity > 1:    
        print "# ...done."
    
