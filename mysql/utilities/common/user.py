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
This module contains and abstraction of a MySQL user object.
"""

import re
import mysql.connector
from mysql.utilities.exception import UtilError, UtilDBError

def parse_user_host(user_name):
    """Parse user, passwd, host, port from user:passwd@host
    
    user_name[in]      MySQL user string (user:passwd@host)
    """

    user_tuple = (None, None, None)
    no_ticks = user_name.replace("'", "")
    user_credentials = re.match("(\w+)(?:\:(\w+))?@([\w-]+(?:%)?(?:\.[\w-]+)*|%)",
                                no_ticks)
    if user_credentials:
        user_tuple = user_credentials.groups()
    else:
        raise UtilError("Cannot parse user:pass@host : %s." %
                              no_ticks)
    extraneous = no_ticks[user_credentials.end():]
    return user_tuple
            

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
            'fetch' : False
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

        res = self.server1.exec_query(query_str, self.query_options)
        
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
            user, passwd, host = parse_user_host(new_user)
            query_str += "'%s'@'%s' " % (user, host)
        else:
            query_str += "'%s'@'%s' " % (self.user, self.host)
            
        if self.verbosity > 0:
            print query_str
            
        res = self.server1.exec_query(query_str, self.query_options)

    def exists(self, user_name=None):
        """Check to see if the user exists
        
        user_name[in]      MySQL user string (user@host:passwd)
                           (optional) If omitted, operation is performed
                           on the class instance user name.

        return True = user exists, False = user does not exist
        """
        
        user, host, passwd = self.user, self.host, self.passwd
        if user_name:
            user, passwd, host = parse_user_host(user_name)

        res = self.server1.exec_query("SELECT * FROM mysql.user "
                                      "WHERE user = %s and host = %s",
                                      {'params':(user, host)})

        return (res is not None and len(res) >= 1)

    def get_grants(self, globals=False):
        """Retrieve the grants for the current user

        globals[in]        Include global privileges in clone (i.e. user@%)
        
        returns result set or None if no grants defined
        """
        # Get the users' connection user@host if not retrieved
        if self.current_user is None:
            res = self.server1.exec_query("SELECT CURRENT_USER()")
            parts = res[0][0].split('@')
            # If we're connected as some other user, use the user@host
            # defined at instantiation
            if parts[0] != self.user:
                self.current_user = "'%s'@'%s'" % (self.user, self.host)
            else:
                self.current_user = "'%s'@'%s'" % (parts[0], parts[1])
        grants = []
        try:
            res = self.server1.exec_query("SHOW GRANTS FOR %s" % 
                                          self.current_user)
            for grant in res:
                grants.append(grant)
        except UtilDBError, e:
            pass # Error here is ok - no grants found.
        if globals:
            try:
                res = self.server1.exec_query("SHOW GRANTS FOR '%s'" % \
                                              self.user + "@'%'")
                for grant in res:
                    grants.append(grant)
            except UtilDBError, e:
                pass # Error here is ok - no grants found.
        return grants

    def has_privilege(self, db, obj, access):
        """Check to see user has a specific access to a db.object
        
 
        db[in]             Name of database
        obj[in]            Name of object
        access[in]         MySQL access to test (e.g. SELECT)

        Returns True if user has access, False if not
        """
        regex = re.compile(r"GRANT.*\b(?:ALL PRIVILEGES|%s)\b.*"
                           r"ON\s+(?:\*|['`]?%s['`]?)\.(?:\*|[`']?%s[`']?)\s+TO"
                           % (re.escape(access), re.escape(db), re.escape(obj)))
        for grant in self.get_grants(True):
            #print "G:", grant[0], regex.match(grant[0]) is not None
            if regex.match(grant[0]) is not None:
                return True

    def print_grants(self):
        """Display grants for the current user"""
        
        res = self.get_grants(True)
        for grant_tuple in res:
            print grant_tuple[0]

    def clone(self, new_user, destination=None, globals=False):
        """Clone the current user to the new user
        
        Operation will create the new user account copying all of the
        grants for the current user to the new user. If operation fails,
        an error message is generated and the process halts.
        
        new_name[in]       MySQL user string (user@host:passwd)
        destination[in]    A connection to a new server to clone the user
                           (default is None)
        globals[in]        Include global privileges in clone (i.e. user@%)
        
        Note: Caller must ensure the new user account does not exist.
        """
        
        res = self.get_grants(globals)
        server = self.server1
        if destination is not None:
            server = destination
        for row in res:
            # Create an instance of the user class.
            user = User(server, new_user, self.verbosity)
            if not user.exists():
                user.create()

            base_user_ticks = "'" + self.user + "'@'" + self.host + "'"
            user, passwd, host = parse_user_host(new_user)
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

