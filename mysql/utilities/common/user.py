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
This module contains and abstraction of a MySQL user object.
"""

import re
import MySQLdb
from mysql.utilities.common import MySQLUtilError

def parse_user_host(user_name):
    """Parse user, passwd, host, port from user:passwd@host
    
    user_name[in]      MySQL user string (user:passwd@host)
    """

    no_ticks = user_name.replace("'", "")
    user_credentials = re.match("(\w+)(?:\:(\w+))?@(\w+)",
                                no_ticks)
    if user_credentials:
        return user_credentials.groups()
    else:
        return (None, None, None)
        

class User(object):
    """
    The User class can be used to clone the user and its grants to another
    user with the following utilities:

        - Parsing user@host:passwd strings
        - Create, Drop user
        - Check to see if user exists
        - Retrieving and printing grants for user
    """   
    
        
    def __init__(self, server1, user, verbose=False):
        """Constructor
        
        server1[in]        Server class
        user[in]           MySQL user credentials string (user@host:passwd)
        verbose[in]        print extra data during operations (optional)
                           default value = False
        """
        
        self.server1 = server1
        self.user, self.passwd, self.host = parse_user_host(user)
        self.verbose = verbose

    def create(self, new_user=None):
        """Create the user
                
        Attempts to create the user. If the operation fails, an error is
        generated and printed.
        
        new_user[in]       MySQL user string (user@host:passwd)
                           (optional) If omitted, operation is performed
                           on the class instance user name.
        """
        
        cur = self.server1.cursor()
        query_str = "CREATE USER "
        user, passwd, host = None, None, None
        if new_user:
            user, passwd, host = parse_user_host(new_user)
            query_str += "'%s'@'%s' " % (user, host)
        else:
            query_str += "'%s'@'%s' " % (self.user, self.host)
            
        if passwd:
            query_str += "IDENTIFIED BY '%s'" % (passwd)
        if self.verbose:
            print query_str
        try:
            res = cur.execute(query_str)
            
        except MySQLdb.Error, e:
            raise MySQLUtilError("%d: %s" % (e.args[0], e.args[1]))
        finally:
            cur.close()

    def drop(self, new_user=None):
        """Drop user from the server

        Attempts to drop the user. If the operation fails, an error is
        generated and printed.

        new_user[in]       MySQL user string (user@host:passwd)
                           (optional) If omitted, operation is performed
                           on the class instance user name.
        """
        
        cur = self.server1.cursor()
        query_str = "DROP USER "
        if new_user:
            user, passwd, host = parse_user_host(new_user)
            query_str += "'%s'@'%s' " % (user, host)
        else:
            query_str += "'%s'@'%s' " % (self.user, self.host)
            
        if self.verbose:
            print query_str
            
        try:
            res = cur.execute(query_str)
        except MySQLdb.Error, e:
            raise MySQLUtilError("%d: %s" % (e.args[0], e.args[1]))
        finally:
            cur.close()

    def exists(self, user_name=None):
        """Check to see if the user exists
        
        user_name[in]      MySQL user string (user@host:passwd)
                           (optional) If omitted, operation is performed
                           on the class instance user name.

        return True = user exists, False = user does not exist
        """
        
        cur = self.server1.cursor()
        user, host, passwd = self.user, self.host, self.passwd
        if user_name:
            user, passwd, host = parse_user_host(user_name)

        res = cur.execute("SELECT * FROM mysql.user WHERE user = '%s'"
                          " and host = '%s'" % (user, host))
        cur.close()
        
        if res:
            return True
        else:
            return False        

    def get_grants(self):
        """Retrieve the grants for the current user
        
        returns MySQLdb.result set or None if no grants defined
        """
        grants = []
        try:
            res = self.server1.exec_query("SHOW GRANTS FOR '%s'@'%s'" % 
                                          (self.user, self.host))
            for grant in res:
                grants.append(grant)
        except MySQLUtilError, e:
            pass # Error here is ok - no grants found.
        try:
            res = self.server1.exec_query("SHOW GRANTS FOR '%s'" % self.user +
                                          "@'%%'")
            for grant in res:
                grants.append(grant)
        except MySQLUtilError, e:
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
        for grant in self.get_grants():
            if regex.match(grant[0]):
                return True

    def print_grants(self):
        """Display grants for the current user"""
        
        res = self.get_grants()
        for grant_tuple in res:
            print grant_tuple[0]

    def clone(self, new_user, destination=None):
        """Clone the current user to the new user
        
        Operation will create the new user account copying all of the
        grants for the current user to the new user. If operation fails,
        an error message is generated and the process halts.
        
        new_name[in]       MySQL user string (user@host:passwd)
        destination[in]    A connection to a new server to clone the user
                           (default is None)
        
        Note: Caller must ensure the new user account does not exist.
        """
        
        res = self.get_grants()
        server = self.server1
        if destination is not None:
            server = destination
        for row in res:
            # Create an instance of the user class.
            user = User(server, new_user, self.verbose)
            if not self.exists():
                try:
                    self.create()
                except MySQLUtilError, e:
                    raise e

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
                
            if self.verbose:
                print grant
                
            cur = server.cursor()
            try:
                res = cur.execute(grant)
            except MySQLdb.Error, e:
                raise MySQLUtilError("%d: %s" % (e.args[0], e.args[1]))
                break
            finally:
                cur.close()

