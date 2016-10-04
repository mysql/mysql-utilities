#
# Copyright (c) 2014, 2016, Oracle and/or its affiliates. All rights reserved.
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
This file contains the commands to show the grantees and respective grants
over a set of objects.

"""
from collections import defaultdict
from mysql.utilities.common.database import Database
from mysql.utilities.common.grants_info import (DATABASE_TYPE, ROUTINE_TYPE,
                                                TABLE_TYPE, get_grantees,
                                                filter_grants, DATABASE_LEVEL,
                                                OBJECT_LEVEL, GLOBAL_LEVEL)
from mysql.utilities.common.messages import ERROR_USER_WITHOUT_PRIVILEGES
from mysql.utilities.common.server import connect_servers
from mysql.utilities.common.sql_transform import (is_quoted_with_backticks,
                                                  quote_with_backticks)
from mysql.utilities.common.tools import join_and_build_str
from mysql.utilities.common.user import User
from mysql.utilities.exception import UtilError


def _check_privileges(server):
    """Verify required privileges to check grantee privileges.

    server[in]    Instance of Server class.

    This method checks if the used User for the server possesses
    the required privileges get the list of grantees and respective grants
    for the objects.
    Specifically, the following privilege is required: SELECT on mysql.*
    An exception is thrown if the user doesn't have this privilege.
    """

    user_obj = User(server, "{0}@{1}".format(server.user, server.host))
    has_privilege = user_obj.has_privilege('mysql', '*', 'SELECT')
    if not has_privilege:
        raise UtilError(ERROR_USER_WITHOUT_PRIVILEGES.format(
            user=server.user, host=server.host,
            port=server.port,
            operation='read the available grants',
            req_privileges="SELECT on mysql.*"
        ))


def validate_obj_type_dict(server, obj_type_dict):
    """Validates the dictionary of objects against the specified server

    This function builds a dict with the types of the objects in
    obj_type_dict, filtering out non existing databases and objects.

    Returns a dictionary with only the existing objects, using  object_types
    as keys and as values a list of tuples (<DB NAME>, <OBJ_NAME>).
    """
    valid_obj_dict = defaultdict(list)
    server_dbs = set(row[0] for row in
                     server.get_all_databases(
                         ignore_internal_dbs=False))
    argument_dbs = set(obj_type_dict.keys())

    # Get non existing_databases and dbs to check
    non_existing_dbs = argument_dbs.difference(server_dbs)
    dbs_to_check = server_dbs.intersection(argument_dbs)

    if non_existing_dbs:
        if len(non_existing_dbs) > 1:
            plurals = ('s', '', 'them')
        else:
            plurals = ('', 'es', 'it')
        print('# WARNING: specified database{0} do{1} not '
              'exist on base server and will be skipped along '
              'any tables and routines belonging to {2}: '
              '{3}.'.format(plurals[0], plurals[1], plurals[2],
                            ", ".join(non_existing_dbs)))

    # Get sql_mode value set on servers
    sql_mode = server.select_variable("SQL_MODE")

    # Now for each db that actually exists, get the type of the specified
    # objects
    for db_name in dbs_to_check:
        db = Database(server, db_name)
        # quote database name if necessary
        quoted_db_name = db_name
        if not is_quoted_with_backticks(db_name, sql_mode):
            quoted_db_name = quote_with_backticks(db_name, sql_mode)
        # if wilcard (db.*) is used add all supported objects of the database
        if '*' in obj_type_dict[db_name]:
            obj_type_dict[db_name] = obj_type_dict[db_name] - set('*')
            tables = (table[0] for table in db.get_db_objects('TABLE'))
            obj_type_dict[db_name] = obj_type_dict[db_name] | set(tables)
            procedures = (proc[0] for proc in db.get_db_objects('PROCEDURE'))
            obj_type_dict[db_name] = obj_type_dict[db_name] | set(procedures)
            functions = (proc[0] for proc in db.get_db_objects('FUNCTION'))
            obj_type_dict[db_name] = obj_type_dict[db_name] | set(functions)
        for obj_name in obj_type_dict[db_name]:
            if obj_name is None:
                # We must consider the database itself
                valid_obj_dict[DATABASE_TYPE].append((quoted_db_name,
                                                      quoted_db_name))
            else:
                # get quoted name for obj_name
                quoted_obj_name = obj_name
                if not is_quoted_with_backticks(obj_name, sql_mode):
                    quoted_obj_name = quote_with_backticks(obj_name, sql_mode)

                # Test if the object exists and if it does, test if it
                # is one of the supported object types, else
                # print a warning and skip the object
                obj_type = db.get_object_type(obj_name)
                if obj_type is None:
                    print("# WARNING: specified object does not exist. "
                          "{0}.{1} will be skipped."
                          "".format(quoted_db_name, quoted_obj_name))
                elif 'PROCEDURE' in obj_type or 'FUNCTION' in obj_type:
                    valid_obj_dict[ROUTINE_TYPE].append((quoted_db_name,
                                                         quoted_obj_name))
                elif 'TABLE' in obj_type:
                    valid_obj_dict[TABLE_TYPE].append((quoted_db_name,
                                                       quoted_obj_name))
                else:
                    print('# WARNING: specified object is not supported '
                          '(not a DATABASE, FUNCTION, PROCEDURE or TABLE),'
                          ' as such it will be skipped: {0}.{1}.'
                          ''.format(quoted_db_name, quoted_obj_name))
    return valid_obj_dict


def check_grants(server_cnx_val, options, dict_of_objects):
    """Show list of privileges over a set of objects

    This function creates a GrantShow object which shows the list of
    users with (the optionally specified list of ) privileges over the
    specified set of objects.

    server_cnx_val[in]      Dictionary with the connection values to the
                            server.
    options[in]             Dictionary of options (verbosity, privileges,
                            show_mode).
    dict_of_objects[in]     Dictionary of objects (set of databases, tables
                            and procedures) by database to check.

    """

    # Create server connection:
    server = connect_servers(server_cnx_val, None, options)[0]

    # Check user permissions to consult the grant information.
    _check_privileges(server)

    # Validate the dict of objects against our server.
    valid_dict_of_objects = validate_obj_type_dict(server, dict_of_objects)

    # Get optional list of required privileges
    req_privs = set(options['privileges']) if options['privileges'] else None

    # Get hide_inherit_grants option
    inherit_level_str = options['inherit_level'].lower()
    inherit_level = {"global": GLOBAL_LEVEL,
                     "database": DATABASE_LEVEL,
                     "object": OBJECT_LEVEL}[inherit_level_str]

    # If we specify some privileges that are not valid for all the objects
    # print warning message stating that some will be ignored.
    if req_privs:
        for obj_type in valid_dict_of_objects:
            # get list of privileges that applies to the object type
            filtered_req_privs = filter_grants(req_privs, obj_type)
            # if the size of the set is different that means that some of the
            # privileges cannot be applied to this object type, print warning
            if len(filtered_req_privs) != len(req_privs):
                if obj_type.upper() == DATABASE_TYPE:
                    obj_lst = [obj_tpl[0] for obj_tpl in
                               valid_dict_of_objects[obj_type]]
                else:
                    obj_lst = [".".join(obj_tpl) for obj_tpl in
                               valid_dict_of_objects[obj_type]]
                obj_lst_str = join_and_build_str(sorted(obj_lst))
                missing_privs = sorted(req_privs - filtered_req_privs)
                priv_str = join_and_build_str(missing_privs)
                verb = "do" if len(missing_privs) > 1 else "does"
                print("# WARNING: {0} {1} not apply to {2}s "
                      "and will be ignored for: {3}.".format(
                          priv_str, verb, obj_type.lower(), obj_lst_str))

    # get the grantee information dictionary
    grantee_info_dict = get_grantees(server, valid_dict_of_objects,
                                     req_privileges=req_privs,
                                     inherit_level=inherit_level)

    # Print the information
    obj_type_lst = [DATABASE_TYPE, TABLE_TYPE, ROUTINE_TYPE]
    # pylint: disable=R0101
    for obj_type in obj_type_lst:
        if obj_type in grantee_info_dict:
            # Sort by object name
            for obj_name in sorted(grantee_info_dict[obj_type]):
                print("\n# {0} {1}:".format(obj_type, obj_name))
                if options['show_mode'] == 'users':
                    # Sort by grantee name
                    output_str = ", ".join(
                        sorted(grantee_info_dict[obj_type][obj_name].keys()))
                    print("# - {0}".format(output_str))
                elif options['show_mode'] == 'user_grants':
                    # Sort by grantee name
                    for grantee, priv_set in sorted(
                            grantee_info_dict[obj_type][obj_name].iteritems()):
                        # print privileges sorted by name
                        print("# - {0} : {1}".format(
                            grantee, ", ".join(sorted(priv_set))))
                else:  # raw mode
                    # Sort by grantee name
                    for grantee in sorted(
                            grantee_info_dict[obj_type][obj_name].keys()):
                        user = User(server, grantee)
                        grant_stms = sorted(
                            user.get_grants_for_object(obj_name, obj_type))
                        if grant_stms:
                            print("# - For {0}".format(grantee))
                        for grant_stm in grant_stms:
                            print("{0}".format(grant_stm))
