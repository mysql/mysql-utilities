#
# Copyright (c) 2010, 2013, Oracle and/or its affiliates. All rights reserved.
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
This module contains abstractions of a MySQL Database object used by
multiple utilities.
"""

import re

from mysql.utilities.exception import UtilError, UtilDBError
from mysql.utilities.common.sql_transform import quote_with_backticks
from mysql.utilities.common.sql_transform import remove_backtick_quoting
from mysql.utilities.common.sql_transform import is_quoted_with_backticks

# List of database objects for enumeration
_DATABASE, _TABLE, _VIEW, _TRIG, _PROC, _FUNC, _EVENT, _GRANT = "DATABASE", \
    "TABLE", "VIEW", "TRIGGER", "PROCEDURE", "FUNCTION", "EVENT", "GRANT"

_OBJTYPE_QUERY = """
    (
       SELECT TABLE_TYPE as object_type
       FROM INFORMATION_SCHEMA.TABLES
       WHERE TABLES.TABLE_SCHEMA = '%(db_name)s' AND
         TABLES.TABLE_NAME = '%(obj_name)s'
    )
    UNION
    (
        SELECT 'TRIGGER' as object_type
        FROM INFORMATION_SCHEMA.TRIGGERS
        WHERE TRIGGER_SCHEMA = '%(db_name)s' AND
          TRIGGER_NAME = '%(obj_name)s'
    )
    UNION
    (
        SELECT TYPE as object_type
        FROM mysql.proc
        WHERE DB = '%(db_name)s' AND NAME = '%(obj_name)s'
    )
    UNION
    (
        SELECT 'EVENT' as object_type
        FROM mysql.event
        WHERE DB = '%(db_name)s' AND NAME = '%(obj_name)s'
    )
"""

_DEFINITION_QUERY = """
  SELECT %(columns)s
  FROM INFORMATION_SCHEMA.%(table_name)s WHERE %(conditions)s
"""

_PARTITION_QUERY = """
  SELECT PARTITION_NAME, SUBPARTITION_NAME, PARTITION_ORDINAL_POSITION,
         SUBPARTITION_ORDINAL_POSITION, PARTITION_METHOD, SUBPARTITION_METHOD,
         PARTITION_EXPRESSION, SUBPARTITION_EXPRESSION, PARTITION_DESCRIPTION
  FROM INFORMATION_SCHEMA.PARTITIONS
  WHERE TABLE_SCHEMA = '%(db)s' AND TABLE_NAME = '%(name)s'
"""

_COLUMN_QUERY = """
  SELECT ORDINAL_POSITION, COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE,
         COLUMN_DEFAULT, EXTRA, COLUMN_COMMENT, COLUMN_KEY       
  FROM INFORMATION_SCHEMA.COLUMNS
  WHERE TABLE_SCHEMA = '%(db)s' AND TABLE_NAME = '%(name)s'
