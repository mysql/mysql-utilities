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
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301 USA
#

"""
This file contains the clone user operation. It is used to clone an existing
MySQL user to one or more new user accounts copying all grant statements
to the new users.
"""

import sys
from mysql.utilities.exception import UtilError

def _show_user_grants(source, user_source, base_user, verbosity):
    """Show grants for a specific user.
    """
    from mysql.utilities.common.user import User

    try:
        if not user_source:
            user_source = User(source, base_user, verbosity)
        print "# Dumping grants for user " + base_user
        user_source.print_grants()
    except UtilError, e:
        print "# Cannot show grants for user %s." % base_user + \
              "Please check user and host for valid names."


def show_users(src_val, verbosity, format, dump=False):
    """Show all users except root and anonymous users on the server.

    src_val[in]        a dictionary containing connection information for the
                       source including:
                       (user, password, host, port, socket)
    verbosty[in]       level of information to display
    format[in]         format of output
    dump[in]           if True, dump the grants for all users
                       default = False
    """

    from mysql.utilities.common.server import connect_servers
    from mysql.utilities.common.format import print_list

    conn_options = {
        'version'   : "5.1.0",
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
    print_list(sys.stdout, format, cols, users)
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

    from mysql.utilities.common.server import connect_servers
    from mysql.utilities.common.user import User

    dump_sql = options.get("dump", False)
    overwrite = options.get("overwrite", False)
    verbosity = options.get("verbosity", False)
    quiet = options.get("quiet", False)
    global_privs = options.get("global_privs", False)

    # Don't require destination for dumping base user grants
    conn_options = {
        'quiet'     : quiet,
        'version'   : "5.1.0",
    }
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

    # Perform the clone here. Loop through new users and clone.
    for new_user in new_user_list:
        if not quiet:
            print "# Cloning %s to user %s " % (base_user, new_user)
        # Check to see if user exists.
        if user_dest.exists(new_user):
            user_dest.drop(new_user)
        # Clone user.
        try:
            user_source.clone(new_user, destination, global_privs)
        except UtilError, e:
            raise

    if not quiet:
        print "# ...done."

    return True
