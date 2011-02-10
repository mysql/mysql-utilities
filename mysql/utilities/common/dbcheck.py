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
This file contains the methods for checking consistency among two databases.
"""

from mysql.utilities.common.options import parse_connection
from mysql.utilities.exception import MySQLUtilError

def _get_objects(server, database, options):
    """Get all objects from the database (except grants)
    
    server[in]        connected server object
    database[in]      database names
    options[in]       global options
    
    Returns list - objects in database
    """
    from mysql.utilities.common.database import Database

    options["skip_grants"] = True   # Tell db class to skip grants

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
    """Print the list of items in the list.
    
    This method is used to display the list of objects that are missing
    from one of the databases in the compare.
    
    item_list[in]     list of items to print
    first[in]         name of first database
    second[in]        name of second database
    
    Returns bool True if items in the list, False if list is empty
    """
    if len(item_list) > 0:
        print "WARNING: Objects in %s but not in %s:" % (first, second)
        for item in item_list:
            print "  %s: %s" % (item[0], item[1][0])
        return True
    return False


def _get_create_object(server, object_name, options):
    """Get the object's create statement.
    
    server[in]        server connection
    object_name[in]   name of object in the form db.objectname
    options[in]       options: verbosity, quiet
    
    This method retrieves the object create statement from the database.
    
    Returns string : create statment or raise error if object or db not exist
    """
    from mysql.utilities.common.database import Database

    verbosity = options.get("verbosity", 0)
    quiet = options.get("quiet", False)

    object = object_name.split(".")
    
    db = Database(server, object[0], options)

    # Error if atabase does not exist
    if not db.exists():
        raise MySQLUtilError("The database does not exist: %s" % object[0])
    
    obj_type = db.get_object_type(object[1])
    
    if obj_type is None:
        raise MySQLUtilError("The object %s does not exist." % object_name)
        
    create_stmt = db.get_create_statement(object[0], object[1], obj_type)
    
    if verbosity > 0:
        print "\n# Definition for object %s:" % object_name
        print create_stmt 

    return create_stmt


def server_connect(server1_val, server2_val, object1, object2, options):
    """Connect to the servers
    
    This method connects to the servers and checks to see if the objects
    are different: db1.obj1 != db2.obj2 by name match.
    
    server1_val[in]    a dictionary containing connection information for the
                       first server including:
                       (user, password, host, port, socket)
    server2_val[in]    a dictionary containing connection information for the
                       second server including:
                       (user, password, host, port, socket)
    object1[in]        the first object in the compare
    object2[in]        the second object in the compare
    options[in]        a dictionary containing the options for the operation:
                       (quiet, verbosity)

    Returns tuple of Server objects (server1, server2)
    """
    from mysql.utilities.common.server import connect_servers

    quiet = options.get("quiet", False)
    verbosity = options.get("verbosity", 0)

    try:
        servers = connect_servers(server1_val, server2_val, quiet, "5.1.30",
                                  "server1", "server2")
    except MySQLUtilError, e:
        raise e
    server1 = servers[0]
    server2 = servers[1]
    if server2 is None:
        server2 = server1
 
    if server1 == server2 and object1 == object2:
        raise MySQLUtilError("Comparing the same object on the same server.")

    return (server1, server2)

def get_common_objects(server1, server2, db1, db2,
                       print_list=True, options={}):
    """Get a list of the common objects among two databases.
    
    server1[in]        first server connection
    server2[in]        second server connection
    object1[in]        the first object in the compare in the form: (db.name)
    object2[in]        the second object in the compare in the form: (db.name)
    print_list[in]     if True, print list of missing items
    options[in]        global options
   
    Returns (tuple) lists containing: items in both,
                                      items in db1 and not in db2,
                                      items in db2 not in db1
    """

    try:
        db1_objects = _get_objects(server1, db1, options)
        db2_objects = _get_objects(server2, db2, options)
    except MySQLUtilError, e:
        raise e
        
    # Compare lists
    in_db1_not_db2 = list(set(db1_objects)-set(db2_objects))
    in_db2_not_db1 = list(set(db2_objects)-set(db1_objects))
    in_both = list(set(db1_objects)-set(in_db1_not_db2))
    in_both.sort()
    if print_list:
        _print_list(in_db1_not_db2, "server1:%s" % db1, "server2:%s" % db2) 
        _print_list(in_db2_not_db1, "server2:%s" % db2, "server1:%s" % db1)
    
    return (in_both, in_db1_not_db2, in_db2_not_db1)


def diff_objects(server1, server2, object1, object2, options):
    """diff the definition of two objects
    
    Produce a diff in the form unified, context, or ndiff of two objects.
    Note: objects must exist else exception is thrown.
    
    server1[in]        first server connection
    server2[in]        second server connection
    object1            the first object in the compare in the form: (db.name)
    object2            the second object in the compare in the form: (db.name)
    options[in]        a dictionary containing the options for the operation:
                       (quiet, verbosity, difftype, width)

    Returns None = objects are the same, diff[] = objects differ
    """
    import difflib
    import sys
    
    quiet = options.get("quiet", False)
    verbosity = options.get("verbosity", 0)
    difftype = options.get("difftype", "unified")
    width = options.get("width", 75)

    try:
        object1_create = _get_create_object(server1, object1, options)
    except MySQLUtilError, e:
        raise e
    
    try:
        object2_create = _get_create_object(server2, object2, options)
    except MySQLUtilError, e:
        raise e

    if not quiet:
        msg = "# Comparing %s to %s " % (object1, object2)
        sys.stdout.write(msg)
        linelen = width - (len(msg) + 8)
        sys.stdout.write(' ' * linelen)

    diff_str = []
    if difftype == 'unified':
        for line in difflib.unified_diff(object1_create.split('\n'),
                                         object2_create.split('\n'),
                                         fromfile=object1, tofile=object2):
            diff_str.append(line.strip('\n'))
    elif difftype == 'context':
        for line in difflib.context_diff(object1_create.split('\n'),
                                         object2_create.split('\n'),
                                         fromfile=object1, tofile=object2):
            diff_str.append(line.strip('\n'))
    else:
        has_diff = False
        for line in difflib.ndiff(object1_create.split('\n'),
                                  object2_create.split('\n')):
            diff_str.append(line.strip('\n'))
            if line[0] in ['-', '+', '?']:
                has_diff = True
                
        if not has_diff:
            diff_str = []

    if len(diff_str) > 0:
        if not quiet:
            print "[FAIL]\n# Object definitions are not the same:"
            for line in diff_str:
                print line
        return diff_str
    
    if not quiet:
        print "[PASS]"

    return None
