#
# Copyright (c) 2010, 2014, Oracle and/or its affiliates. All rights reserved.
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
This module contains and abstraction of a MySQL user object.
"""

import re

from mysql.utilities.exception import UtilError, UtilDBError, FormatError
from mysql.utilities.common.ip_parser import parse_connection, clean_IPv6


def change_user_privileges(server, user_name, user_passwd, host,
                           grant_list=None, revoke_list=None,
                           disable_binlog=False, create_user=False):
    """ Change the privileges of a new or existing user.

    This method GRANT or REVOKE privileges to a new user (creating it) or
    existing user.

    server[in]          MySQL server instances to apply changes
                        (from mysql.utilities.common.server.Server).
    user_name[in]       user name to apply changes.
    user_passwd[in]     user's password.
    host[in]            host name associated to the user account.
    grant_list[in]      List of privileges to GRANT.
    revoke_list[in]     List of privileges to REVOKE.
    disable_binlog[in]  Boolean value to determine if the binary logging
                        will be disabled to perform this operation (and
                        re-enabled at the end). By default: False (do not
                        disable binary logging).
    create_user[in]     Boolean value to determine if the user will be
                        created before changing its privileges. By default:
                        False (do no create user).
    """
    if disable_binlog:
        server.exec_query("SET SQL_LOG_BIN=0")
    if create_user:
        server.exec_query("CREATE USER '{0}'@'{1}' IDENTIFIED BY "
                          "'{2}'".format(user_name, host, user_passwd))
    if grant_list:
        grants_str = ", ".join(grant_list)
        server.exec_query("GRANT {0} ON *.* TO '{1}'@'{2}' IDENTIFIED BY "
                          "'{3}'".format(grants_str, user_name, host,
                                         user_passwd))
    if revoke_list:
        revoke_str = ", ".join(revoke_list)
        server.exec_query("REVOKE {0} ON *.* FROM '{1}'@'{2}'"
                          "".format(revoke_str, user_name, host))
    if disable_binlog:
        server.exec_query("SET SQL_LOG_BIN=1")


def parse_user_host(user_name):
    """Parse user, passwd, host, port from user:passwd@host

    user_name[in]      MySQL user string (user:passwd@host)
    """

    no_ticks = user_name.replace("'", "")
    try:
        conn_values = parse_connection(no_ticks)
    except FormatError:
        raise UtilError("Cannot parse user:pass@host : %s." %
                        no_ticks)
    return (conn_values['user'], conn_values['passwd'], conn_values['host'])


class User(object):
    """
    The User class can be used to clone the user and its grants to another
    user with the following utilities:

        - Parsing user@host:passwd strings
        - Create, Drop user
        - Check to see if user exists
        - Retrieving and printing grants for user
    """

    def __init__(self, server1, user, verbosity=0):
        """Constructor

        server1[in]        Server class
        user[in]           MySQL user credentials string (user@host:passwd)
        verbose[in]        print extra data during operations (optional)
                           default value = False
        """

        self.server1 = server1
        self.user, self.passwd, self.host = parse_user_host(user)
        self.verbosity = verbosity
        self.current_user = None
        self.query_options = {
            'fetch': False
        }

    def create(self, new_user=None):
        """Create the user

        Attempts to create the user. If the operation fails, an error is
        generated and printed.

        new_user[in]       MySQL user string (user@host:passwd)
                           (optional) If omitted, operation is performed
                           on the class instance user name.
        """

        query_str = "CREATE USER "
        user, passwd, host = None, None, None
        if new_user:
            user, passwd, host = parse_user_host(new_user)
            query_str += "'%s'@'%s' " % (user, host)
        else:
            query_str += "'%s'@'%s' " % (self.user, self.host)
            passwd = self.passwd

        if passwd:
            query_str += "IDENTIFIED BY '%s'" % (passwd)
        if self.verbosity > 0:
            print query_str

        self.server1.exec_query(query_str, self.query_options)

    def drop(self, new_user=None):
        """Drop user from the server

        Attempts to drop the user. If the operation fails, an error is
        generated and printed.

        new_user[in]       MySQL user string (user@host:passwd)
                           (optional) If omitted, operation is performed
                           on the class instance user name.
        """
        query_str = "DROP USER "
        if new_user:
            user, _, host = parse_user_host(new_user)
            query_str += "'%s'@'%s' " % (user, host)
        else:
            query_str += "'%s'@'%s' " % (self.user, self.host)

        if self.verbosity > 0:
            print query_str

        try:
            self.server1.exec_query(query_str, self.query_options)
        except UtilError:
            return False
        return True

    def exists(self, user_name=None):
        """Check to see if the user exists

        user_name[in]      MySQL user string (user@host:passwd)
                           (optional) If omitted, operation is performed
                           on the class instance user name.

        return True = user exists, False = user does not exist
        """

        user, host, _ = self.user, self.host, self.passwd
        if user_name:
            user, _, host = parse_user_host(user_name)

        res = self.server1.exec_query("SELECT * FROM mysql.user "
                                      "WHERE user = %s and host = %s",
                                      {'params': (user, host)})

        return (res is not None and len(res) >= 1)

    def get_grants(self, globals_privs=False):
        """Retrieve the grants for the current user

        globals_privs[in]     Include global privileges in clone (i.e. user@%)

        returns result set or None if no grants defined
        """
        # Get the users' connection user@host if not retrieved
        if self.current_user is None:
            res = self.server1.exec_query("SELECT CURRENT_USER()")
            parts = res[0][0].split('@')
            # If we're connected as some other user, use the user@host
            # defined at instantiation
            if parts[0] != self.user:
                host = clean_IPv6(self.host)
                self.current_user = "'%s'@'%s'" % (self.user, host)
            else:
                self.current_user = "'%s'@'%s'" % (parts[0], parts[1])
        grants = []
        try:
            res = self.server1.exec_query("SHOW GRANTS FOR "
                                          "{0}".format(self.current_user))
            for grant in res:
                grants.append(grant)
        except UtilDBError:
            pass  # Error here is ok - no grants found.

        # If current user is already using global host wildcard '%', there is
        # no need to run the show grants again.
        if globals_privs and self.host != '%':
            try:
                res = self.server1.exec_query("SHOW GRANTS FOR "
                                              "'{0}'{1}".format(self.user,
                                                                "@'%'"))
                for grant in res:
                    grants.append(grant)
            except UtilDBError:
                pass  # Error here is ok - no grants found.
        return grants

    def has_privilege(self, db, obj, access, allow_skip_grant_tables=True):
        """Check to see user has a specific access to a db.object.

        db[in]             Name of database
        obj[in]            Name of object
        access[in]         MySQL privilege to check (e.g. SELECT, SUPER, DROP)
        allow_skip_grant_tables[in]  If True, allow silent failure for
                           cases where the server is started with
                           --skip-grant-tables. Default=True

        Returns True if user has access, False if not
        """
        grants_enabled = self.server1.grant_tables_enabled()
        # If grants are disabled and it is Ok to allow skipped grant tables,
        # return True - privileges disabled so user can do anything.
        if allow_skip_grant_tables and not grants_enabled:
            return True
        # Convert privilege to upper cases.
        access = access.upper()
        # Create regexp to match SHOW GRANTS.
        if access == "GRANT OPTION":
            # WITH GRANT OPTION appears at the end of SHOW GRANTS.
            regex = re.compile(r"GRANT.+ON\s+"
                               r"(?:\*|['`]?{db}['`]?)\.(?:\*|[`']?{obj}[`']?)"
                               r"\s+TO.+"
                               r"WITH GRANT OPTION".format(db=re.escape(db),
                                                           obj=re.escape(obj)))
        else:
            # GRANT with ALL PRIVILEGES or given privilege (access parameter).
            regex = re.compile(r"GRANT.*\b(?:ALL PRIVILEGES|{priv})\b.*ON\s+"
                               r"(?:\*|['`]?{db}['`]?)\.(?:\*|[`']?{obj}[`']?)"
                               r"\s+TO".format(priv=re.escape(access),
                                               db=re.escape(db),
                                               obj=re.escape(obj)))
        for grant in self.get_grants(True):
            # Check if SHOW GRANTS match regexp with privilege.
            if regex.match(grant[0]):
                return True

    def print_grants(self):
        """Display grants for the current user"""

        res = self.get_grants(True)
        for grant_tuple in res:
            print grant_tuple[0]

    def clone(self, new_user, destination=None, globals_privs=False):
        """Clone the current user to the new user

        Operation will create the new user account copying all of the
        grants for the current user to the new user. If operation fails,
        an error message is generated and the process halts.

        new_name[in]       MySQL user string (user@host:passwd)
        destination[in]    A connection to a new server to clone the user
                           (default is None)
        globals_privs[in]  Include global privileges in clone (i.e. user@%)

        Note: Caller must ensure the new user account does not exist.
        """

        res = self.get_grants(globals_privs)
        server = self.server1
        if destination is not None:
            server = destination
        for row in res:
            # Create an instance of the user class.
            user = User(server, new_user, self.verbosity)
            if not user.exists():
                user.create()

            base_user_ticks = "'" + self.user + "'@'" + self.host + "'"
            user, _, host = parse_user_host(new_user)
            new_user_ticks = "'" + user + "'@'" + host + "'"
            grant = row[0].replace(base_user_ticks, new_user_ticks, 1)

            # Need to remove the IDENTIFIED BY clause for the base user.
            search_str = "IDENTIFIED BY PASSWORD"
            try:
                start = grant.index(search_str)
            except:
                start = 0

            if start > 0:
                end = grant.index("'", start + len(search_str) + 2) + 2
                grant = grant[0:start] + grant[end:]

            if self.verbosity > 0:
                print grant

            res = server.exec_query(grant, self.query_options)
