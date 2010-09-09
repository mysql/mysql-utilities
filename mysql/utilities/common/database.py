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
DATABASE, TABLE, VIEW, TRIGGER, PROC, FUNC, EVENT, GRANT = "DATABASE", \
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
    obj_type = DATABASE
    
    def __init__(self, source, name, options):
        """Constructor
        
        source[in]         A Server object
        name[in]           Name of database
        verbose[in]        print extra data during operations (optional)
                           default value = False
        options[in]        Array of options for controlling what is included
                           and how operations perform (e.g., verbose) 
        """
        self.verbose = options["verbose"]
        self.source = source
        self.db_name = name
        self.skip_tables = options["skip_tables"]
        self.skip_views = options["skip_views"]
        self.skip_triggers = options["skip_triggers"]
        self.skip_procs = options["skip_procs"]
        self.skip_funcs = options["skip_funcs"]
        self.skip_events = options["skip_events"]
        self.skip_grants = options["skip_grants"]
        self.skip_create = options["skip_create"]
        self.skip_data = options["skip_data"]
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
        if obj_type == TABLE and self.cloning:
            return None
        # Grants are a different animal!
        if obj_type == GRANT:
            if obj[3]:
                create_str = "GRANT %s ON %s.%s TO %s" % \
                             (obj[1], self.new_db, obj[3], obj[0])
            else:
                create_str = "GRANT %s ON %s.* TO %s" % \
                             (obj[1], self.new_db, obj[0])
        else:
            create_str = self.source.get_create_statement(self.db_name,
                                                           obj[0], obj_type)
            if self.new_db != self.db_name:
                create_str = re.sub(self.db_name, self.new_db, create_str)

        return create_str


    def __add_db_objects(self, obj_type):
        """Get a list of objects from a database based on type.
        
        This method retrieves the list of objects for a specific object
        type and adds it to the class' master object list.
        
        obj_type[in]       Object type (string) e.g. DATABASE
        """

        rows = self.source.get_db_objects(self.db_name, obj_type)
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
        # Get tables
        if not self.skip_tables:
            self.__add_db_objects(TABLE)
        # Get views
        if not self.skip_views:
            self.__add_db_objects(VIEW)
        # Get triggers
        if not self.skip_triggers:
            self.__add_db_objects(TRIGGER)
        # Get stored procedures
        if not self.skip_procs:
            self.__add_db_objects(PROC)
        # Get functions
        if not self.skip_funcs:
            self.__add_db_objects(FUNC)
        # Get events
        if not self.skip_events:
            self.__add_db_objects(EVENT)
        # Get grants
        if not self.skip_grants:
            self.__add_db_objects(GRANT)
        self.init_called = True
    
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
        if obj_type == TABLE and self.cloning:
            create_str = "CREATE TABLE %s.%s LIKE %s.%s" % \
                         (self.new_db, obj[0], self.db_name, obj[0])
        else:
            create_str = self.__make_create_statement(obj_type, obj)
        str = "# Copying"
        if not silent:
            if obj_type == GRANT:
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
            if create_str.find("'%'"):
                create_str = re.sub("'%'", "'%%'", create_str)
            res = self.destination.exec_query(create_str)
        except Exception, e:
            raise MySQLUtilError("Cannot operate on %s object with: %s" % 
                                 (obj_type, create_str))

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
        
    
    def copy(self, new_db, input_file, options, new_server=None):
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
        """
 
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
            if options["copy_dir"]:
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
            if options["force"]:
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
            if options["force"] and obj[0] != GRANT:
                self.__drop_object(obj[0], obj[1][0])
                
            # Create the object
            try:
                self.__create_object(obj[0], obj[1], not grant_msg_displayed,
                                     options["silent"])
            except MySQLUtilError, e:
                raise e
            
            if obj[0] == GRANT and not grant_msg_displayed:
                grant_msg_displayed = True
                
            # Now copy the data if enabled
            if not self.skip_data:
                if obj[0] == TABLE:
                    if self.cloning:
                        self.__copy_table_data(obj[1][0], options["silent"])
                    else:
                        if not options["silent"]:
                            print "# Copying data for TABLE %s.%s" % \
                                   (self.db_name, obj[1][0])
                        self.source.get_table_data(self.db_name,
                                                    obj[1][0],
                                                    copy_file,
                                                    self.verbose,
                                                    new_db)
                        self.destination.read_and_exec_SQL(copy_file,
                                                       self.verbose)
               
        # Read input file if provided
        if input_file:
            if not options["silent"]:
                print "# Reading the file %s to populate the data" % (input_file)
            if self.verbose and not options["silent"]:
                print "# Executing the following data commands:"
            self.source.read_and_exec_SQL(input_file, self.verbose)
        
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

