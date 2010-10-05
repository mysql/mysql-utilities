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
This module contains abstractions of a MySQL Database object used by
multiple utilities.
"""

import datetime
import os
import re
import MySQLdb
from mysql.utilities.common import MySQLUtilError

# List of database objects for enumeration
_DATABASE, _TABLE, _VIEW, _TRIG, _PROC, _FUNC, _EVENT, _GRANT = "DATABASE", \
    "TABLE", "VIEW", "TRIGGER", "PROCEDURE", "FUNCTION", "EVENT", "GRANT"

class Database(object):
    """
    The Table class encapsulates a database. The class
    has the following capabilities:

        - Check to see if the database exists
        - Drop the database
        - Create the database
        - Clone the database
        - Print CREATE statements for all objects
    """
    obj_type = _DATABASE
    
    def __init__(self, source, name, options={}):
        """Constructor
        
        source[in]         A Server object
        name[in]           Name of database
        verbose[in]        print extra data during operations (optional)
                           default value = False
        options[in]        Array of options for controlling what is included
                           and how operations perform (e.g., verbose) 
        """
        self.source = source
        self.db_name = name
        self.verbose = options.get("verbose", False)
        self.skip_tables = options.get("skip_tables", False)
        self.skip_views = options.get("skip_views", False)
        self.skip_triggers = options.get("skip_triggers", False)
        self.skip_procs = options.get("skip_procs", False)
        self.skip_funcs = options.get("skip_funcs", False)
        self.skip_events = options.get("skip_events", False)
        self.skip_grants = options.get("skip_grants", False)
        self.skip_create = options.get("skip_create", False)
        self.skip_data = options.get("skip_data", False)
        self.new_db = None
        self.init_called = False
        self.destination = None # Used for copy mode
        self.cloning = False    # Used for clone mode
        
        self.objects = []
        self.new_objects = []
        
    def exists(self, server=None, db_name=None):
        """Check to see if the database exists
        
        server[in]         A Server object
                           (optional) If omitted, operation is performed
                           using the source server connection.
        db_name[in]        database name
                           (optional) If omitted, operation is performed
                           on the class instance table name.

        return True = database exists, False = database does not exist
        """
        
        if not server:
            server = self.source
        cur = server.cursor()
        db = None
        if db_name:
            db = db_name
        else:
            db = self.db_name
            
        res = cur.execute("SELECT SCHEMA_NAME " +
                          "FROM INFORMATION_SCHEMA.SCHEMATA " +
                          "WHERE SCHEMA_NAME = '%s'" % db)
        cur.close()
        
        if res:
            return True
        else:
            return False
    
    def drop(self, server, silent, db_name=None):
        """Drop the database
        
        server[in]         A Server object
        silent[in]         ignore error on drop
        db_name[in]        database name
                           (optional) If omitted, operation is performed
                           on the class instance table name.

        return True = database successfully dropped, False = error
        """

        cur = server.cursor()
        db = None
        if db_name:
            db = db_name
        else:
            db = self.db_name
        op_ok = False
        if silent:
            try:
                res = cur.execute("DROP DATABASE %s" % (db))
            except:
                pass
            cur.close()
        else:
            try:
                res = cur.execute("DROP DATABASE %s" % (db))
                op_ok = True
            except MySQLdb.Error, e:
                raise MySQLUtilError("%d: %s" % (e.args[0], e.args[1]))
            finally:
                cur.close()
        return op_ok
        
        
    def create(self, server, db_name=None):
        """Create the database
        
        server[in]         A Server object
        db_name[in]        database name
                           (optional) If omitted, operation is performed
                           on the class instance table name.

        return True = database successfully created, False = error
        """

        cur = server.cursor()
        db = None
        if db_name:
            db = db_name
        else:
            db = self.db_name
        op_ok = False
        try:
            res = cur.execute("CREATE DATABASE %s" % (db))
            op_ok = True
        except MySQLdb.Error, e:
            raise MySQLUtilError("%d: %s" % (e.args[0], e.args[1]))
        finally:
            cur.close()
        return op_ok
    
    def __make_create_statement(self, obj_type, obj):
        """Construct a CREATE statement for a database object.
        
        This method will get the CREATE statement from the method
        get_create_statement() and also replace all occurrances of the
        old database name with the new.
        
        obj_type[in]       Object type (string) e.g. DATABASE
        obj[in]            A row from the get_db_objects() method
                           that contains the elements of the object
 
        Note: This does not work for tables.

        Returns the CREATE string
        """
        
        if not self.new_db:
            self.new_db = self.db_name
        create_str = None
        # Tables are not supported
        if obj_type == _TABLE and self.cloning:
            return None
        # Grants are a different animal!
        if obj_type == _GRANT:
            if obj[3]:
                create_str = "GRANT %s ON %s.%s TO %s" % \
                             (obj[1], self.new_db, obj[3], obj[0])
            else:
                create_str = "GRANT %s ON %s.* TO %s" % \
                             (obj[1], self.new_db, obj[0])
            if create_str.find("%"):
                create_str = re.sub("%", "%%", create_str)
        else:
            create_str = self.get_create_statement(self.db_name,
                                                   obj[0], obj_type)
            if self.new_db != self.db_name:
                create_str = re.sub(r" %s\." % self.db_name,
                                    r" %s." % self.new_db,
                                    create_str)
                create_str = re.sub(r" `%s`\." % self.db_name, 
                                    r" `%s`." % self.new_db,
                                    create_str)
                create_str = re.sub(r" '%s'\." % self.db_name, 
                                    r" '%s'." % self.new_db,
                                    create_str)
                create_str = re.sub(r' "%s"\.' % self.db_name, 
                                    r' "%s".' % self.new_db,
                                    create_str)
        return create_str


    def __add_db_objects(self, obj_type):
        """Get a list of objects from a database based on type.
        
        This method retrieves the list of objects for a specific object
        type and adds it to the class' master object list.
        
        obj_type[in]       Object type (string) e.g. DATABASE
        """

        rows = self.get_db_objects(obj_type)
        if rows:
            for row in rows:
                tuple = (obj_type, row)
                self.objects.append(tuple)
                

    def init(self):
        """Get all objects for the database based on options set.
        
        This method initializes the database object with a list of all
        objects except those object types that are excluded. It calls
        the helper method self.__add_db_objects() for each type of
        object.
        
        NOTE: This method must be called before the copy method. A
              guard is in place to ensure this.
        """
        self.init_called = True
        # Get tables
        if not self.skip_tables:
            self.__add_db_objects(_TABLE)
        # Get views
        if not self.skip_views:
            self.__add_db_objects(_VIEW)
        # Get triggers
        if not self.skip_triggers:
            self.__add_db_objects(_TRIG)
        # Get stored procedures
        if not self.skip_procs:
            self.__add_db_objects(_PROC)
        # Get functions
        if not self.skip_funcs:
            self.__add_db_objects(_FUNC)
        # Get events
        if not self.skip_events:
            self.__add_db_objects(_EVENT)
        # Get grants
        if not self.skip_grants:
            self.__add_db_objects(_GRANT)
    
    def __drop_object(self, obj_type, name):
        """Drop a database object.
        
        Attempts a silent drop of a database object (no errors are
        printed).

        obj_type[in]       Object type (string) e.g. DATABASE
        name[in]           Name of the object
        """

        if self.verbose:
            print "Dropping new object %s %s.%s" % \
                  (obj_type, self.new_db, name)
        drop_str = "DROP %s %s.%s" % \
                   (obj_type, self.new_db, name)
        # Suppress the error on drop
        if self.cloning:
            try:
                self.source.exec_query(drop_str)
            except:
                pass
        else:
            try:
                self.destination.exec_query(drop_str)
            except:
                pass
            

    def __create_object(self, obj_type, obj, show_grant_msg,
                        silent=False):
        """Create a database object.

        obj_type[in]       Object type (string) e.g. DATABASE
        obj[in]            A row from the get_db_objects() method
                           that contains the elements of the object
        show_grant_msg[in] If true, display diagnostic information
        silent[in]         do not print informational messages

        Note: will handle exception and print error if query fails
        """
        
        create_str = None
        if obj_type == _TABLE and self.cloning:
            create_str = "CREATE TABLE %s.%s LIKE %s.%s" % \
                         (self.new_db, obj[0], self.db_name, obj[0])
        else:
            create_str = self.__make_create_statement(obj_type, obj)
        str = "# Copying"
        if not silent:
            if obj_type == _GRANT:
                if show_grant_msg:
                    print "%s GRANTS from %s" % (str, self.db_name)
            else:
                print "%s %s %s.%s" % \
                      (str, obj_type, self.db_name, obj[0])
            if self.verbose:
                print create_str
        res = None
        try:
            res = self.destination.exec_query("USE %s" % self.new_db)
        except:
            pass
        try:
            res = self.destination.exec_query(create_str)
        except Exception, e:
            raise MySQLUtilError("Cannot operate on %s object. Error: %s" % 
                                 (obj_type, e.errmsg))

    def __copy_table_data(self, name, silent=False):
        """Clone table data.
        
        This method will copy all of the data for a table
        from the old database to the new database.

        name[in]           Name of the object
        silent[in]         do not print informational messages

        Note: will handle exception and print error if query fails
        """
        
        if not silent:
            print "# Copying table data."
        query_str = "INSERT INTO %s.%s SELECT * FROM %s.%s" % \
                    (self.new_db, name, self.db_name, name)
        if self.verbose and not silent:
            print query_str
        try:
            self.source.exec_query(query_str)
        except MySQLUtilError, e:
            raise e
        
    
    def copy(self, new_db, input_file, options,
             new_server=None, connections=1):
        """Copy a database.
        
        This method will copy a database and all of its objecs and data
        to another, new database. Options set at instantiation will determine
        if there are objects that are excluded from the copy. Likewise,
        the method will also skip data if that option was set and process
        an input file with INSERT statements if that option was set.

        The method can also be used to copy a database to another server
        by providing the new server object (new_server). Copy to the same
        name by setting new_db = old_db or as a new database.
        
        new_db[in]         Name of the new database
        input_file[in]     Full path of input file (or None)
        options[in]        Options for copy e.g. force, copy_dir, etc.
        new_server[in]     Connection to another server for copying the db
                           Default is None (copy to same server - clone)
        connections[in]    Number of threads(connections) to use for insert
        """
        
        from mysql.utilities.common import Table
 
        # Must call init() first!
        # Guard for init() prerequisite
        assert self.init_called, "You must call db.init() before db.copy()."

        grant_msg_displayed = False
        self.new_db = new_db
        copy_file = None
        self.destination = new_server
        
        # We know we're cloning if there is no new connection.
        self.cloning = (new_server is None)

        # Turn off input file if we aren't cloning
        if not self.cloning:
            copy_file = input_file
            input_file = None
            self.destination = new_server
            copy_file = "copy_data_%s" % \
                        (datetime.datetime.now().strftime("%Y.%m.%d"))
            if options.get("copy_dir", False):
               copy_file = options["copy_dir"] + copy_file
        else:
            self.destination = self.source

        try:
            res = self.destination.show_server_variable("foreign_key_checks")
            if res:
                fkey = (res[0][1] == "ON")
            else:
                fkey = False
        except MySQLUtilError, e:
            raise e
            
        fkey_query = "SET foreign_key_checks = %s"
            
        # First, turn off foreign keys if turned on
        if fkey:
            try:
                res = self.destination.exec_query(fkey_query, "OFF")
            except MySQLUtilError, e:
                raise e
        
        # Check to see if database exists
        exists = False
        drop_server = None
        if self.cloning:
            exists = self.exists(self.source, new_db)
            drop_server = self.source
        else:
            exists = self.exists(self.destination, new_db)
            drop_server = self.destination
        if exists:
            if options.get("force", False):
                self.drop(drop_server, True, new_db)
            elif not self.skip_create:
                raise MySQLUtilError("destination database exists. Use "
                                      "--force to overwrite existing "
                                      "database.")

        # Create new database first
        if not self.skip_create:
            if self.cloning:
                self.create(self.source, new_db)
            else:
                self.create(self.destination, new_db)
            
        # Create the objects in the new database
        for obj in self.objects:

            # Drop object if --force specified and database not dropped
            # Grants do not need to be dropped for overwriting
            if options.get("force", False) and obj[0] != _GRANT:
                self.__drop_object(obj[0], obj[1][0])
                
            # Create the object
            try:
                self.__create_object(obj[0], obj[1], not grant_msg_displayed,
                                     options.get("silent", False))
            except MySQLUtilError, e:
                raise e
            
            if obj[0] == _GRANT and not grant_msg_displayed:
                grant_msg_displayed = True
                
            # Now copy the data if enabled
            if not self.skip_data:
                if obj[0] == _TABLE:
                    tblname = obj[1][0]
                    if self.cloning:
                        self.__copy_table_data(tblname, options.get("silent",
                                                                    False))
                    else:
                        if not options.get("silent", False):
                            print "# Copying data for TABLE %s.%s" % \
                                   (self.db_name, tblname)
                        try:
                            tbl = Table(self.source,
                                        "%s.%s" % (self.db_name, tblname),
                                        self.verbose)
                            if tbl is None:
                                raise MySQLUtilError("Cannot create table "
                                                     "object before copy.")
                                
                            tbl.copy_data(self.destination, new_db,
                                          self.verbose, connections)
                        except MySQLUtilError, e:
                            raise e
                        
        # Cleanup
        if copy_file:
            if os.access(copy_file, os.F_OK):
                os.remove(copy_file)

        # Now, turn on foreign keys if they were on at the start
        if fkey:
            try:
                res = self.destination.exec_query(fkey_query, "ON")
            except MySQLUtilError, e:
                raise e


    def get_create_statement(self, db, name, obj_type):
        """Return the create statement for the object
        
        db[in]             Database name
        name[in]           Name of the object 
        obj_type[in]       Object type (string) e.g. DATABASE
                           Note: this is used to form the correct SHOW command
    
        Returns create statement
        """
    
        row = None
        if obj_type == _DATABASE:
            name_str = name
        else:
            name_str = db + "." + name
        try:
            row = self.source.exec_query("SHOW CREATE %s %s" % \
                                         (obj_type, name_str))
        except MySQLUtilError, e:
            raise e
        
        create_statement = None
        if row:
            if obj_type == _TABLE or obj_type == _VIEW or \
               obj_type == _DATABASE:
                create_statement = row[0][1]
            elif obj_type == _EVENT:
                create_statement = row[0][3]
            else:
                create_statement = row[0][2]
        if create_statement.find("%"):
            create_statement = re.sub("%", "%%", create_statement)
        return create_statement
        

    def get_db_objects(self, obj_type):
        """Return a result set containing all objects for a given database
        
        obj_type[in]       Type of object to retrieve    

        TODO: Change implementation to return classes instead of a result set.
    
        Returns MySQLdb result set
        """
    
        # Must call init() first!
        # Guard for init() prerequisite
        assert self.init_called, "You must call db.init() before db.copy()."

        if obj_type == _TABLE:
            _OBJECT_QUERY = """
            SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_SCHEMA = %s AND TABLE_TYPE <> 'VIEW'
            """
        elif obj_type == _VIEW:
            _OBJECT_QUERY = """
            SELECT TABLE_NAME FROM INFORMATION_SCHEMA.VIEWS 
            WHERE TABLE_SCHEMA = %s
            """
        elif obj_type == _TRIG:
            _OBJECT_QUERY = """
            SELECT TRIGGER_NAME FROM INFORMATION_SCHEMA.TRIGGERS 
            WHERE TRIGGER_SCHEMA = %s 
            """
        elif obj_type == _PROC:
            _OBJECT_QUERY = """
            SELECT ROUTINE_NAME FROM INFORMATION_SCHEMA.ROUTINES 
            WHERE ROUTINE_SCHEMA = %s AND ROUTINE_TYPE = 'PROCEDURE'
            """
        elif obj_type == _FUNC:
            _OBJECT_QUERY = """
            SELECT ROUTINE_NAME FROM INFORMATION_SCHEMA.ROUTINES 
            WHERE ROUTINE_SCHEMA = %s AND ROUTINE_TYPE = 'FUNCTION'
            """
        elif obj_type == _EVENT:
            _OBJECT_QUERY = """
            SELECT EVENT_NAME FROM INFORMATION_SCHEMA.EVENTS 
            WHERE EVENT_SCHEMA = %s
            """
        elif obj_type == _GRANT:
            _OBJECT_QUERY = """
            (
                SELECT grantee AS c1, privilege_type AS c2, table_schema AS c3,
                       NULL AS c4, NULL AS c5, NULL AS c6
                FROM INFORMATION_SCHEMA.SCHEMA_PRIVILEGES 
                WHERE table_schema = %s
            ) UNION (
                SELECT grantee, privilege_type, table_schema, table_name,
                       NULL, NULL 
                FROM INFORMATION_SCHEMA.TABLE_PRIVILEGES 
                WHERE table_schema = %s
            ) UNION (
                SELECT grantee, privilege_type, table_schema, table_name,
                       column_name, NULL 
                FROM INFORMATION_SCHEMA.COLUMN_PRIVILEGES 
                WHERE table_schema = %s
            ) UNION (
                SELECT CONCAT('''', User, '''@''', Host, ''''),  Proc_priv, Db,
                       Routine_name, NULL, Routine_type 
                FROM mysql.procs_priv WHERE Db = %s
            ) ORDER BY c1 ASC, c2 ASC, c3 ASC, c4 ASC, c5 ASC, c6 ASC
            """
        else:
            return None
        
        if obj_type == _GRANT:
            return self.source.exec_query(_OBJECT_QUERY,
                                          (self.db_name, self.db_name,
                                           self.db_name, self.db_name,))
        else:
            return self.source.exec_query(_OBJECT_QUERY, (self.db_name,))
        
        
    def _check_user_permissions(self, uname, host, access):
        """ Check user permissions for a given privilege
    
        uname[in]          user name to check
        host[in]           host name of connection
        acess[in]          privilege to check (e.g. "SELECT")
        
        Returns True if user has permission, False if not
        """
        
        from mysql.utilities.common import User
        
        result = True    
        user = User(self.source, uname+'@'+host)
        result = user.has_privilege(access[0], '*', access[1])
        return result
    
    
    def check_read_access(self, user, host, skip_views,
                          skip_proc, skip_func, skip_grants):
        """ Check access levels for reading database objects
        
        This method will check the user's permission levels for copying a
        database from this server.
        
        It will also skip specific checks if certain objects are not being
        copied (i.e., views, procs, funcs, grants).
    
        user[in]           user name to check
        host[in]           host name to check
        skip_views[in]     True = no views processed
        skup_proc[in]      True = no procedures processed
        skip_func[in]      True = no functions processed
        skip_grants[in]    True = no grants processed
        
        Returns True if user has permissions and raises a MySQLUtilError if the
                     user does not have permission with a message that includes
                     the server context.
        """
    
        # Build minimal list of privileges for source access    
        source_privs = []
        priv_tuple = (self.db_name, "SELECT")
        source_privs.append(priv_tuple)
        # if views are included, we need SHOW VIEW
        if not skip_views:
            priv_tuple = (self.db_name, "SHOW VIEW")
            source_privs.append(priv_tuple)
        # if procs or funcs are included, we need read on mysql db
        if not skip_proc or not skip_func:
            priv_tuple = ("mysql", "SELECT")
            source_privs.append(priv_tuple)
        
        # Check permissions on source
        for priv in source_privs:
            if not self._check_user_permissions(user, host, priv):
                raise MySQLUtilError("User %s on the %s server does not have "
                                     "permissions to read all objects in %s. " %
                                     (user, self.source.role, self.db_name) +
                                     "User needs %s privilege on %s." %
                                     (priv[1], priv[0]))
            
        return True
    
    
    def check_write_access(self, user, host, skip_views,
                           skip_proc, skip_func, skip_grants):
        """ Check access levels for creating and writing database objects
        
        This method will check the user's permission levels for copying a
        database to this server.
        
        It will also skip specific checks if certain objects are not being
        copied (i.e., views, procs, funcs, grants).
    
        user[in]           user name to check
        host[in]           host name to check
        skip_views[in]     True = no views processed
        skup_proc[in]      True = no procedures processed
        skip_func[in]      True = no functions processed
        skip_grants[in]    True = no grants processed
        
        Returns True if user has permissions and raises a MySQLUtilError if the
                     user does not have permission with a message that includes
                     the server context.
        """
    
        dest_privs = [(self.db_name, "CREATE"),
                      (self.db_name, "SUPER"),
                      ("*", "SUPER")]
        if not skip_grants:
            priv_tuple = (self.db_name, "WITH GRANT OPTION")
            dest_privs.append(priv_tuple)
            
        # Check privileges on destination
        for priv in dest_privs:
            if not self._check_user_permissions(user, host, priv):
                raise MySQLUtilError("User %s on the %s server does not "
                                     "have permissions to create all objects "
                                     "in %s. User needs %s privilege on %s." %
                                     (user, self.source.role, priv[0],
                                      priv[1], priv[0]))
                
        return True

