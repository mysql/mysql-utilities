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
This file contains the clone user operation. It is used to clone an existing
MySQL user to one or more new user accounts copying all grant statements
to the new users.
"""

import sys

from mysql.utilities.exception import UtilError, UtilDBError
from mysql.utilities.common.server import connect_servers
from mysql.utilities.common.format import print_list
from mysql.utilities.common.user import User


def _show_user_grants(source, user_source, base_user, verbosity):
    """Show grants for a specific user.
    """
    try:
        if not user_source:
            user_source = User(source, base_user, verbosity)
        print "# Dumping grants for user " + base_user
        user_source.print_grants()
    except UtilError:
        print "# Cannot show grants for user %s." % base_user + \
              "Please check user and host for valid names."


def show_users(src_val, verbosity, fmt, dump=False):
    """Show all users except root and anonymous users on the server.

    src_val[in]        a dictionary containing connection information for the
                       source including:
                       (user, password, host, port, socket)
    verbosty[in]       level of information to display
    fmt[in]            format of output
    dump[in]           if True, dump the grants for all users
                       default = False
    """
    conn_options = {
        'version': "5.1.0",
    }
    servers = connect_servers(src_val, None, conn_options)
    source = servers[0]

    if verbosity <= 1:
        _QUERY = """
            SELECT user, host FROM mysql.user
            WHERE user.user != ''
        """
        cols = ("user", "host")
    else:
        _QUERY = """
            SELECT user.user, user.host, db FROM mysql.user LEFT JOIN mysql.db
            ON user.user = db.user AND user.host = db.host
            WHERE user.user != ''
        """
        cols = ("user", "host", "database")

    users = source.exec_query(_QUERY)
    print "# All Users:"
    print_list(sys.stdout, fmt, cols, users)
    if dump:
        for user in users:
            _show_user_grants(source, None, "'%s'@'%s'" % user[0:2], verbosity)


def clone_user(src_val, dest_val, base_user, new_user_list, options):
    """Clone a user to one or more new user accounts

    This method will create one or more new user accounts copying the
    grant statements from a given user. If source and destination are the
    same, the copy will occur on a single server otherwise, the caller may
    specify a destination server to where the user accounts will be copied.

    NOTES:
    The user is responsible for making sure the databases and objects
    referenced in the cloned GRANT statements exist prior to running this
    utility.

    src_val[in]        a dictionary containing connection information for the
                       source including:
                       (user, password, host, port, socket)
    dest_val[in]       a dictionary containing connection information for the
                       destination including:
                       (user, password, host, port, socket)
    base_user[in]      the user account on the source machine to be used as
                       the template for the new users
    user_list[in]      a list of new user accounts in the form:
                       (username:password@host)
    options[in]        optional parameters dictionary including:
                         dump_sql - if True, print grants for base user
                                    (no new users are created)
                         force    - drop new users if they exist
                         verbosity - print add'l information during operation
                         quiet   - do not print information during operation
                                   Note: Error messages are printed regardless
                         global_privs - include global privileges (i.e. user@%)

    Returns bool True = success, raises UtilError if error
    """
    dump_sql = options.get("dump", False)
    overwrite = options.get("overwrite", False)
    verbosity = options.get("verbosity", False)
    quiet = options.get("quiet", False)
    global_privs = options.get("global_privs", False)

    # Don't require destination for dumping base user grants
    conn_options = {
        'quiet': quiet,
        'version': "5.1.0",
    }

    # Add ssl certs if there are any.
    conn_options['ssl_cert'] = options.get("ssl_cert", None)
    conn_options['ssl_ca'] = options.get("ssl_ca", None)
    conn_options['ssl_key'] = options.get("ssl_key", None)

    if dump_sql:
        servers = connect_servers(src_val, None, conn_options)
    else:
        servers = connect_servers(src_val, dest_val, conn_options)

    source = servers[0]
    destination = servers[1]
    if destination is None:
        destination = servers[0]

    # Create an instance of the user class for source.
    user_source = User(source, base_user, verbosity)

    # Create an instance of the user class for destination.
    user_dest = User(destination, base_user, verbosity)

    # First find out what is the user that will be giving of grants in the
    # destination server.
    try:
        res = destination.exec_query("SELECT CURRENT_USER()")
    except UtilDBError as err:
        raise UtilError("Unable to obtain information about the account used "
                        "to connect to the destination server: "
                        "{0}".format(err.errmsg))

    # Create an instance of the user who will be giving the privileges.
    user_priv_giver = User(destination, res[0][0], verbosity)

    # Check to ensure base user exists.
    if not user_source.exists(base_user):
        raise UtilError("Base user does not exist!")

    # Process dump operation
    if dump_sql and not quiet:
        _show_user_grants(source, user_source, base_user, verbosity)
        return True

    # Check to ensure new users don't exist.
    if overwrite is None:
        for new_user in new_user_list:
            if user_dest.exists(new_user):
                raise UtilError("User %s already exists. Use --force "
                                "to drop and recreate user." % new_user)

    if not quiet:
        print "# Cloning %d users..." % (len(new_user_list))
    # Check privileges to create/delete users.
    can_create = can_drop = False
    if user_priv_giver.has_privilege('*', '*', "CREATE_USER"):
        can_create = can_drop = True
    else:
        if user_priv_giver.has_privilege('mysql', '*', "INSERT"):
            can_create = True
        if user_priv_giver.has_privilege('mysql', '*', "DELETE"):
            can_drop = True

    if not can_create:  # Destination user cannot create new users.
        raise UtilError("Destination user {0}@{1} needs either the "
                        "'CREATE USER' on *.* or 'INSERT' on mysql.* "
                        "privilege to create new users."
                        "".format(user_priv_giver.user, user_priv_giver.host))

    # Perform the clone here. Loop through new users and clone.
    for new_user in new_user_list:
        if not quiet:
            print "# Cloning %s to user %s " % (base_user, new_user)
        # Check to see if user exists.
        if user_dest.exists(new_user):
            if not can_drop:  # Destination user cannot drop existing users.
                raise UtilError("Destination user {0}@{1} needs either the "
                                "'CREATE USER' on *.* or 'DELETE' on mysql.* "
                                "privilege to drop existing users."
                                "".format(user_priv_giver.user,
                                          user_priv_giver.host))

            user_dest.drop(new_user)
        # Clone user.
        try:
            missing_privs = user_priv_giver.missing_user_privileges(
                user_source, plus_grant_option=True)
            if not missing_privs:
                user_source.clone(new_user, destination, global_privs)
            else:
                # Our user lacks some privileges, lets create an informative
                # error message
                pluralize = '' if len(missing_privs) == 1 else 's'
                missing_privs_str = ', '.join(
                    ["{0} on {1}.{2}".format(priv, db, table) for
                     priv, db, table in missing_privs])
                raise UtilError("User {0} cannot be cloned because destination"
                                " user {1}@{2} is missing the following "
                                "privilege{3}: {4}."
                                "".format(new_user, user_priv_giver.user,
                                          user_priv_giver.host, pluralize,
                                          missing_privs_str))
        except UtilError:
            raise

    if not quiet:
        print "# ...done."

    return True
