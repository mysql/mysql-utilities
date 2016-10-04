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
This file contains features to check which users hold privileges, specific or
not, over a given object/list of objects.
"""

from collections import defaultdict

from mysql.utilities.common.sql_transform import (is_quoted_with_backticks,
                                                  remove_backtick_quoting)

_TABLE_PRIV_QUERY = ("SELECT GRANTEE, IS_GRANTABLE, "
                     "GROUP_CONCAT(PRIVILEGE_TYPE) "
                     "FROM INFORMATION_SCHEMA.TABLE_PRIVILEGES WHERE "
                     "TABLE_SCHEMA='{0}' AND TABLE_NAME='{1}' "
                     "GROUP BY GRANTEE, IS_GRANTABLE")

_DB_PRIVS_QUERY = ("SELECT GRANTEE, IS_GRANTABLE, "
                   "GROUP_CONCAT(PRIVILEGE_TYPE) "
                   "FROM INFORMATION_SCHEMA.SCHEMA_PRIVILEGES WHERE "
                   "TABLE_SCHEMA='{0}' GROUP BY GRANTEE, IS_GRANTABLE")

_GLOBAL_PRIV_QUERY = ("SELECT grantee, IS_GRANTABLE, "
                      "GROUP_CONCAT(privilege_type) FROM "
                      "information_schema.USER_PRIVILEGES GROUP BY GRANTEE,"
                      " IS_GRANTABLE")

_PROCS_PRIV_QUERY = ("SELECT User, Host, Proc_priv FROM "
                     "mysql.procs_priv WHERE db='{0}' AND "
                     "routine_name='{1}'")

_GLOBAL_ALL_PRIVS = set(['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'CREATE',
                         'DROP', 'RELOAD', 'SHUTDOWN', 'PROCESS', 'FILE',
                         'REFERENCES', 'INDEX', 'ALTER', 'SHOW DATABASES',
                         'SUPER', 'CREATE TEMPORARY TABLES', 'LOCK TABLES',
                         'EXECUTE', 'REPLICATION SLAVE', 'REPLICATION CLIENT',
                         'CREATE VIEW', 'SHOW VIEW', 'CREATE ROUTINE',
                         'ALTER ROUTINE', 'CREATE USER', 'EVENT', 'TRIGGER',
                         'CREATE TABLESPACE'])

_TABLE_ALL_PRIVS = set(['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'CREATE',
                        'DROP', 'REFERENCES', 'INDEX', 'ALTER', 'CREATE VIEW',
                        'SHOW VIEW', 'TRIGGER'])

_DB_ALL_PRIVS = set(['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'CREATE',
                     'DROP', 'REFERENCES', 'INDEX', 'ALTER',
                     'CREATE TEMPORARY TABLES', 'LOCK TABLES', 'EXECUTE',
                     'CREATE VIEW', 'SHOW VIEW', 'CREATE ROUTINE',
                     'ALTER ROUTINE', 'EVENT', 'TRIGGER'])

_ROUTINE_ALL_PRIVS = set(['EXECUTE', 'ALTER ROUTINE'])

DATABASE_TYPE = 'DATABASE'
TABLE_TYPE = 'TABLE'
PROCEDURE_TYPE = 'PROCEDURE'
ROUTINE_TYPE = 'ROUTINE'
FUNCTION_TYPE = 'FUNCTION'
GLOBAL_TYPE = 'GLOBAL'
GLOBAL_LEVEL = 3
DATABASE_LEVEL = 2
OBJECT_LEVEL = 1

ALL_PRIVS_LOOKUP_DICT = {PROCEDURE_TYPE: _ROUTINE_ALL_PRIVS,
                         ROUTINE_TYPE: _ROUTINE_ALL_PRIVS,
                         FUNCTION_TYPE: _ROUTINE_ALL_PRIVS,
                         TABLE_TYPE: _TABLE_ALL_PRIVS,
                         DATABASE_TYPE: _DB_ALL_PRIVS,
                         GLOBAL_TYPE: _GLOBAL_ALL_PRIVS}


def get_table_privs(server, db_name, table_name):
    """ Get the list of grantees and their privileges for a specific table.

    server[in]          Instance of Server class, where the query will be
                        executed.
    db_name[in]     Name of the database where the table belongs to.
    table_name[in]  Name of the table to check.

    Returns list of tuples (<Grantee>, <SET OF GRANTS>).
    """
    tpl_lst = []
    # Get sql_mode in server
    sql_mode = server.select_variable("SQL_MODE")
    # Remove backticks if necessary
    if is_quoted_with_backticks(db_name, sql_mode):
        db_name = remove_backtick_quoting(db_name, sql_mode)
    if is_quoted_with_backticks(table_name, sql_mode):
        table_name = remove_backtick_quoting(table_name, sql_mode)

    # Build query
    query = _TABLE_PRIV_QUERY.format(db_name, table_name)
    res = server.exec_query(query)
    for grantee, grant_option, grants in res:
        grants = set((grant.upper() for grant in grants.split(',')))
        # remove USAGE privilege since it does nothing.
        grants.discard('USAGE')
        if grants:
            if 'Y' in grant_option.upper():
                grants.add('GRANT OPTION')
            tpl_lst.append((grantee, grants))

    return tpl_lst


def get_db_privs(server, db_name):
    """ Get the list of grantees and their privileges for a database.

    server[in]          Instance of Server class, where the query will be
                        executed.
    db_name[in]  Name of the database to check.

    Returns list of tuples (<Grantee>, <SET OF GRANTS>).
    """
    tpl_lst = []
    # Get sql_mode in server
    sql_mode = server.select_variable("SQL_MODE")
    # remove backticks if necessary
    if is_quoted_with_backticks(db_name, sql_mode):
        db_name = remove_backtick_quoting(db_name, sql_mode)

    # Build query
    query = _DB_PRIVS_QUERY.format(db_name)
    res = server.exec_query(query)
    for grantee, grant_option, grants in res:
        grants = set((grant.upper() for grant in grants.split(',')))
        # remove USAGE privilege since it does nothing.
        grants.discard('USAGE')
        if grants:
            if 'Y' in grant_option.upper():
                grants.add('GRANT OPTION')
            tpl_lst.append((grantee, grants))

    return tpl_lst


def get_global_privs(server):
    """ Get the list of grantees and their list of global privileges.

    server[in]          Instance of Server class, where the query will be
                        executed.

    Returns list of tuples (<Grantee>, <SET OF GRANTS>).
    """
    tpl_lst = []
    query = _GLOBAL_PRIV_QUERY
    res = server.exec_query(query)
    for grantee, grant_option, grants in res:
        grants = set((grant.upper() for grant in grants.split(',')))
        # remove USAGE privilege since it does nothing.
        grants.discard('USAGE')
        if grants:
            if 'Y' in grant_option.upper():
                grants.add('GRANT OPTION')
            tpl_lst.append((grantee, grants))
    return tpl_lst


def get_routine_privs(server, db_name, routine_name):
    """ Get the list of grantees and their privileges for a routine.

    server[in]          Instance of Server class, where the query will be
                        executed.
    db_name[in]         Name of the database where the table belongs to.
    routine_name[in]    Name of the routine to check.

    Returns list of tuples (<GRANTEE>, <SET OF GRANTS>).
    """
    tpl_lst = []
    # Get sql_mode in server
    sql_mode = server.select_variable("SQL_MODE")
    # remove backticks if necesssary
    if is_quoted_with_backticks(db_name, sql_mode):
        db_name = remove_backtick_quoting(db_name, sql_mode)
    if is_quoted_with_backticks(routine_name, sql_mode):
        routine_name = remove_backtick_quoting(routine_name, sql_mode)

    # Build query
    query = _PROCS_PRIV_QUERY.format(db_name, routine_name)
    res = server.exec_query(query)
    for user, host, grants in res:
        grants = set((grant.upper() for grant in grants.split(',')))
        # remove USAGE privilege since it does nothing.
        grants.discard('USAGE')
        if grants:
            tpl_lst.append(("'{0}'@'{1}'".format(user, host), grants))
    return tpl_lst


def simplify_grants(grant_set, obj_type):
    """Replaces set of privileges with ALL PRIVILEGES, if possible

    grant_set[in]  set of privileges.
    obj_type[in]   type of the object to which these privileges apply.

    Returns a set with the simplified version of grant_set.
    """
    # Get set with all the privileges for the specified object type.
    all_privs = ALL_PRIVS_LOOKUP_DICT[obj_type]

    # remove USAGE privilege since it does nothing and is not on the global
    # all privileges set of any type
    grant_set.discard('USAGE')

    # Check if grant_set has grant option and remove if before checking
    # if given set of privileges contains all the privileges for the
    # specified type
    grant_opt_set = set(['GRANT OPTION', 'GRANT'])
    has_grant_opt = bool(grant_opt_set.intersection(grant_set))
    if has_grant_opt:
        # Remove grant option.
        grant_set = grant_set.difference(grant_opt_set)
    # Check if remaining privileges can be replaced with ALL PRIVILEGES.
    if all_privs == grant_set:
        grant_set = set(["ALL PRIVILEGES"])
    if has_grant_opt:
        # Insert GRANT OPTION PRIVILEGE again.
        grant_set.add("GRANT OPTION")
    return grant_set


def filter_grants(grant_set, obj_type_str):
    """This method returns a new set with just the grants that are valid to
    a given object type.

    grant_set[in]          Set of grants we want to 'filter'
    obj_type_str[in]       String with the type of the object that we are
                           working with, must be either 'ROUTINE', 'TABLE' or
                           'DATABASE'.

    Returns a new set with just the grants that apply.
    """
    # Get set with all the privs for obj_type
    all_privs_set = ALL_PRIVS_LOOKUP_DICT[obj_type_str]
    # Besides having all the privs from the obj_type, it can also have
    # 'ALL', 'ALL PRIVILEGES' and 'GRANT OPTION'
    all_privs_set = all_privs_set.union(['ALL', 'ALL PRIVILEGES',
                                         'GRANT OPTION'])

    # By intersecting the grants we have with the object type's valid set of
    # grants we will obtain just the set of valid grants.
    return grant_set.intersection(all_privs_set)


def _build_privilege_dicts(server, obj_type_dict, inherit_level=GLOBAL_LEVEL):
    """Builds TABLE, ROUTINE and DB dictionaries with grantee privileges

    server[in]        Server class instance
    obj_type_dict[in] dictionary with the list of objects to obtain the
                      grantee and respective grant information, organized
                      by object type
    inherit_level[in] Level of inheritance that should be taken into account.
                      It must be one of GLOBAL_LEVEL, DATABASE_LEVEL or
                      OBJECT_LEVEL

    This method builds and returns the 3 dictionaries with grantee
    information taking into account the grant hierarchy from mysql, i.e.
    global grants apply to all objects and database grants apply to all
    the database objects (tables, procedures and functions).
    """
    # Get the global Grants:
    global_grantee_lst = get_global_privs(server)
    # Build the Database level grants dict.
    # {db_name: {grantee: set(privileges)}}
    db_grantee_dict = defaultdict(lambda: defaultdict(set))
    for db_name, _ in obj_type_dict[DATABASE_TYPE]:
        db_privs_lst = get_db_privs(server, db_name)
        for grantee, priv_set in db_privs_lst:
            db_grantee_dict[db_name][grantee] = priv_set
        if inherit_level >= GLOBAL_LEVEL:
            # If global inheritance level is turned on, global privileges
            # also apply to the database level.
            for grantee, priv_set in global_grantee_lst:
                db_grantee_dict[db_name][grantee].update(
                    filter_grants(priv_set, DATABASE_TYPE))

    # Build the table Level grants dict.
    # {db_name: {tbl_name: {grantee: set(privileges)}}}
    table_grantee_dict = defaultdict(
        lambda: defaultdict(lambda: defaultdict(set)))

    for db_name, tbl_name in obj_type_dict[TABLE_TYPE]:
        tbl_privs_lst = get_table_privs(server, db_name, tbl_name)
        for grantee, priv_set in tbl_privs_lst:
            table_grantee_dict[db_name][tbl_name][grantee] = priv_set
        # Existing db and global_grantee level privileges also apply to
        # the table level if inherit level is database level or higher
        if inherit_level >= DATABASE_LEVEL:
            # If we already have the privileges for the database where the
            # table is at, we can use that information.
            if db_grantee_dict[db_name]:
                for grantee, priv_set in db_grantee_dict[db_name].iteritems():
                    table_grantee_dict[db_name][tbl_name][grantee].update(
                        filter_grants(priv_set, TABLE_TYPE))
            else:
                # Get the grant information for the db the table is at and
                # merge it together with database grants.
                db_privs_lst = get_db_privs(server, db_name)
                for grantee, priv_set in db_privs_lst:
                    table_grantee_dict[db_name][tbl_name][grantee].update(
                        filter_grants(priv_set, TABLE_TYPE))
                # Now do the same with global grants
                if inherit_level >= GLOBAL_LEVEL:
                    for grantee, priv_set in global_grantee_lst:
                        table_grantee_dict[db_name][tbl_name][grantee].update(
                            filter_grants(priv_set, TABLE_TYPE))

    # Build the ROUTINE Level grants dict.
    # {db_name: {proc_name: {user: set(privileges)}}}
    proc_grantee_dict = defaultdict(
        lambda: defaultdict(lambda: defaultdict(set)))
    for db_name, proc_name in obj_type_dict[ROUTINE_TYPE]:
        proc_privs_lst = get_routine_privs(server, db_name, proc_name)
        for grantee, priv_set in proc_privs_lst:
            proc_grantee_dict[db_name][proc_name][grantee] = priv_set
        # Existing db and global_grantee level privileges also apply to
        # the routine level if inherit level is database level or higher
        if inherit_level >= DATABASE_LEVEL:
            # If we already have the privileges for the database where the
            # routine is at, we can use that information.
            if db_grantee_dict[db_name]:
                for grantee, priv_set in db_grantee_dict[db_name].iteritems():
                    proc_grantee_dict[db_name][proc_name][grantee].update(
                        filter_grants(priv_set, ROUTINE_TYPE))
            else:
                # Get the grant information for the db the routine belongs to
                #  and merge it together with global grants.
                db_privs_lst = get_db_privs(server, db_name)
                for grantee, priv_set in db_privs_lst:
                    proc_grantee_dict[db_name][proc_name][grantee].update(
                        filter_grants(priv_set, ROUTINE_TYPE))
                # Now do the same with global grants.
                if inherit_level >= GLOBAL_LEVEL:
                    for grantee, priv_set in global_grantee_lst:
                        proc_grantee_dict[db_name][proc_name][grantee].update(
                            filter_grants(priv_set, ROUTINE_TYPE))

    # TODO Refactor the code below to remove code repetition.

    # Simplify sets of privileges for databases.
    for grantee_dict in db_grantee_dict.itervalues():
        for grantee, priv_set in grantee_dict.iteritems():
            grantee_dict[grantee] = simplify_grants(priv_set,
                                                    DATABASE_TYPE)

    # Simplify sets of privileges for tables.
    for tbl_dict in table_grantee_dict.itervalues():
        for grantee_dict in tbl_dict.itervalues():
            for grantee, priv_set in grantee_dict.iteritems():
                grantee_dict[grantee] = simplify_grants(priv_set,
                                                        TABLE_TYPE)

    # Simplify sets of privileges for routines.
    for proc_dict in proc_grantee_dict.itervalues():
        for grantee_dict in proc_dict.itervalues():
            for grantee, priv_set in grantee_dict.iteritems():
                grantee_dict[grantee] = simplify_grants(priv_set,
                                                        ROUTINE_TYPE)

    return db_grantee_dict, table_grantee_dict, proc_grantee_dict


def _has_all_privileges(query_priv_set, grantee_priv_set, obj_type):
    """Determines if a grantee has a certain set of privileges.

    query_priv_set[in]     set of privileges to be tested
    grantee_priv_set[in]   list of the privileges a grantee has over the
                           object
    obj_type[in]           string with the type of the object to be tested

    This method's purpose receives a set of privileges to test
    (query_priv_set), a set of privileges that a given grantee user
    possesses over a certain object(grantee_priv_set) and the type of that
    object. It returns True if the set of privileges that
    the user has over the object is a superset of query_priv_set.

    """
    # If the user has GRANT OPTION and and ALL PRIVILEGES, then we can
    # automatically return True
    if ("GRANT OPTION" in grantee_priv_set and
            ('ALL PRIVILEGES' in grantee_priv_set or
             'ALL' in grantee_priv_set)):
        return True

    # Remove USAGE privilege because it is the same has having nothing
    query_priv_set.discard('USAGE')

    # Also if query_priv_set contains ALL or ALL PRIVILEGES we can simply
    # discard the rest of the privileges on the set except for GRANT OPTION
    if 'ALL' in query_priv_set or 'ALL PRIVILEGES' in query_priv_set:
        query_priv_set = set(['ALL PRIVILEGES']).union(
            query_priv_set & set(['GRANT OPTION'])
        )
    else:
        # Remove privileges that do not apply to the type of object
        query_priv_set = query_priv_set.intersection(
            ALL_PRIVS_LOOKUP_DICT[obj_type].union(["GRANT OPTION"]))

    return query_priv_set.issubset(grantee_priv_set)


def get_grantees(server, valid_obj_type_dict, req_privileges=None,
                 inherit_level=GLOBAL_LEVEL):
    """Get grantees and respective grants for the specified objects.

    server[in]            Server class instance
    valid_obj_type_dict   Dict with list of valid object for server, sorted
                          by object type. We assume that each object exists
                          on the server
    req_privileges[in]    Optional set of required privileges
    inherit_level[in]     Level of inheritance that should be taken into
                          account. It must be one of GLOBAL_LEVEL,
                          DATABASE_LEVEL or OBJECT_LEVEL
    """

    # Build the privilege dicts
    db_dict, table_dict, proc_dict = _build_privilege_dicts(
        server, valid_obj_type_dict, inherit_level)

    # Build final dict with grantee/grant information, taking into account
    # required privileges
    # grantee_dict = {obj_type: {obj_name:{grantee:set_privs}}}
    grantee_dict = defaultdict(
        lambda: defaultdict(lambda: defaultdict(set)))

    # pylint: disable=R0101
    for obj_type in valid_obj_type_dict:
        for db_name, obj_name in valid_obj_type_dict[obj_type]:
            if obj_type == DATABASE_TYPE:
                for grantee, priv_set in db_dict[obj_name].iteritems():
                    if req_privileges is not None:
                        if _has_all_privileges(req_privileges,
                                               priv_set, obj_type):
                            grantee_dict[obj_type][obj_name][grantee] = \
                                priv_set
                    else:  # No need to check if it meets privileges
                        grantee_dict[obj_type][obj_name][grantee] = \
                            priv_set
            else:
                # It is either TABLE or ROUTINE and both have equal
                # structure dicts
                if obj_type == TABLE_TYPE:
                    type_dict = table_dict
                else:
                    type_dict = proc_dict

                for grantee, priv_set in \
                        type_dict[db_name][obj_name].iteritems():
                    # Get the full qualified name for the object
                    f_obj_name = "{0}.{1}".format(db_name, obj_name)
                    if req_privileges is not None:
                        if _has_all_privileges(
                                req_privileges, priv_set, obj_type):
                            grantee_dict[obj_type][f_obj_name][grantee] = \
                                priv_set
                    else:
                        grantee_dict[obj_type][f_obj_name][grantee] = \
                            priv_set

    return grantee_dict