"""

class Database(object):
    """
    The Database class encapsulates a database. The class has the following
    capabilities:

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
        # Keep database identifier considering backtick quotes
        if is_quoted_with_backticks(name):
            self.q_db_name = name
            self.db_name = remove_backtick_quoting(self.q_db_name)
        else:
            self.db_name = name
            self.q_db_name = quote_with_backticks(self.db_name)
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
        self.exclude_patterns = options.get("exclude_patterns", None)
        self.use_regexp = options.get("use_regexp", False)
        self.new_db = None
        self.q_new_db = None
        self.init_called = False
        self.destination = None # Used for copy mode
        self.cloning = False    # Used for clone mode
        self.query_options = {  # Used for skipping fetch of rows
            'fetch' : False
        }

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
        db = None
        if db_name:
            db = db_name
        else:
            db = self.db_name
            
        _QUERY = """
            SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA 
            WHERE SCHEMA_NAME = '%s'
        """
        res = server.exec_query(_QUERY % db)
        return (res is not None and len(res) >= 1)


    def drop(self, server, quiet, db_name=None):
        """Drop the database

        server[in]         A Server object
        quiet[in]          ignore error on drop
        db_name[in]        database name
                           (optional) If omitted, operation is performed
                           on the class instance table name.

        return True = database successfully dropped, False = error
        """

        db = None
        if db_name:
            db = db_name if is_quoted_with_backticks(db_name) \
                    else quote_with_backticks(db_name)
        else:
            db = self.q_db_name
        op_ok = False
        if quiet:
            try:
                res = server.exec_query("DROP DATABASE %s" % (db),
                                        self.query_options)
                op_ok = True
            except:
                pass
        else:
            res = server.exec_query("DROP DATABASE %s" % (db),
                                    self.query_options)
            op_ok = True
        return op_ok

    def create(self, server, db_name=None):
        """Create the database

        server[in]         A Server object
        db_name[in]        database name
                           (optional) If omitted, operation is performed
                           on the class instance table name.

        return True = database successfully created, False = error
        """

        db = None
        if db_name:
            db = db_name if is_quoted_with_backticks(db_name) \
                    else quote_with_backticks(db_name)
        else:
            db = self.q_db_name
        op_ok = False
        res = server.exec_query("CREATE DATABASE %s" % (db),
                                self.query_options)
        op_ok = True
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
            self.q_new_db = self.q_db_name
        create_str = None
        # Tables are not supported
        if obj_type == _TABLE and self.cloning:
            return None
        # Grants are a different animal!
        if obj_type == _GRANT:
            if obj[3]:
                create_str = "GRANT %s ON %s.%s TO %s" % \
                             (obj[1], self.q_new_db, obj[3], obj[0])
            else:
                create_str = "GRANT %s ON %s.* TO %s" % \
                             (obj[1], self.q_new_db, obj[0])
        else:
            create_str = self.get_create_statement(self.db_name,
                                                   obj[0], obj_type)
            if self.new_db != self.db_name:
                create_str = re.sub(r" %s\." % self.q_db_name,
                                    r" %s." % self.q_new_db,
                                    create_str)
                create_str = re.sub(r",%s\." % self.q_db_name,
                                    r",%s." % self.q_new_db,
                                    create_str)
                create_str = re.sub(r" %s\." % self.db_name,
                                    r" %s." % self.new_db,
                                    create_str)
                create_str = re.sub(r",%s\." % self.db_name,
                                    r",%s." % self.new_db,
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

        Attempts a quiet drop of a database object (no errors are
        printed).

        obj_type[in]       Object type (string) e.g. DATABASE
        name[in]           Name of the object
        """

        if self.verbose:
            print "# Dropping new object %s %s.%s" % \
                  (obj_type, self.new_db, name)
        drop_str = "DROP %s %s.%s" % \
                   (obj_type, self.q_new_db, name)
        # Suppress the error on drop
        if self.cloning:
            try:
                self.source.exec_query(drop_str, self.query_options)
            except:
                pass
        else:
            try:
                self.destination.exec_query(drop_str, self.query_options)
            except:
                pass


    def __create_object(self, obj_type, obj, show_grant_msg,
                        quiet=False, new_engine=None, def_engine=None):
        """Create a database object.

        obj_type[in]       Object type (string) e.g. DATABASE
        obj[in]            A row from the get_db_object_names() method
                           that contains the elements of the object
        show_grant_msg[in] If true, display diagnostic information
        quiet[in]          do not print informational messages
        new_engine[in]     Use this engine if not None for object
        def_engine[in]     If target storage engine doesn't exist, use
                           this engine.

        Note: will handle exception and print error if query fails
        """

        create_str = None
        if obj_type == _TABLE and self.cloning:
            create_str = "CREATE TABLE %s.%s LIKE %s.%s" % \
                         (self.q_new_db, obj[0], self.q_db_name, obj[0])
        else:
            create_str = self.__make_create_statement(obj_type, obj)
        if obj_type == _TABLE:
            tbl_name = "%s.%s" % (self.q_new_db, obj[0])
            create_str = self.destination.substitute_engine(tbl_name,
                                                            create_str,
                                                            new_engine,
                                                            def_engine,
                                                            quiet)
        str = "# Copying"
        if not quiet:
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
            res = self.destination.exec_query("USE %s" % self.q_new_db,
                                              self.query_options)
        except:
            pass
        try:
            res = self.destination.exec_query(create_str, self.query_options)
        except Exception, e:
            raise UtilDBError("Cannot operate on %s object. Error: %s" %
                              (obj_type, e.errmsg), -1, self.db_name)


    def copy_objects(self, new_db, options, new_server=None,
                     connections=1, check_exists=True):
        """Copy the database objects.

        This method will copy a database and all of its objects and data
        to another, new database. Options set at instantiation will determine
        if there are objects that are excluded from the copy. Likewise,
        the method will also skip data if that option was set and process
        an input file with INSERT statements if that option was set.

        The method can also be used to copy a database to another server
        by providing the new server object (new_server). Copy to the same
        name by setting new_db = old_db or as a new database.
        
        new_db[in]         Name of the new database
        options[in]        Options for copy e.g. force, etc.
        new_server[in]     Connection to another server for copying the db
                           Default is None (copy to same server - clone)
        connections[in]    Number of threads(connections) to use for insert
        check_exists[in]   If True, check for database existance before copy
                           Default is True
        """

        from mysql.utilities.common.table import Table

        # Must call init() first!
        # Guard for init() prerequisite
        assert self.init_called, "You must call db.init() before " + \
                                 "db.copy_objects()."

        grant_msg_displayed = False

        if new_db:
            # Assign new database identifier considering backtick quotes.
            if is_quoted_with_backticks(new_db):
                self.q_new_db = new_db
                self.new_db = remove_backtick_quoting(new_db)
            else:
                self.new_db = new_db
                self.q_new_db = quote_with_backticks(new_db)
        else:
            # If new_db is not defined use the same as source database.
            self.new_db = self.db_name
            self.q_new_db = self.q_db_name

        self.destination = new_server

        # We know we're cloning if there is no new connection.
        self.cloning = (new_server == self.source)

        if self.cloning:
            self.destination = self.source


        # Check to see if database exists
        if check_exists:
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
                    raise UtilDBError("destination database exists. Use "
                                      "--force to overwrite existing "
                                      "database.", -1, new_db)

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
            self.__create_object(obj[0], obj[1], not grant_msg_displayed,
                                 options.get("quiet", False),
                                 options.get("new_engine", None),
                                 options.get("def_engine", None))

            if obj[0] == _GRANT and not grant_msg_displayed:
                grant_msg_displayed = True


    def copy_data(self, new_db, options, new_server=None, connections=1):
        """Copy the data for the tables.

        This method will copy the data for all of the tables to another, new
        database. The method will process an input file with INSERT statements
        if the option was selected by the caller.

        new_db[in]         Name of the new database
        options[in]        Options for copy e.g. force, etc.
        new_server[in]     Connection to another server for copying the db
                           Default is None (copy to same server - clone)
        connections[in]    Number of threads(connections) to use for insert
        """

        from mysql.utilities.common.table import Table

        # Must call init() first!
        # Guard for init() prerequisite
        assert self.init_called, "You must call db.init() before "+ \
                                 "db.copy_data()."

        if self.skip_data:
            return
        
        self.destination = new_server

        # We know we're cloning if there is no new connection.
        self.cloning = (new_server == self.source)

        if self.cloning:
            self.destination = self.source

        quiet = options.get("quiet", False)
        
        tbl_options = {
            'verbose'  : self.verbose,
            'get_cols' : True,
            'quiet'    : quiet
        }

        table_names = [obj[0] for obj in self.get_db_objects(_TABLE)]
        for tblname in table_names:
            if not quiet:
                print "# Copying data for TABLE %s.%s" % (self.db_name, 
                                                          tblname)
            tbl = Table(self.source, "%s.%s" % (self.q_db_name,
                                                quote_with_backticks(tblname)),
                        tbl_options)
            if tbl is None:
                raise UtilDBError("Cannot create table object before copy.",
                                  -1, self.db_name)
            tbl.copy_data(self.destination, self.cloning, new_db, connections)


    def get_create_statement(self, db, name, obj_type):
        """Return the create statement for the object

        db[in]             Database name
        name[in]           Name of the object
        obj_type[in]       Object type (string) e.g. DATABASE
                           Note: this is used to form the correct SHOW command

        Returns create statement
        """

        row = None
        q_name = name if is_quoted_with_backticks(name) \
                                    else quote_with_backticks(name)
        if obj_type == _DATABASE:
            name_str = q_name
        else:
            q_db = db if is_quoted_with_backticks(db) \
                                    else quote_with_backticks(db)
            name_str = q_db + "." + q_name
        row = self.source.exec_query("SHOW CREATE %s %s" % (obj_type,
                                                            name_str))

        create_statement = None
        if row:
            if obj_type == _TABLE or obj_type == _VIEW or \
               obj_type == _DATABASE:
                create_statement = row[0][1]
            elif obj_type == _EVENT:
                create_statement = row[0][3]
            else:
                create_statement = row[0][2]
        return create_statement


    def get_object_definition(self, db, name, obj_type):
        """Return a list of the object's creation metadata.
        
        This method queries the INFORMATION_SCHEMA or MYSQL database for the
        row-based (list) description of the object. This is similar to the
        output EXPLAIN <object>.

        db[in]             Database name
        name[in]           Name of the object
        obj_type[in]       Object type (string) e.g. DATABASE
                           Note: this is used to form the correct SHOW command

        Returns list - object definition, None if db.object does not exist
        """
        definition = []
        from_name = None
        condition = None
        
        if obj_type == _DATABASE:
            columns = 'SCHEMA_NAME, DEFAULT_CHARACTER_SET_NAME, ' + \
                      'DEFAULT_COLLATION_NAME, SQL_PATH'
            from_name = 'SCHEMATA'
            condition = "SCHEMA_NAME = '%s'" % name
        elif obj_type == _TABLE:
            columns = 'TABLE_SCHEMA, TABLE_NAME, ENGINE, AUTO_INCREMENT, ' + \
                      'AVG_ROW_LENGTH, CHECKSUM, TABLE_COLLATION, ' + \
                      'TABLE_COMMENT, ROW_FORMAT, CREATE_OPTIONS'
            from_name = 'TABLES'
            condition = "TABLE_SCHEMA = '%s' AND TABLE_NAME = '%s'" % \
                         (db, name) 
        elif obj_type == _VIEW:
            columns = 'TABLE_SCHEMA, TABLE_NAME, VIEW_DEFINITION, ' + \
                      'CHECK_OPTION, DEFINER, SECURITY_TYPE'
            from_name = 'VIEWS'
            condition = "TABLE_SCHEMA = '%s' AND TABLE_NAME = '%s'" % \
                         (db, name)
        elif obj_type == _TRIG:
            columns = 'TRIGGER_SCHEMA, TRIGGER_NAME, EVENT_MANIPULATION, ' + \
                      'EVENT_OBJECT_TABLE, ACTION_STATEMENT, ' + \
                      'ACTION_TIMING, DEFINER'
            from_name = 'TRIGGERS'
            condition = "TRIGGER_SCHEMA = '%s' AND TRIGGER_NAME = '%s'" % \
                         (db, name)
        elif obj_type == _PROC or obj_type == _FUNC:
            columns = 'ROUTINE_SCHEMA, ROUTINE_NAME, ROUTINE_DEFINITION, ' + \
                      'ROUTINES.SQL_DATA_ACCESS, ROUTINES.SECURITY_TYPE, ' + \
                      'ROUTINE_COMMENT, ROUTINES.DEFINER, param_list, ' + \
                      'DTD_IDENTIFIER, ROUTINES.IS_DETERMINISTIC'
            from_name = 'ROUTINES JOIN mysql.proc ON ' + \
                        'ROUTINES.ROUTINE_SCHEMA = proc.db AND ' + \
                        'ROUTINES.ROUTINE_NAME = proc.name AND ' + \
                        'ROUTINES.ROUTINE_TYPE = proc.type '
            condition = "ROUTINE_SCHEMA = '%s' AND ROUTINE_NAME = '%s'" % \
                         (db, name)
            if obj_type == _PROC:
                type = 'PROCEDURE'
            else:
                type = 'FUNCTION'
            condition += " AND ROUTINE_TYPE = '%s'" % type
        elif obj_type == _EVENT:
            columns = 'EVENT_SCHEMA, EVENT_NAME, DEFINER, EVENT_DEFINITION, ' + \
                      'EVENT_TYPE, INTERVAL_FIELD, INTERVAL_VALUE, STATUS, '+ \
                      'ON_COMPLETION, STARTS, ENDS'
            from_name = 'EVENTS'
            condition = "EVENT_SCHEMA = '%s' AND EVENT_NAME = '%s'" % \
                         (db, name)            

        if from_name is None:
            raise UtilError('Attempting to get definition from unknown object '
                            'type = %s.' % obj_type)

        values = {
            'columns'    : columns,
            'table_name' : from_name,
            'conditions' : condition,
        }
        rows = self.source.exec_query(_DEFINITION_QUERY % values)
        if rows != []:
            # If this is a table, we need three types of information:
            # basic info, column info, and partitions info
            if obj_type == _TABLE:
                values['name'] = name
                values['db'] = db
                basic_def = rows[0]
                col_def = self.source.exec_query(_COLUMN_QUERY % values)
                part_def = self.source.exec_query(_PARTITION_QUERY % \
                                                  values)
                definition.append((basic_def, col_def, part_def))
            else:
                definition.append(rows[0])
            
        return definition
    

    def get_next_object(self):
        """Retrieve the next object in the database list.

        This method is an iterator for retrieving the objects in the database
        as specified in the init() method. You must call this method first.

        Returns next object in list or throws exception at EOL.
        """

        # Must call init() first!
        # Guard for init() prerequisite
        assert self.init_called, "You must call db.init() before db.copy()."

        for obj in self.objects:
            yield obj


    def __build_exclude_patterns(self, exclude_param):
        """Return a string to add to where clause to exclude objects.

        This method will add the conditions to exclude objects based on
        name if there is a dot notation or by a search pattern as specified
        by the options.

        exclude_param[in]  Name of column to check.

        Returns (string) String to add to where clause or ""
        """
        from mysql.utilities.common.options import obj2sql
        
        oper = 'NOT REGEXP' if self.use_regexp else 'NOT LIKE'
        str = ""
        for pattern in self.exclude_patterns:
            value = None
            if pattern.find(".") > 0:
                db, name = pattern.split(".")
                if db == self.db_name:
                    value = name
            else:
                value = pattern
            if value is not None:
                str += " AND {0} {1} {2}".format(exclude_param, oper,
                                                 obj2sql(value))

        return str


    def get_object_type(self, object_name):
        """Return the object type of an object
        
        This method attempts to locate the object name among the objects
        in the database. It returns the object type if found or None
        if not found.
        
        object_name[in]    Name of the object to find
        
        Returns (string) object type or None if not found
        """
        object_type = None

        # Remove object backticks if needed
        obj_name = remove_backtick_quoting(object_name) \
                    if is_quoted_with_backticks(object_name) else object_name

        res = self.source.exec_query(_OBJTYPE_QUERY %
                                     { 'db_name'  : self.db_name,
                                       'obj_name' : obj_name })
        
        if res != [] and res is not None and len(res) > 0:
            object_type = res[0][0]
            if object_type == 'BASE TABLE':
                object_type = 'TABLE'
        
        return object_type


    def get_db_objects(self, obj_type, columns='names', get_columns=False, 
                       need_backtick=False):
        """Return a result set containing a list of objects for a given
        database based on type.

        This method returns either a list of names for the object type
        specified, a brief list of minimal columns for creating the
        objects, or the full list of columns from INFORMATION_SCHEMA. It can
        also provide the list of column names if desired.

        obj_type[in]       Type of object to retrieve
        columns[in]        Column mode - names (default), brief, or full
                           Note: not valid for GRANT objects.
        get_columns[in]    If True, return column names as first element
                           and result set as second element. If False,
                           return only the result set.
        need_backtick[in]  If True, it returns any identifiers, e.g. table and
                           column names, quoted with backticks.
                           By default, False.

        TODO: Change implementation to return classes instead of a result set.

        Returns mysql.connector result set
        """

        exclude_param = ""
        if obj_type == _TABLE:
            _NAMES = """
            SELECT DISTINCT TABLES.TABLE_NAME
            """
            names_pos_to_quote = (0,)
            _FULL = """
            SELECT TABLES.TABLE_CATALOG, TABLES.TABLE_SCHEMA,
                TABLES.TABLE_NAME, TABLES.TABLE_TYPE,
                TABLES.ENGINE, TABLES.VERSION, TABLES.ROW_FORMAT,
                TABLES.TABLE_ROWS, TABLES.AVG_ROW_LENGTH, TABLES.DATA_LENGTH,
                TABLES.MAX_DATA_LENGTH, TABLES.INDEX_LENGTH, TABLES.DATA_FREE,
                TABLES.AUTO_INCREMENT, TABLES.CREATE_TIME, TABLES.UPDATE_TIME,
                TABLES.CHECK_TIME, TABLES.TABLE_COLLATION, TABLES.CHECKSUM,
                TABLES.CREATE_OPTIONS, TABLES.TABLE_COMMENT,
                COLUMNS.ORDINAL_POSITION, COLUMNS.COLUMN_NAME,
                COLUMNS.COLUMN_TYPE, COLUMNS.IS_NULLABLE,
                COLUMNS.COLUMN_DEFAULT, COLUMNS.COLUMN_KEY,
                REFERENTIAL_CONSTRAINTS.CONSTRAINT_NAME,
                REFERENTIAL_CONSTRAINTS.REFERENCED_TABLE_NAME,
                REFERENTIAL_CONSTRAINTS.UNIQUE_CONSTRAINT_NAME,
                REFERENTIAL_CONSTRAINTS.UNIQUE_CONSTRAINT_SCHEMA,
                REFERENTIAL_CONSTRAINTS.UPDATE_RULE,
                REFERENTIAL_CONSTRAINTS.DELETE_RULE,
                KEY_COLUMN_USAGE.CONSTRAINT_NAME,
                KEY_COLUMN_USAGE.COLUMN_NAME AS COL_NAME,
                KEY_COLUMN_USAGE.REFERENCED_TABLE_SCHEMA,
                KEY_COLUMN_USAGE.REFERENCED_COLUMN_NAME
            """
            full_pos_to_quote = (1, 2, 22, 27, 28, 29, 30, 33, 34, 35, 36)
            _MINIMAL = """
            SELECT TABLES.TABLE_SCHEMA, TABLES.TABLE_NAME, TABLES.ENGINE,
                COLUMNS.ORDINAL_POSITION, COLUMNS.COLUMN_NAME,
                COLUMNS.COLUMN_TYPE, COLUMNS.IS_NULLABLE,
                COLUMNS.COLUMN_DEFAULT, COLUMNS.COLUMN_KEY,
                TABLES.TABLE_COLLATION,
                TABLES.CREATE_OPTIONS,
                REFERENTIAL_CONSTRAINTS.CONSTRAINT_NAME,
                REFERENTIAL_CONSTRAINTS.REFERENCED_TABLE_NAME,
                REFERENTIAL_CONSTRAINTS.UNIQUE_CONSTRAINT_NAME,
                REFERENTIAL_CONSTRAINTS.UPDATE_RULE,
                REFERENTIAL_CONSTRAINTS.DELETE_RULE,
                KEY_COLUMN_USAGE.CONSTRAINT_NAME,
                KEY_COLUMN_USAGE.COLUMN_NAME AS COL_NAME,
                KEY_COLUMN_USAGE.REFERENCED_TABLE_SCHEMA,
                KEY_COLUMN_USAGE.REFERENCED_COLUMN_NAME
            """
            minimal_pos_to_quote = (0, 1, 4, 11, 12, 13, 16, 17, 18, 19)
            _OBJECT_QUERY = """
            FROM INFORMATION_SCHEMA.TABLES JOIN INFORMATION_SCHEMA.COLUMNS ON
                TABLES.TABLE_SCHEMA = COLUMNS.TABLE_SCHEMA AND
                TABLES.TABLE_NAME = COLUMNS.TABLE_NAME
            LEFT JOIN INFORMATION_SCHEMA.REFERENTIAL_CONSTRAINTS ON
                TABLES.TABLE_SCHEMA = REFERENTIAL_CONSTRAINTS.CONSTRAINT_SCHEMA
                AND
                TABLES.TABLE_NAME = REFERENTIAL_CONSTRAINTS.TABLE_NAME
            LEFT JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE ON
                TABLES.TABLE_SCHEMA = KEY_COLUMN_USAGE.CONSTRAINT_SCHEMA
                AND
                TABLES.TABLE_NAME = KEY_COLUMN_USAGE.TABLE_NAME
            WHERE TABLES.TABLE_SCHEMA = '%s' AND TABLE_TYPE <> 'VIEW' %s
            ORDER BY TABLES.TABLE_SCHEMA, TABLES.TABLE_NAME,
                     COLUMNS.ORDINAL_POSITION
            """
            exclude_param = "TABLES.TABLE_NAME"
            
        elif obj_type == _VIEW:
            _NAMES = """
            SELECT TABLE_NAME
            """
            names_pos_to_quote = (0,)
            _FULL = """
            SELECT TABLE_CATALOG, TABLE_SCHEMA, TABLE_NAME, VIEW_DEFINITION,
                   CHECK_OPTION, IS_UPDATABLE, DEFINER, SECURITY_TYPE,
                   CHARACTER_SET_CLIENT, COLLATION_CONNECTION
            """
            full_pos_to_quote = (1, 2)
            _MINIMAL = """
            SELECT TABLE_SCHEMA, TABLE_NAME, DEFINER, SECURITY_TYPE,
                   VIEW_DEFINITION, CHECK_OPTION, IS_UPDATABLE,
                   CHARACTER_SET_CLIENT, COLLATION_CONNECTION
            """
            minimal_pos_to_quote = (0, 1)
            _OBJECT_QUERY = """
            FROM INFORMATION_SCHEMA.VIEWS
            WHERE TABLE_SCHEMA = '%s' %s
            """
            exclude_param = "VIEWS.TABLE_NAME"
        elif obj_type == _TRIG:
            _NAMES = """
            SELECT TRIGGER_NAME
            """
            names_pos_to_quote = (0,)
            _FULL = """
            SELECT TRIGGER_CATALOG, TRIGGER_SCHEMA, TRIGGER_NAME,
                   EVENT_MANIPULATION, EVENT_OBJECT_CATALOG,
                   EVENT_OBJECT_SCHEMA, EVENT_OBJECT_TABLE, ACTION_ORDER,
                   ACTION_CONDITION, ACTION_STATEMENT, ACTION_ORIENTATION,
                   ACTION_TIMING, ACTION_REFERENCE_OLD_TABLE, 
                   ACTION_REFERENCE_NEW_TABLE, ACTION_REFERENCE_OLD_ROW,
                   ACTION_REFERENCE_NEW_ROW, CREATED, SQL_MODE, DEFINER,
                   CHARACTER_SET_CLIENT, COLLATION_CONNECTION,
                   DATABASE_COLLATION
            """
            full_pos_to_quote = (1, 2, 5, 6)  # 9 ?
            _MINIMAL = """
            SELECT TRIGGER_NAME, DEFINER, EVENT_MANIPULATION,
                   EVENT_OBJECT_SCHEMA, EVENT_OBJECT_TABLE,
                   ACTION_ORIENTATION, ACTION_TIMING,
                   ACTION_STATEMENT, SQL_MODE,
                   CHARACTER_SET_CLIENT, COLLATION_CONNECTION,
                   DATABASE_COLLATION
            """
            # Note: 7 (ACTION_STATEMENT) might require special handling
            minimal_pos_to_quote = (0, 3, 4)
            _OBJECT_QUERY = """
            FROM INFORMATION_SCHEMA.TRIGGERS
            WHERE TRIGGER_SCHEMA = '%s' %s
            """
            exclude_param = "TRIGGERS.TRIGGER_NAME"
        elif obj_type == _PROC:
            _NAMES = """
            SELECT NAME
            """
            names_pos_to_quote = (0,)
            _FULL = """
            SELECT DB, NAME, TYPE, SPECIFIC_NAME, LANGUAGE, SQL_DATA_ACCESS,
                   IS_DETERMINISTIC, SECURITY_TYPE, PARAM_LIST, RETURNS, BODY,
                   DEFINER, CREATED, MODIFIED, SQL_MODE, COMMENT,
                   CHARACTER_SET_CLIENT, COLLATION_CONNECTION, DB_COLLATION,
                   BODY_UTF8
            """
            full_pos_to_quote = (0, 1, 3)
            _MINIMAL = """
            SELECT NAME, LANGUAGE, SQL_DATA_ACCESS, IS_DETERMINISTIC,
                   SECURITY_TYPE, DEFINER, PARAM_LIST, RETURNS,
                   BODY, SQL_MODE,
                   CHARACTER_SET_CLIENT, COLLATION_CONNECTION,
                   DB_COLLATION
            """
            minimal_pos_to_quote = (0,)
            _OBJECT_QUERY = """
            FROM mysql.proc
            WHERE DB = '%s' AND TYPE = 'PROCEDURE' %s
            """
            exclude_param = "NAME"
        elif obj_type == _FUNC:
            _NAMES = """
            SELECT NAME
            """
            names_pos_to_quote = (0,)
            _FULL = """
            SELECT DB, NAME, TYPE, SPECIFIC_NAME, LANGUAGE, SQL_DATA_ACCESS,
                   IS_DETERMINISTIC, SECURITY_TYPE, PARAM_LIST, RETURNS, BODY,
                   DEFINER, CREATED, MODIFIED, SQL_MODE, COMMENT,
                   CHARACTER_SET_CLIENT, COLLATION_CONNECTION, DB_COLLATION,
                   BODY_UTF8
            """
            full_pos_to_quote = (0, 1, 3)
            _MINIMAL = """
            SELECT NAME, LANGUAGE, SQL_DATA_ACCESS, IS_DETERMINISTIC,
                   SECURITY_TYPE, DEFINER, PARAM_LIST, RETURNS,
                   BODY, SQL_MODE,
                   CHARACTER_SET_CLIENT, COLLATION_CONNECTION,
                   DB_COLLATION
            """
            minimal_pos_to_quote = (0,)
            _OBJECT_QUERY = """
            FROM mysql.proc
            WHERE DB = '%s' AND TYPE = 'FUNCTION' %s
            """
            exclude_param = "NAME"
        elif obj_type == _EVENT:
            _NAMES = """
            SELECT NAME
            """
            names_pos_to_quote = (0,)
            _FULL = """
            SELECT DB, NAME, BODY, DEFINER, EXECUTE_AT, INTERVAL_VALUE,
                   INTERVAL_FIELD, CREATED, MODIFIED, LAST_EXECUTED, STARTS,
                   ENDS, STATUS, ON_COMPLETION, SQL_MODE, COMMENT, ORIGINATOR,
                   TIME_ZONE, CHARACTER_SET_CLIENT, COLLATION_CONNECTION,
                   DB_COLLATION, BODY_UTF8
            """
            full_pos_to_quote = (0, 1)
            _MINIMAL = """
            SELECT NAME, DEFINER, BODY, STATUS,
                   EXECUTE_AT, INTERVAL_VALUE, INTERVAL_FIELD, SQL_MODE,
                   STARTS, ENDS, STATUS, ON_COMPLETION, ORIGINATOR,
                   CHARACTER_SET_CLIENT, COLLATION_CONNECTION,
                   DB_COLLATION
            """
            minimal_pos_to_quote = (0,)
            _OBJECT_QUERY = """
            FROM mysql.event
            WHERE DB = '%s' %s
            """
            exclude_param = "NAME"
        elif obj_type == _GRANT:
            _OBJECT_QUERY = """
            (
                SELECT GRANTEE, PRIVILEGE_TYPE, TABLE_SCHEMA,
                       NULL as TABLE_NAME, NULL AS COLUMN_NAME,
                       NULL AS ROUTINE_NAME
                FROM INFORMATION_SCHEMA.SCHEMA_PRIVILEGES
                WHERE table_schema = '%s'
            ) UNION (
                SELECT grantee, privilege_type, table_schema, table_name,
                       NULL, NULL
                FROM INFORMATION_SCHEMA.TABLE_PRIVILEGES
                WHERE table_schema = '%s'
            ) UNION (
                SELECT grantee, privilege_type, table_schema, table_name,
                       column_name, NULL
                FROM INFORMATION_SCHEMA.COLUMN_PRIVILEGES
                WHERE table_schema = '%s'
            ) UNION (
                SELECT CONCAT('''', User, '''@''', Host, ''''),  Proc_priv, Db,
                       Routine_name, NULL, Routine_type
                FROM mysql.procs_priv WHERE Db = '%s'
            ) ORDER BY GRANTEE ASC, PRIVILEGE_TYPE ASC, TABLE_SCHEMA ASC,
                       TABLE_NAME ASC, COLUMN_NAME ASC, ROUTINE_NAME ASC
            """
        else:
            return None

        col_options = {
            'columns' : get_columns
        }
        pos_to_quote = ()
        if obj_type == _GRANT:
            query = _OBJECT_QUERY % (self.db_name, self.db_name,
                                     self.db_name, self.db_name)
            return self.source.exec_query(query, col_options)
        else:
            if columns == "names":
                prefix = _NAMES
                if need_backtick:
                    pos_to_quote = names_pos_to_quote
            elif columns == "full":
                prefix = _FULL
                if need_backtick:
                    pos_to_quote = full_pos_to_quote
            else:
                prefix = _MINIMAL
                if need_backtick:
                    pos_to_quote = minimal_pos_to_quote
            # Form exclusion string
            exclude_str = ""
            if self.exclude_patterns is not None:
                exclude_str += self.__build_exclude_patterns(exclude_param)
            query = prefix + _OBJECT_QUERY % (self.db_name, exclude_str)
            res = self.source.exec_query(query, col_options)

            # Quote required identifiers with backticks
            if need_backtick:
                # function to quote row elements at a given positions
                #quote = lambda pos, obj: quote_with_backticks(obj) \
                #                        if obj and pos in pos_to_quote else obj
                new_rows = []
                for row in res[1]:
                    # recreate row tuple quoting needed elements with backticks
                    #r = tuple([quote(i, data) for i, data in enumerate(row)])
                    r = tuple([quote_with_backticks(data)
                               if data and i in pos_to_quote else data
                               for i, data in enumerate(row)])
                    new_rows.append(r)

                # set new result with with required data quoted with backticks
                res = (res[0], new_rows)

            return res


    def _check_user_permissions(self, uname, host, access):
        """Check user permissions for a given privilege

        uname[in]          user name to check
        host[in]           host name of connection
        acess[in]          privilege to check (e.g. "SELECT")

        Returns True if user has permission, False if not
        """

        from mysql.utilities.common.user import User

        user = User(self.source, uname+'@'+host)
        result = user.has_privilege(access[0], '*', access[1])
        return result


    def check_read_access(self, user, host, options):
        """Check access levels for reading database objects

        This method will check the user's permission levels for copying a
        database from this server.

        It will also skip specific checks if certain objects are not being
        copied (i.e., views, procs, funcs, grants).
    
        user[in]           user name to check
        host[in]           host name to check
        options[in]        dictionary of values to include:
            skip_views     True = no views processed
            skip_proc      True = no procedures processed
            skip_func      True = no functions processed
            skip_grants    True = no grants processed
            skip_events    True = no events processed

        Returns True if user has permissions and raises a UtilDBError if the
                     user does not have permission with a message that includes
                     the server context.
        """

        # Build minimal list of privileges for source access
        source_privs = []
        priv_tuple = (self.db_name, "SELECT")
        source_privs.append(priv_tuple)
        # if views are included, we need SHOW VIEW
        if not options.get('skip_views', False):
            priv_tuple = (self.db_name, "SHOW VIEW")
            source_privs.append(priv_tuple)
        # if procs or funcs are included, we need read on mysql db
        if not options.get('skip_proc', False) or \
           not options.get('skip_func', False):
            priv_tuple = ("mysql", "SELECT")
            source_privs.append(priv_tuple)
        # if events, we need event
        if not options.get('skip_events', False):
            priv_tuple = (self.db_name, "EVENT")
            source_privs.append(priv_tuple)

        # Check permissions on source
        for priv in source_privs:
            if not self._check_user_permissions(user, host, priv):
                raise UtilDBError("User %s on the %s server does not have "
                                  "permissions to read all objects in %s. " %
                                   (user, self.source.role, self.db_name) +
                                   "User needs %s privilege on %s." %
                                   (priv[1], priv[0]), -1, priv[0])

        return True


    def check_write_access(self, user, host, options):
        """Check access levels for creating and writing database objects

        This method will check the user's permission levels for copying a
        database to this server.

        It will also skip specific checks if certain objects are not being
        copied (i.e., views, procs, funcs, grants).

        user[in]           user name to check
        host[in]           host name to check
        options[in]        dictionary of values to include:
            skip_views     True = no views processed
            skip_proc      True = no procedures processed
            skip_func      True = no functions processed
            skip_grants    True = no grants processed
            skip_events    True = no events processed


        Returns True if user has permissions and raises a UtilDBError if the
                     user does not have permission with a message that includes
                     the server context.
        """

        dest_privs = [(self.db_name, "CREATE"),
                      (self.db_name, "SUPER"),
                      ("*", "SUPER")]
        if not options.get('skip_grants', False):
            priv_tuple = (self.db_name, "WITH GRANT OPTION")
            dest_privs.append(priv_tuple)

        # Check privileges on destination
        for priv in dest_privs:
            if not self._check_user_permissions(user, host, priv):
                raise UtilDBError("User %s on the %s server does not "
                                  "have permissions to create all objects "
                                  "in %s. User needs %s privilege on %s." %
                                  (user, self.source.role, priv[0], priv[1],
                                   priv[0]), -1, priv[0])

        return True
