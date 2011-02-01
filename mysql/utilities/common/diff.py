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
This file contains the diff methods for finding the differences among
the definitions of two objects.
"""

from mysql.utilities.common.options import parse_connection
from mysql.utilities.exception import MySQLUtilError

def _get_object_create(server, object_name, options):
    """Get the object's create statement.
    
    server[in]        Server connection
    object_name[in]   Name of object in the form db.objectname
    options[in]       Options: verbosity
    
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


def get_diff(server1, server2, object1, object2, options):
    """diff the definition of two objects
    
    Produce a diff in the form unified, context, or ndiff of two objects.
    Note: objects must exist else exception is thrown.
    
    server1[in]        first server connection
    server2[in]        second server connection
    object1            the first object in the compare in the form: (db.name)
    object2            the second object in the compare in the form: (db.name)
    options[in]        a dictionary containing the options for the operation:
                       (quiet, verbosity, difftype, width)

    Returns tuple (True, None) = objects are the same,
                  (False, diff[]) = objects differ
    """
    import difflib
    import sys
               
    quiet = options.get("quiet", False)
    verbosity = options.get("verbosity", 0)
    difftype = options.get("difftype", "unified")
    width = options.get("width", 75)

    try:
        object1_create = _get_object_create(server1, object1, options)
    except MySQLUtilError, e:
        raise e
    
    try:
        object2_create = _get_object_create(server2, object2, options)
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
        return (False, diff_str)
    
    if not quiet:
        print "[PASS]"

    return (True, None)
