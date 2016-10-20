#
# Copyright (c) 2011, 2016, Oracle and/or its affiliates. All rights reserved.
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

from mysql.utilities.exception import UtilDBError
from mysql.utilities.common.pattern_matching import parse_object_name
from mysql.utilities.common.database import Database
from mysql.utilities.common.dbcompare import (diff_objects, get_common_objects,
                                              server_connect)
from mysql.utilities.common.sql_transform import (is_quoted_with_backticks,
                                                  quote_with_backticks)


def object_diff(server1_val, server2_val, object1, object2, options,
                object_type=None):
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
    object_type[in]    type of the objects to be compared (e.g., TABLE,
                       PROCEDURE, etc.). By default None (not defined).

    Returns None = objects are the same, diff[] = tables differ
    """
    server1, server2 = server_connect(server1_val, server2_val,
                                      object1, object2, options)

    force = options.get("force", None)
    # Get the object type if unknown considering that objects of different
    # types can be found with the same name.
    if not object_type:
        # Get object types of object1
        sql_mode = server1.select_variable("SQL_MODE")
        db_name, obj_name = parse_object_name(object1, sql_mode)
        db = Database(server1, db_name, options)
        obj1_types = db.get_object_type(obj_name)
        if not obj1_types:
            msg = "The object {0} does not exist.".format(object1)
            if not force:
                raise UtilDBError(msg)
            print("ERROR: {0}".format(msg))
            return []

        # Get object types of object2
        sql_mode = server2.select_variable("SQL_MODE")
        db_name, obj_name = parse_object_name(object2, sql_mode)
        db = Database(server2, db_name, options)
        obj2_types = db.get_object_type(obj_name)
        if not obj2_types:
            msg = "The object {0} does not exist.".format(object2)
            if not force:
                raise UtilDBError(msg)
            print("ERROR: {0}".format(msg))
            return []

        # Merge types found for both objects
        obj_types = set(obj1_types + obj2_types)

        # Diff objects considering all types found
        result = []
        for obj_type in obj_types:
            res = diff_objects(server1, server2, object1, object2, options,
                               obj_type)
            if res:
                result.append(res)
        return result if len(result) > 0 else None
    else:
        # Diff objects of known type
        return diff_objects(server1, server2, object1, object2, options,
                            object_type)


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
    force = options.get("force", False)

    server1, server2 = server_connect(server1_val, server2_val,
                                      db1, db2, options)
    in_both, in_db1, in_db2 = get_common_objects(server1, server2,
                                                 db1, db2, True, options)
    in_both.sort()
    if (len(in_db1) > 0 or len(in_db2) > 0) and not force:
        return False

    # Get sql_mode value set on servers
    server1_sql_mode = server1.select_variable("SQL_MODE")
    server2_sql_mode = server2.select_variable("SQL_MODE")

    # Quote database names with backticks.
    q_db1 = db1 if is_quoted_with_backticks(db1, server1_sql_mode) \
        else quote_with_backticks(db1, server1_sql_mode)
    q_db2 = db2 if is_quoted_with_backticks(db2, server2_sql_mode) \
        else quote_with_backticks(db2, server2_sql_mode)

    # Do the diff for the databases themselves
    result = object_diff(server1, server2, q_db1, q_db2, options, 'DATABASE')
    if result is not None:
        success = False
        if not force:
            return False

    # For each that match, do object diff
    success = True
    for item in in_both:
        # Quote object name with backticks with sql_mode from server1
        q_obj_name1 = item[1][0] if \
            is_quoted_with_backticks(item[1][0], server1_sql_mode) \
            else quote_with_backticks(item[1][0], server1_sql_mode)
        # Quote object name with backticks with sql_mode from server2
        q_obj_name2 = item[1][0] if \
            is_quoted_with_backticks(item[1][0], server2_sql_mode) \
            else quote_with_backticks(item[1][0], server2_sql_mode)
        object1 = "{0}.{1}".format(q_db1, q_obj_name1)
        object2 = "{0}.{1}".format(q_db2, q_obj_name2)
        result = object_diff(server1, server2, object1, object2, options,
                             item[0])
        if result is not None:
            success = False
            if not force:
                return False

    return success
