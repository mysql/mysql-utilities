#!/usr/bin/env python
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
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307 USA
#

"""
This file contains the clone user operation. It is used to clone an existing
MySQL user to one or more new user accounts copying all grant statements
to the new users.
"""

import MySQLdb
from mysql.utilities.common import MySQLUtilError

def clone_user(src_val, dest_val, base_user, new_user_list, dump_sql,
               copy_dir=None, overwrite=False, verbose=False, silent=False):
    """ Clone a user to one or more new user accounts
    
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
    dumpSQL[in]        if True, print grants for base user (no new users
                       are created)
    force[in]          drop new users if they exist
    verbose[in]        print additional information during operation
                       (default is False)
    silent[in]         do not print any information during the operation -
                       Note: Error messages are printed regardless
                       (default is False)
                       
    Returns bool True = success, raises MySQLUtilError if error
    """

    from mysql.utilities.common import connect_servers
    from mysql.utilities.common import User

    try:
        servers = connect_servers(src_val, dest_val, silent, "5.1.0")
    except MySQLUtilError, e:
        raise e

    source = servers[0]
    destination = servers[1]
    
    # Create an instance of the user class.
    user = User(source, base_user, verbose)
    
    # Check to ensure base user exists.
    if not user.exists(base_user):
        raise MySQLUtilError("Base user does not exist!")

    # Process dump operation
    if len(new_user_list) >= 1 and dump_sql and not silent:
        print "Dumping grants for user " + base_user
        user.print_grants()
        return True
    
    # Check to ensure new users don't exist.
    if overwrite is None:
        for new_user in new_user_list:
            if user.exists(new_user):
                raise MySQLUtilError("User %s already exists. Use --force "
                      "to drop and recreate user." % new_user)
    
    if not silent:
        print "# Cloning %d users..." % (len(new_user_list))
    
    # Perform the clone here. Loop through new users and clone.
    for new_user in new_user_list:
        if not silent:
            print "# Cloning %s to user %s " % (base_user, new_user)
        # Check to see if user exists.
        if user.exists(new_user):
            user.drop(new_user)
        # Clone user.
        try:
            user.clone(new_user, destination)
        except MySQLUtilError, e:
            raise

    if not silent:    
        print "# ...done."

    return True