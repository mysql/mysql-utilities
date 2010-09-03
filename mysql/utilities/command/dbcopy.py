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
This file contains the copy database operation which ensures a database
is exactly the same among two servers.
""" 

import sys
import MySQLdb
from mysql.utilities.common import MySQLUtilError

def _check_user_permissions(server, uname, host, access):
    """ Check user permissions for a given privilege

    server[in]         Server object to query
    uname[in]          user name to check
    host[in]           host name of connection
    acess[in]          privilege to check (e.g. "SELECT")
    
    Returns True if user has permission, False if not
    """
    
    from mysql.utilities.common import User
    
    result = True    
    user = User(server, uname+'@'+host)
    result = user.has_privilege(access[0], '*', access[1])
    return result


def _check_access(source, destination, s_user, s_host, d_user, d_host,
                  db, cloning, skip_views, skip_proc, skip_func, skip_grants):
    """ Check access levels for source and destination
    
    This method will check the user's permission levels for copying a
    database from the source and creating it on the destination server.
    It will also skip specific checks if certain objects are not being
    copied (i.e., views, procs, funcs, grants).

    source[in]         source server object to query
    destination[in]    destination server object to query
    s_user[in]         source user name to check
    s_host[in]         source host name of connection
    d_user[in]         destination user name to check
    d_host[in]         destination host name of connection
    db[in]             database
    cloning[in]        True if source == destination
    skip_views[in]     True = no views processed
    skup_proc[in]      True = no procedures processed
    skip_func[in]      True = no functions processed
    skip_grants[in]    True = no grants processed
    
    Returns tuple (bool, msg) where (True, None) = user has permissions and
                  (False, Message) = user does not have permission and
                  Message includes a context error message
    """

    # Build minimal list of privileges for source access    
    source_privs = []
    priv_tuple = (db[0], "SELECT")
    source_privs.append(priv_tuple)
    # if views are included, we need SHOW VIEW
    if not skip_views:
        priv_tuple = (db[0], "SHOW VIEW")
        source_privs.append(priv_tuple)
    # if procs or funcs are included, we need read on mysql db
    if not skip_proc or not skip_func:
        priv_tuple = ("mysql", "SELECT")
        source_privs.append(priv_tuple)
    
    # Check permissions on source
    for priv in source_privs:
        if not _check_user_permissions(source, s_user, s_host, priv):
            raise MySQLUtilError("User %s on the source server does not have "
                                 "permissions to read all objects in %s. " %
                                 (s_user, db) + "User needs %s privilege "
                                 "on %s." % (priv[1], priv[0]))
        
    # Build minimal list of privileges for destination access
    if cloning:
        server = source
        user = s_user
        host = s_host
    else:
        server = destination
        user = d_user
        host = d_host

    dest_privs = [(db[1], "CREATE"),
                  (db[1], "SUPER"),
                  ("*", "SUPER")]
    if not skip_grants:
        priv_tuple = (db[1], "WITH GRANT OPTION")
        dest_privs.append(priv_tuple)
        
    # Check privileges on destination
    for priv in dest_privs:
        if not _check_user_permissions(server, user, host, priv):
            raise MySQLUtilError("User %s on the destination server does not "
                                 "have permissions to create all objects "
                                 "in %s. User needs %s privilege on %s." %
                                 (user, priv[0], priv[1], priv[0]))
            
    return (True, None)


def copy_db(src_val, dest_val, db_list, options):
    """ Copy a database
    
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
                       skip_data, copy_dir, verbose, force, and silent)

    Notes:
        copy_dir - a directory to use for temporary files (default is None)
        force    - if True, the database on the destination will be dropped
                   if it exists (default is False)
        silent   - do not print any information during operation 
                   (default is False)
                       
    Returns bool True = success, False = error
    """
    
    from mysql.utilities.common import Database
    from mysql.utilities.common import connect_servers

    try:
        servers = connect_servers(src_val, dest_val, options["silent"])
        #print servers
    except MySQLUtilError, e:
        raise e

    source = servers[0]
    destination = servers[1]

    cloning = (src_val == dest_val) or dest_val is None
                            
    # Check user permissions on source and destination for all databases
    for db_name in db_list:
        try:
            result = _check_access(source, destination, src_val["user"],
                                   src_val["host"], dest_val["user"],
                                   dest_val["host"], db_name, cloning,
                                   options["skip_views"],
                                   options["skip_procs"],
                                   options["skip_funcs"],
                                   options["skip_grants"])
        except MySQLUtilError, e:
            raise e
            
    for db_name in db_list:

        # Error is source db and destination db are the same and we're cloning
        if destination is None and db_name[0] == db_name[1]:
            raise MySQLUtilError("Destination database name is same as "
                                 "source - source = %s, destinion = %s" %
                                 (db_name[0], db_name[1]))
    
        # Display copy message
        if not options["silent"]:
            msg = "# Copying database %s " % db_name[0]
            if db_name[1]:
                msg += "renamed as %s" % (db_name[1])
            print msg
        
        # Get a Database class instance
        db = Database(source, db_name[0], options)
        
        # Error is source database does not exist
        if not db.exists():
            raise MySQLUtilError("Source database does not exist - %s" %
                                 db_name[0])

        # Perform the copy
        db.init()
        try:
            db.copy(db_name[1], None, options, destination)
        except MySQLUtilError, e:
            raise e
            
    if not options["silent"]:
        print "#...done."
    return True
