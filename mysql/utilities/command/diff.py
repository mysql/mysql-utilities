#!/usr/bin/env python
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
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307 USA
#

"""
This file contains the diff commands for finding the difference among
the definitions of two databases.
"""

from mysql.utilities.common.options import parse_connection
from mysql.utilities.exception import MySQLUtilError

def _get_connections(server1_val, server2_val, options):
    """Connect to the servers presented.
    
    This method attempts to connect to the servers based on the connection
    value dictionaries passed. If server2 is missing, server1's connection
    is used instead.
    
    server1_val[in]    a dictionary containing connection information for the
                       first server including:
                       (user, password, host, port, socket)
    server2_val[in]    a dictionary containing connection information for the
                       second server including:
                       (user, password, host, port, socket)
    options[in]        a dictionary containing the options for the operation:
                       (quiet, verbosity, difftype)
    
    Returns tuple (server1, server2) or raises error on failure
    """
    from mysql.utilities.common.server import connect_servers
    from mysql.utilities.common.server import Server

    quiet = options.get("quiet", False)

    server1 = None
    server2 = None
    if type(server1_val) == type({}): 
        try:
            servers = connect_servers(server1_val, server2_val, quiet, "5.1.30",
                                      "server1", "server2")
        except MySQLUtilError, e:
            raise e
        server1 = servers[0]
        server2 = servers[1]
    elif type(server1_val) != Server:
        raise MySQLUtilError("Cannot determine type of parameter.")
    else:
        server1 = server1_val
        server2 = server2_val
    
    if server2 is None:
        server2 = server1

    return (server1, server2)


def object_diff(server1_val, server2_val, object1, object2, options):
    """diff the definition of two objects
    
    Find the difference among two object definitions.
    
    server1_val[in]    a dictionary containing connection information for the
                       first server including:
                       (user, password, host, port, socket)
    server2_val[in]    a dictionary containing connection information for the
                       second server including:
                       (user, password, host, port, socket)
    object1[in]        the first object in the compare in the form: (db.name)
    object2[in]        the second object in the compare in the form: (db.name)
    options[in]        a dictionary containing the options for the operation:
                       (quiet, verbosity, difftype)

    Returns tuple (True, None) = tables are the same,
                  (False, diff[]) = tables differ
    """
    from mysql.utilities.common.diff import get_diff

    quiet = options.get("quiet", False)
    verbosity = options.get("verbosity", 0)

    try:
        server1, server2 = _get_connections(server1_val, server2_val, options)
    except MySQLUtilError, e:
        raise e
 
    if server1 == server2 and object1 == object2:
        raise MySQLUtilError("Comparing the same object on the same server.")

    try:
        result = get_diff(server1, server2, object1, object2, options)
    except MySQLUtilError, e:
        raise e
    
    return result


def database_diff(server1_val, server2_val, db1, db2, options):
    """Find differences among objects from two databases.
    
    This method compares the object definitions among two databases. If any
    differences are found, the differences are printed in the format chosen
    and the method returns False. A True result is returned only when all
    object definitions match.
    
    The method will stop and return False on the first difference found unless
    the option force is set to True (default = False).
    
    server1_val[in]    a dictionary containing connection information for the
                       first server including:
                       (user, password, host, port, socket)
    server2_val[in]    a dictionary containing connection information for the
                       second server including:
                       (user, password, host, port, socket)
    db1[in]            the first database in the compare
    db2[in]            the second database in the compare
    options[in]        a dictionary containing the options for the operation:
                       (quiet, verbosity, difftype, force)

    Returns bool True if all object match, False if partial match
    """
    
    def _get_objects(server, database, options):
        from mysql.utilities.common.database import Database

        db_obj = Database(server, database, options)
        if not db_obj.exists():
            raise MySQLUtilError("The database does not exist: %s" % database)
        db_obj.init()
        db_objects = []
        for item in db_obj.get_next_object():
            db_objects.append(item)
        db_objects.sort()
        
        return db_objects
    
    def _print_list(item_list, first, second):
        if len(in_db1_not_db2) > 0:
            print "WARNING: Objects in %s but not in %s:" % (first, second)
            for item in item_list:
                print "  %s: %s" % (item[0], item[1][0])
            return True
        return False
        
    from mysql.utilities.common.diff import get_diff

    quiet = options.get("quiet", False)
    verbosity = options.get("verbosity", 0)
    force = options.get("force", False)
    options["skip_grants"] = True   # Tell db class to skip grants

    try:
        server1, server2 = _get_connections(server1_val, server2_val, options)
    except MySQLUtilError, e:
        raise e

    # Get list of all items in db1 and db2
    try:
        db = db1
        db1_objects = _get_objects(server1, db1, options)
        db = db2
        db2_objects = _get_objects(server2, db2, options)
    except MySQLUtilError, e:
        raise e
        
    # Compare lists
    in_db1_not_db2 = list(set(db1_objects)-set(db2_objects))
    in_db2_not_db1 = list(set(db2_objects)-set(db1_objects))
    in_both = list(set(db1_objects)-set(in_db1_not_db2))
    in_both.sort()
    diff_list1 = _print_list(in_db1_not_db2,
                             "server1:%s" % db1,
                             "server2:%s" % db2) 
    diff_list2 = _print_list(in_db2_not_db1,
                             "server2:%s" % db2,
                             "server1:%s" % db1)
    if (diff_list1 or diff_list2) and not force:
        return True
    
    # For each that match, do object diff
    success = True
    for item in in_both:
        object1 = "%s.%s" % (db1, item[1][0])
        object2 = "%s.%s" % (db2, item[1][0])
        try:
            result = object_diff(server1, server2, object1, object2, options)
        except MySQLUtilError, e:
            raise e
        if result[0] == False:
            success = False
            if not force:
                return False

    return success    
