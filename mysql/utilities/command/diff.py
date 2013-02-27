#
# Copyright (c) 2011, 2013, Oracle and/or its affiliates. All rights reserved.
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
This file contains the diff commands for finding the difference among
the definitions of two databases.
"""

from mysql.utilities.common.sql_transform import is_quoted_with_backticks
from mysql.utilities.common.sql_transform import quote_with_backticks


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

    Returns None = objects are the same, diff[] = tables differ
    """
    from mysql.utilities.common.dbcompare import diff_objects, server_connect

    server1, server2 = server_connect(server1_val, server2_val,
                                      object1, object2, options)
    result = diff_objects(server1, server2, object1, object2, options)
    
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
    from mysql.utilities.common.dbcompare import get_common_objects
    from mysql.utilities.common.dbcompare import server_connect
    
    force = options.get("force", False)

    server1, server2 = server_connect(server1_val, server2_val,
                                      db1, db2, options)
    in_both, in_db1, in_db2 = get_common_objects(server1, server2,
                                                 db1, db2, True, options)
    in_both.sort()
    if (len(in_db1) > 0 or len(in_db2) > 0) and not force:
        return False
    
    # Do the diff for the databases themselves
    result = object_diff(server1, server2, db1, db2, options)
    if result is not None:
        success = False
        if not force:
            return False

    # For each that match, do object diff
    success = True
    for item in in_both:
        obj_name1 = quote_with_backticks(item[1][0]) \
                        if is_quoted_with_backticks(db1) else item[1][0]
        obj_name2 = quote_with_backticks(item[1][0]) \
                        if is_quoted_with_backticks(db2) else item[1][0]
        object1 = "%s.%s" % (db1, obj_name1)
        object2 = "%s.%s" % (db2, obj_name2)
        result = object_diff(server1, server2, object1, object2, options)
        if result is not None:
            success = False
            if not force:
                return False

    return success    
