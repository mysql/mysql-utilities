#
# Copyright (c) 2010, 2016, Oracle and/or its affiliates. All rights reserved.
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

import multiprocessing
import os
import re
import sys

from collections import deque

from mysql.utilities.exception import UtilError, UtilDBError
from mysql.utilities.common.pattern_matching import parse_object_name
from mysql.utilities.common.options import obj2sql
from mysql.utilities.common.server import connect_servers, Server
from mysql.utilities.common.user import User
from mysql.utilities.common.sql_transform import (quote_with_backticks,
                                                  remove_backtick_quoting,
                                                  is_quoted_with_backticks)

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

_FK_CONSTRAINT_QUERY = """
SELECT TABLE_NAME, CONSTRAINT_NAME, COLUMN_NAME, REFERENCED_TABLE_SCHEMA,
REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME, UPDATE_RULE, DELETE_RULE
FROM INFORMATION_SCHEMA.REFERENTIAL_CONSTRAINTS
JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE
USING (CONSTRAINT_SCHEMA, CONSTRAINT_NAME, TABLE_NAME, REFERENCED_TABLE_NAME)
WHERE CONSTRAINT_SCHEMA = '{DATABASE!s}'
AND TABLE_NAME = '{TABLE!s}'
"""

_ALTER_TABLE_ADD_FK_CONSTRAINT = """
ALTER TABLE {DATABASE!s}.{TABLE!s} add CONSTRAINT `{CONSTRAINT_NAME!s}`
FOREIGN KEY (`{COLUMN_NAMES}`)
REFERENCES `{REFERENCED_DATABASE}`.`{REFERENCED_TABLE!s}`
(`{REFERENCED_COLUMNS!s}`)
ON UPDATE {UPDATE_RULE}
ON DELETE {DELETE_RULE}
"""


def _multiprocess_tbl_copy_task(copy_tbl_task):
    """Multiprocess copy table data method.

    This method wraps the copy of the table's data to allow its concurrent
    execution by a pool of processes.

    copy_tbl_task[in]   dictionary of values required by a process to
                        perform the table copy task, namely:
                        'source_srv': <dict with source connections values>,
                        'dest_srv': <dict with destination connections values>,
                        'source_db': <source database name>,
                        'destination_db': <destination database name>,
                        'table': <table to copy>,
                        'options': <dict of options>,
                        'cloning': <cloning flag>,
                        'connections': <number of concurrent connections>,
                        'q_source_db': <quoted source database name>.
    """
    # Get input to execute task.
    source_srv = copy_tbl_task.get('source_srv')
    dest_srv = copy_tbl_task.get('dest_srv')
    source_db = copy_tbl_task.get('source_db')
    target_db = copy_tbl_task.get('target_db')
    table = copy_tbl_task.get('table')
    options = copy_tbl_task.get('options')
    cloning = copy_tbl_task.get('cloning')
    # Execute copy table task.
    # NOTE: Must handle any exception here, because worker processes will not
    # propagate them to the main process.
    try:
        _copy_table_data(source_srv, dest_srv, source_db, target_db, table,
                         options, cloning)
    except UtilError:
        _, err, _ = sys.exc_info()
        print("ERROR copying data for table '{0}': {1}".format(table,
                                                               err.errmsg))


def _copy_table_data(source_srv, destination_srv, db_name, new_db_name,
                     tbl_name, tbl_options, cloning, connections=1):
    """Copy the data of the specified table.

    This method copies/clones all the data from a table to another (new)
    database.

    source_srv[in]      Source server (Server instance or dict. with the
                        connection values).
    destination_srv[in] Destination server (Server instance or dict. with the
                        connection values).
    db_name[in]         Name of the database with the table to copy.
    new_db_name[in]     Name of the destination database to copy the table.
    tbl_name[in]        Name of the table to copy.
    tbl_options[in]     Table options.
    cloning[in]         Cloning flag, in order to use a different method to
                        copy data on the same server
    connections[in]     Specify the use of multiple connections/processes to
                        copy the table data (rows). By default, only 1 used.
                        Note: Multiprocessing option should be preferred.
    """
    # Import table needed here to avoid circular import issues.
    from mysql.utilities.common.table import Table
    # Handle source and destination server instances or connection values.
    # Note: For multiprocessing the use of connection values instead of a
    # server instance is required to avoid internal errors.
    if isinstance(source_srv, Server):
        source = source_srv
    else:
        # Get source server instance from connection values.
        conn_options = {
            'quiet': True,  # Avoid repeating output for multiprocessing.
            'version': "5.1.30",
        }
        servers = connect_servers(source_srv, None, conn_options)
        source = servers[0]
    if isinstance(destination_srv, Server):
        destination = destination_srv
    else:
        # Get source server instance from connection values.
        conn_options = {
            'quiet': True,  # Avoid repeating output for multiprocessing.
            'version': "5.1.30",
        }
        servers = connect_servers(destination_srv, None, conn_options)
        destination = servers[0]

    # Copy table data.
    if not tbl_options.get("quiet", False):
        print("# Copying data for TABLE {0}.{1}".format(db_name,
                                                        tbl_name))
    source_sql_mode = source.select_variable("SQL_MODE")
    q_tbl_name = "{0}.{1}".format(quote_with_backticks(db_name,
                                                       source_sql_mode),
                                  quote_with_backticks(tbl_name,
                                                       source_sql_mode))
    tbl = Table(source, q_tbl_name, tbl_options)
    if tbl is None:
        raise UtilDBError("Cannot create table object before copy.", -1,
                          db_name)
    tbl.copy_data(destination, cloning, new_db_name, connections)


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

    def __init__(self, source, name, options=None):
        """Constructor

        source[in]         A Server object
        name[in]           Name of database
        verbose[in]        print extra data during operations (optional)
                           default value = False
        options[in]        Array of options for controlling what is included
                           and how operations perform (e.g., verbose)
        """
        if options is None:
            options = {}
        self.source = source
        # Get the SQL_MODE set on the source
        self.sql_mode = self.source.select_variable("SQL_MODE")
        # Keep database identifier considering backtick quotes
        if is_quoted_with_backticks(name, self.sql_mode):
            self.q_db_name = name
            self.db_name = remove_backtick_quoting(self.q_db_name,
                                                   self.sql_mode)
        else:
            self.db_name = name
            self.q_db_name = quote_with_backticks(self.db_name,
                                                  self.sql_mode)
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
        self.skip_table_opts = options.get("skip_table_opts", False)
        self.new_db = None
        self.q_new_db = None
        self.init_called = False
        self.destination = None  # Used for copy mode
        self.cloning = False    # Used for clone mode
        self.query_options = {  # Used for skipping buffered fetch of rows
            'fetch': False,
            'commit': False,  # No COMMIT needed for DDL operations (default).
        }
        # Used to store constraints to execute
        # after table creation, deque is
        # thread-safe
        self.constraints = deque()

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
        # Get the SQL_MODE set on the server
        sql_mode = server.select_variable("SQL_MODE")
        if db_name:
            db = db_name if is_quoted_with_backticks(db_name, sql_mode) \
                else quote_with_backticks(db_name, sql_mode)
        else:
            db = self.q_db_name
        op_ok = False
        if quiet:
            try:
                server.exec_query("DROP DATABASE %s" % (db),
                                  self.query_options)
                op_ok = True
            except:
                pass
        else:
            server.exec_query("DROP DATABASE %s" % (db),
                              self.query_options)
            op_ok = True
        return op_ok

    def create(self, server, db_name=None, charset_name=None,
               collation_name=None):
        """Create the database

        server[in]         A Server object
        db_name[in]        database name
                           (optional) If omitted, operation is performed
                           on the class instance table name.

        return True = database successfully created, False = error
        """
        # Get the SQL_MODE set on the server
        sql_mode = server.select_variable("SQL_MODE")
        if db_name:
            db = db_name if is_quoted_with_backticks(db_name, sql_mode) \
                else quote_with_backticks(db_name, sql_mode)
        else:
            db = self.q_db_name

        specification = ""
        if charset_name:
            specification = " DEFAULT CHARACTER SET {0}".format(charset_name)
        if collation_name:
            specification = "{0} DEFAULT COLLATE {1}".format(specification,
                                                             collation_name)
        query_create_db = "CREATE DATABASE {0} {1}".format(db, specification)
        server.exec_query(query_create_db, self.query_options)

        return True

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
                # Replace the occurrences of the old database name (quoted with
                # backticks) with the new one when preceded by: a whitespace
                # character, comma or optionally a left parentheses.
                create_str = re.sub(
                    r"(\s|,)(\(?){0}\.".format(self.q_db_name),
                    r"\1\2{0}.".format(self.q_new_db),
                    create_str
                )
                # Replace the occurrences of the old database name (without
                # backticks) with the new one when preceded by: a whitespace
                # character, comma or optionally a left parentheses and
                # surrounded by single or double quotes.
                create_str = re.sub(
                    r"(\s|,)(\(?)(\"|\'?){0}(\"|\'?)\.".format(self.db_name),
                    r"\1\2\3{0}\4.".format(self.new_db),
                    create_str
                )
        return create_str

    def _get_views_sorted_by_dependencies(self, views, columns,
                                          need_backtick=True):
        """Get a list of views sorted by their dependencies.

        views[in]          List of views objects
        columns[in]        Column mode - names (default), brief, or full
        need_backtick[in]  True if view need backticks in the name

        Returns the list of view sorted by their dependencies
        """
        if columns == "names":
            name_idx = 0
        elif columns == "full":
            name_idx = 2
        else:
            name_idx = 1

        def _get_dependent_views(view, v_name_dict):
            """Get a list with all the dependent views for a given view
            view          [in]  current view being analyzed
            v_name_dict   [in]  mapping from short view names to used view_stm
            """
            # Get view name and use backticks if necessary
            v_name = view[name_idx]
            if need_backtick:
                v_name = quote_with_backticks(v_name, self.sql_mode)

            # Get view create statement and for each view in views_to_check
            # see if it is mentioned in the statement
            stmt = self.get_create_statement(self.db_name, v_name, _VIEW)
            base_views = []
            for v in v_name_dict:
                # No looking for itself
                if v != v_name:
                    # split off the from clause
                    # strip WHERE, ORDER BY, and GROUP BY
                    try:
                        from_clause = stmt.rsplit('from', 1)[1]
                        from_clause = from_clause.split('WHERE', 1)[0]
                    except:
                        from_clause = None
                    if from_clause:
                        index = from_clause.find(v)
                    else:
                        index = stmt.find(v)
                    if index >= 0:
                        base_views.append(v_name_dict[v])
            return base_views

        def build_view_deps(view_lst):
            """Get a list of views sorted by their dependencies.

            view_lst   [in]   list with views yet to to be ordered

            Returns the list of view sorted by their dependencies
            """
            # Mapping from view_names to views(brief, name or full)
            v_name_dict = {}
            for view in view_lst:
                key = quote_with_backticks(view[name_idx], self.sql_mode) if \
                    need_backtick else view[name_idx]
                v_name_dict[key] = view

            # Initialize sorted_tpl
            sorted_views = []
            # set with view whose dependencies were/are being analyzed.key
            visited_views = set()

            # set with views that have already been processed
            # (subset of processed_views). Contains the same elements as
            # sorted_views.
            processed_views = set()

            # Init stack
            view_stack = view_lst[:]
            while view_stack:
                curr_view = view_stack[-1]  # look at top of the stack
                if curr_view in visited_views:
                    view_stack.pop()
                    if curr_view not in processed_views:
                        sorted_views.append(curr_view)
                        processed_views.add(curr_view)
                else:
                    visited_views.add(curr_view)
                    children_views = _get_dependent_views(curr_view,
                                                          v_name_dict)
                    if children_views:
                        for child in children_views:
                            # store not yet processed base views the temp stack
                            if child not in processed_views:
                                view_stack.append(child)
            # No more views on the stack, return list of sorted views
            return sorted_views
        # Returns without columns names
        if isinstance(views[0], tuple):
            return build_view_deps(views)

        # Returns the tuple reconstructed with views sorted
        return (views[0], build_view_deps(views[1]),)

    def __add_db_objects(self, obj_type):
        """Get a list of objects from a database based on type.

        This method retrieves the list of objects for a specific object
        type and adds it to the class' master object list.

        obj_type[in]       Object type (string) e.g. DATABASE
        """

        rows = self.get_db_objects(obj_type)
        if rows:
            for row in rows:
                tup = (obj_type, row)
                self.objects.append(tup)

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
        # Get functions
        if not self.skip_funcs:
            self.__add_db_objects(_FUNC)
        # Get stored procedures
        if not self.skip_procs:
            self.__add_db_objects(_PROC)
        # Get views
        if not self.skip_views:
            self.__add_db_objects(_VIEW)
        # Get triggers
        if not self.skip_triggers:
            self.__add_db_objects(_TRIG)
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
            except UtilError:
                if self.verbose:
                    print("# WARNING: Unable to drop {0} from {1} database "
                          "(object may not exist): {2}".format(name,
                                                               "source",
                                                               drop_str))
        else:
            try:
                self.destination.exec_query(drop_str, self.query_options)
            except UtilError:
                if self.verbose:
                    print("# WARNING: Unable to drop {0} from {1} database "
                          "(object may not exist): {2}".format(name,
                                                               "destination",
                                                               drop_str))

    def __create_object(self, obj_type, obj, show_grant_msg,
                        quiet=True, new_engine=None, def_engine=None):
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
        # Use the sql_mode set on destination server
        dest_sql_mode = self.destination.select_variable("SQL_MODE")
        q_new_db = quote_with_backticks(self.new_db, dest_sql_mode)
        q_db_name = quote_with_backticks(self.db_name, dest_sql_mode)
        if obj_type == _TABLE and self.cloning:
            obj_name = quote_with_backticks(obj[0], dest_sql_mode)
            create_list = [
                "CREATE TABLE {0!s}.{1!s} LIKE {2!s}.{1!s}"
                "".format(q_new_db, obj_name, q_db_name)
            ]
        else:
            create_list = [self.__make_create_statement(obj_type, obj)]
        if obj_type == _TABLE:
            may_skip_fk = False  # Check possible issues with FK Constraints
            obj_name = quote_with_backticks(obj[0], dest_sql_mode)
            tbl_name = "%s.%s" % (self.q_new_db, obj_name)
            create_list = self.destination.substitute_engine(tbl_name,
                                                             create_list[0],
                                                             new_engine,
                                                             def_engine,
                                                             quiet)

            # Get storage engines from the source table and destination table
            # If the source table's engine is INNODB and the destination is
            # not we will loose any FK constraints that may exist
            src_eng = self.get_object_definition(self.q_db_name,
                                                 obj[0], obj_type)[0][0][2]
            dest_eng = None

            # Information about the engine is always in the last statement of
            # the list, be it a regular create table statement or a create
            # table; alter table statement.
            i = create_list[-1].find("ENGINE=")
            if i > 0:
                j = create_list[-1].find(" ", i)
                dest_eng = create_list[-1][i + 7:j]
            dest_eng = dest_eng or src_eng

            if src_eng.upper() == 'INNODB' and dest_eng.upper() != 'INNODB':
                may_skip_fk = True

        string = "# Copying"
        if not quiet:
            if obj_type == _GRANT:
                if show_grant_msg:
                    print "%s GRANTS from %s" % (string, self.db_name)
            else:
                print "%s %s %s.%s" % \
                      (string, obj_type, self.db_name, obj[0])
            if self.verbose:
                print("; ".join(create_list))

        try:
            self.destination.exec_query("USE %s" % self.q_new_db,
                                        self.query_options)
        except:
            pass
        for stm in create_list:
            try:
                if obj_type == _GRANT:
                    user = User(self.destination, obj[0])
                    if not user.exists():
                        user.create()
                self.destination.exec_query(stm, self.query_options)
            except UtilDBError as e:
                raise UtilDBError("Cannot operate on {0} object."
                                  " Error: {1}".format(obj_type, e.errmsg),
                                  -1, self.db_name)

        # Look for foreign key constraints
        if obj_type == _TABLE:
            params = {
                'DATABASE': self.db_name,
                'TABLE': obj[0],
            }
            try:
                query = _FK_CONSTRAINT_QUERY.format(**params)
                fkey_constr = self.source.exec_query(query)
            except UtilDBError as e:
                raise UtilDBError("Unable to obtain Foreign Key constraint "
                                  "information for table {0}.{1}. "
                                  "Error: {2}".format(self.db_name, obj[0],
                                                      e.errmsg), -1,
                                  self.db_name)

            # Get information about the foreign keys of the table being
            # copied/cloned.
            if fkey_constr and not may_skip_fk:

                # Create a constraint dictionary with the constraint
                # name as key
                constr_dict = {}

                # This list is used to ensure the same constraints are applied
                # in the same order, because iterating the dictionary doesn't
                # offer any guarantees regarding order, and Python 2.6 has
                # no ordered_dict
                constr_lst = []

                for fkey in fkey_constr:
                    params = constr_dict.get(fkey[1])
                    # in case the constraint entry already exists, it means it
                    # is composite, just update the columns names and
                    # referenced column fields
                    if params:
                        params['COLUMN_NAMES'].append(fkey[2])
                        params['REFERENCED_COLUMNS'].append(fkey[5])
                    else:  # else create a new entry
                        constr_lst.append(fkey[1])
                        constr_dict[fkey[1]] = {
                            'DATABASE': self.new_db,
                            'TABLE': fkey[0],
                            'CONSTRAINT_NAME': fkey[1],
                            'COLUMN_NAMES': [fkey[2]],
                            'REFERENCED_DATABASE': fkey[3],
                            'REFERENCED_TABLE': fkey[4],
                            'REFERENCED_COLUMNS': [fkey[5]],
                            'UPDATE_RULE': fkey[6],
                            'DELETE_RULE': fkey[7],
                        }
                # Iterate all the constraints and get the necessary parameters
                # to create the query
                for constr in constr_lst:
                    params = constr_dict[constr]
                    if self.cloning:  # if it is a cloning table operation

                        # In case the foreign key is composite we need to join
                        # the columns to use in in alter table query. Only
                        # useful when cloning
                        params['COLUMN_NAMES'] = '`,`'.join(
                            params['COLUMN_NAMES'])
                        params['REFERENCED_COLUMNS'] = '`,`'.join(
                            params['REFERENCED_COLUMNS'])

                        # If the foreign key points to a table under the
                        # database being cloned, change the referenced database
                        #  name to the new cloned database
                        if params['REFERENCED_DATABASE'] == self.db_name:
                            params['REFERENCED_DATABASE'] = self.new_db
                        else:
                            print("# WARNING: The database being cloned has "
                                  "external Foreign Key constraint "
                                  "dependencies, {0}.{1} depends on {2}."
                                  "{3}".format(params['DATABASE'],
                                               params['TABLE'],
                                               params['REFERENCED_DATABASE'],
                                               params['REFERENCED_TABLE']))
                        query = _ALTER_TABLE_ADD_FK_CONSTRAINT.format(**params)

                        # Store constraint query for later execution
                        self.constraints.append(query)
                        if self.verbose:
                            print(query)
                    else:  # if we are copying
                        if params['REFERENCED_DATABASE'] != self.db_name:
                            # if the table being copied has dependencies
                            # to external databases
                            print("# WARNING: The database being copied has "
                                  "external Foreign Key constraint "
                                  "dependencies, {0}.{1} depends on {2}."
                                  "{3}".format(params['DATABASE'],
                                               params['TABLE'],
                                               params['REFERENCED_DATABASE'],
                                               params['REFERENCED_TABLE']))
            elif fkey_constr and may_skip_fk:
                print("# WARNING: FOREIGN KEY constraints for table {0}.{1} "
                      "are missing because the new storage engine for "
                      "the table is not InnoDB".format(self.new_db, obj[0]))

    def __apply_constraints(self):
        """This method applies to the database the constraints stored in the
        self.constraints instance variable
        """

        # Enable Foreign Key Checks to prevent the swapping of
        # RESTRICT referential actions with NO ACTION
        query_opts = {'fetch': False, 'commit': False}
        self.destination.exec_query("SET FOREIGN_KEY_CHECKS=1", query_opts)

        # while constraint queue is not empty
        while self.constraints:
            try:
                query = self.constraints.pop()
            except IndexError:
                # queue is empty, exit while statement
                break
            if self.verbose:
                print(query)
            try:
                self.destination.exec_query(query, query_opts)
            except UtilDBError as err:
                raise UtilDBError("Unable to execute constraint query "
                                  "{0}. Error: {1}".format(query, err.errmsg),
                                  -1, self.new_db)

        # Turn Foreign Key Checks off again
        self.destination.exec_query("SET FOREIGN_KEY_CHECKS=0", query_opts)

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
        options[in]        Options for copy e.g. do_drop, etc.
        new_server[in]     Connection to another server for copying the db
                           Default is None (copy to same server - clone)
        connections[in]    Number of threads(connections) to use for insert
        check_exists[in]   If True, check for database existence before copy
                           Default is True
        """

        # Must call init() first!
        # Guard for init() prerequisite
        assert self.init_called, "You must call db.init() before " + \
                                 "db.copy_objects()."

        grant_msg_displayed = False

        # Get sql_mode in new_server
        sql_mode = new_server.select_variable("SQL_MODE")

        if new_db:
            # Assign new database identifier considering backtick quotes.
            if is_quoted_with_backticks(new_db, sql_mode):
                self.q_new_db = new_db
                self.new_db = remove_backtick_quoting(new_db, sql_mode)
            else:
                self.new_db = new_db
                self.q_new_db = quote_with_backticks(new_db, sql_mode)
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
            if self.cloning:
                exists = self.exists(self.source, new_db)
                drop_server = self.source
            else:
                exists = self.exists(self.destination, new_db)
                drop_server = self.destination
            if exists:
                if options.get("do_drop", False):
                    self.drop(drop_server, True, new_db)
                elif not self.skip_create:
                    raise UtilDBError("destination database exists. Use "
                                      "--drop-first to overwrite existing "
                                      "database.", -1, new_db)

        db_name = self.db_name
        definition = self.get_object_definition(db_name, db_name, _DATABASE)
        _, character_set, collation, _ = definition[0]
        # Create new database first
        if not self.skip_create:
            if self.cloning:
                self.create(self.source, new_db, character_set,
                            collation)
            else:
                self.create(self.destination, new_db, character_set,
                            collation)

        # Get sql_mode set on destination server
        dest_sql_mode = self.destination.select_variable("SQL_MODE")

        # Create the objects in the new database
        # Save any views that fail due to dependencies
        dependent_views = []
        for obj in self.objects:
            # Drop object if --drop-first specified and database not dropped
            # Grants do not need to be dropped for overwriting
            if options.get("do_drop", False) and obj[0] != _GRANT:
                obj_name = quote_with_backticks(obj[1][0], dest_sql_mode)
                self.__drop_object(obj[0], obj_name)

            # Attempt to create the object.
            try:
                # Create the object
                self.__create_object(obj[0], obj[1], not grant_msg_displayed,
                                     options.get("quiet", False),
                                     options.get("new_engine", None),
                                     options.get("def_engine", None))
            except UtilDBError as err:
                # If this is a view and it fails dependency checking, save
                # it and retry the view later, but only if we're not skipping
                # tables.
                if (obj[0] == _VIEW and "doesn't exist" in err.errmsg and
                        not self.skip_tables):
                    dependent_views.append(obj)
                else:
                    raise err

            if obj[0] == _GRANT and not grant_msg_displayed:
                grant_msg_displayed = True

        # Now retry the views
        if self.verbose and len(dependent_views) > 0:
            print("# Attempting to create views that failed dependency "
                  "checks on first pass.")
        for obj in dependent_views:
            # Drop object if --drop-first specified and database not dropped
            if self.verbose:
                print("#  Retrying view {0}".format(obj[1]))
            if options.get("do_drop", False):
                obj_name = quote_with_backticks(obj[1][0], dest_sql_mode)
                self.__drop_object(obj[0], obj_name)

            # Create the object
            self.__create_object(obj[0], obj[1], not grant_msg_displayed,
                                 options.get("quiet", False),
                                 options.get("new_engine", None),
                                 options.get("def_engine", None))

        # After object creation, add the constraints
        if self.constraints:
            self.__apply_constraints()

    def copy_data(self, new_db, options, new_server=None, connections=1,
                  src_con_val=None, dest_con_val=None):
        """Copy the data for the tables.

        This method will copy the data for all of the tables to another, new
        database. The method will process an input file with INSERT statements
        if the option was selected by the caller.

        new_db[in]          Name of the new database
        options[in]         Options for copy e.g. do_drop, etc.
        new_server[in]      Connection to another server for copying the db
                            Default is None (copy to same server - clone)
        connections[in]     Number of threads(connections) to use for insert
        src_con_val[in]     Dict. with the connection values of the source
                            server (required for multiprocessing).
        dest_con_val[in]    Dict. with the connection values of the
                            destination server (required for multiprocessing).
        """

        # Must call init() first!
        # Guard for init() prerequisite
        assert self.init_called, "You must call db.init() before " + \
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
            'verbose': self.verbose,
            'get_cols': True,
            'quiet': quiet
        }

        copy_tbl_tasks = []
        table_names = [obj[0] for obj in self.get_db_objects(_TABLE)]
        for tblname in table_names:
            # Check multiprocess table copy (only on POSIX systems).
            if options['multiprocess'] > 1 and os.name == 'posix':
                # Create copy task.
                copy_task = {
                    'source_srv': src_con_val,
                    'dest_srv': dest_con_val,
                    'source_db': self.db_name,
                    'target_db': new_db,
                    'table': tblname,
                    'options': tbl_options,
                    'cloning': self.cloning,
                }
                copy_tbl_tasks.append(copy_task)
            else:
                # Copy data from a table (no multiprocessing).
                _copy_table_data(self.source, self.destination, self.db_name,
                                 new_db, tblname, tbl_options, self.cloning)

        # Copy tables concurrently.
        if copy_tbl_tasks:
            # Create process pool.
            workers_pool = multiprocessing.Pool(
                processes=options['multiprocess']
            )
            # Concurrently export tables.
            workers_pool.map_async(_multiprocess_tbl_copy_task, copy_tbl_tasks)
            workers_pool.close()
            # Wait for all task to be completed by workers.
            workers_pool.join()

    def get_create_statement(self, db, name, obj_type):
        """Return the create statement for the object

        db[in]             Database name
        name[in]           Name of the object
        obj_type[in]       Object type (string) e.g. DATABASE
                           Note: this is used to form the correct SHOW command

        Returns create statement
        """
        # Save current sql_mode and switch it to '' momentarily as this
        # prevents issues when copying blobs and destination server is
        # set with SQL_MODE='NO_BACKSLASH_ESCAPES'
        prev_sql_mode = ''
        if (self.destination is not None and 'ANSI_QUOTES' in self.sql_mode and
                'ANSI_QUOTES' not in
                self.destination.select_variable("SQL_MODE")):
            prev_sql_mode = self.source.select_variable("SQL_MODE")
            self.source.exec_query("SET @@SESSION.SQL_MODE=''")
            self.sql_mode = ""
            # Quote with current sql_mode
            name = (name if not is_quoted_with_backticks(name, prev_sql_mode)
                    else remove_backtick_quoting(name, prev_sql_mode))
            db = (db if not is_quoted_with_backticks(db, prev_sql_mode)
                  else remove_backtick_quoting(db, prev_sql_mode))
        # Quote database and object name with backticks.
        q_name = (name if is_quoted_with_backticks(name, self.sql_mode)
                  else quote_with_backticks(name, self.sql_mode))
        if obj_type == _DATABASE:
            name_str = q_name
        else:
            q_db = (db if is_quoted_with_backticks(db, self.sql_mode)
                    else quote_with_backticks(db, self.sql_mode))

            # Switch the default database to execute the
            # SHOW CREATE statement without needing to specify the database
            # This is for 5.1 compatibility reasons:
            try:
                self.source.exec_query("USE {0}".format(q_db),
                                       self.query_options)
            except UtilError as err:
                raise UtilDBError("ERROR: Couldn't change "
                                  "default database: {0}".format(err.errmsg))
        name_str = q_name

        # Retrieve the CREATE statement.
        row = self.source.exec_query(
            "SHOW CREATE {0} {1}".format(obj_type, name_str)
        )

        # Restore previews sql_mode
        if prev_sql_mode:
            self.source.exec_query("SET @@SESSION.SQL_MODE={0}"
                                   "".format(prev_sql_mode))
            self.sql_mode = prev_sql_mode

        create_statement = None
        if row:
            if obj_type == _TABLE or obj_type == _VIEW or \
               obj_type == _DATABASE:
                create_statement = row[0][1]
            elif obj_type == _EVENT:
                create_statement = row[0][3]
            else:
                create_statement = row[0][2]

        # Remove all table options from the CREATE statement (if requested).
        if self.skip_table_opts and obj_type == _TABLE:
            # First, get partition options.
            create_tbl, sep, part_opts = create_statement.rpartition('\n/*')
            # Handle situation where no partition options are found.
            if not create_tbl:
                create_tbl = part_opts
                part_opts = ''
            else:
                part_opts = "{0}{1}".format(sep, part_opts)
            # Then, separate table definitions from table options.
            create_tbl, sep, _ = create_tbl.rpartition(') ')
            # Reconstruct CREATE statement without table options.
            create_statement = "{0}{1}{2}".format(create_tbl, sep, part_opts)

        return create_statement

    def get_create_table(self, db, table):
        """Return the create table statement for the given table.

        This method returns the CREATE TABLE statement for the given table with
        or without the table options, according to the Database object
        property 'skip_table_opts'.

        db[in]             Database name.
        table[in]          Table name.

        Returns a tuple with the CREATE TABLE statement and table options
        (or None). If skip_table_opts=True the CREATE statement does not
        include the table options that are returned separately, otherwise the
        table options are included in the CREATE statement and None is returned
        as the second tuple element.
        """
        # Quote database and table name with backticks.
        q_table = (table if is_quoted_with_backticks(table, self.sql_mode)
                   else quote_with_backticks(table, self.sql_mode))
        q_db = db if is_quoted_with_backticks(db, self.sql_mode) else \
            quote_with_backticks(db, self.sql_mode)

        # Retrieve CREATE TABLE.
        try:
            row = self.source.exec_query(
                "SHOW CREATE TABLE {0}.{1}".format(q_db, q_table)
            )
            create_tbl = row[0][1]
        except UtilError as err:
            raise UtilDBError("Error retrieving CREATE TABLE for {0}.{1}: "
                              "{2}".format(q_db, q_table, err.errmsg))

        # Separate table options from table definition.
        tbl_opts = None
        if self.skip_table_opts:
            # First, get partition options.
            create_tbl, sep, part_opts = create_tbl.rpartition('\n/*')
            # Handle situation where no partition options are found.
            if not create_tbl:
                create_tbl = part_opts
                part_opts = ''
            else:
                part_opts = "{0}{1}".format(sep, part_opts)
            # Then, separate table definitions from table options.
            create_tbl, sep, tbl_opts = create_tbl.rpartition(') ')
            # Reconstruct CREATE TABLE without table options.
            create_tbl = "{0}{1}{2}".format(create_tbl, sep, part_opts)

        return create_tbl, tbl_opts

    def get_table_options(self, db, table):
        """Return the table options.

        This method returns the list of used table options (from the CREATE
        TABLE statement).

        db[in]             Database name.
        table[in]          Table name.

        Returns a list of table options.
        For example: ['AUTO_INCREMENT=5','ENGINE=InnoDB']
        """
        # Quote database and table name with backticks.
        q_table = (table if is_quoted_with_backticks(table, self.sql_mode)
                   else quote_with_backticks(table, self.sql_mode))
        q_db = db if is_quoted_with_backticks(db, self.sql_mode) else \
            quote_with_backticks(db, self.sql_mode)

        # Retrieve CREATE TABLE statement.
        try:
            row = self.source.exec_query(
                "SHOW CREATE TABLE {0}.{1}".format(q_db, q_table)
            )
            create_tbl = row[0][1]
        except UtilError as err:
            raise UtilDBError("Error retrieving CREATE TABLE for {0}.{1}: "
                              "{2}".format(q_db, q_table, err.errmsg))

        # First, separate partition options.
        create_tbl, _, part_opts = create_tbl.rpartition('\n/*')
        # Handle situation where no partition options are found.
        create_tbl = part_opts if not create_tbl else create_tbl
        # Then, separate table options from table definition.
        create_tbl, _, tbl_opts = create_tbl.rpartition(') ')
        table_options = tbl_opts.split()

        return table_options

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

        # Remove objects backticks if needed
        db = remove_backtick_quoting(db, self.sql_mode) \
            if is_quoted_with_backticks(db, self.sql_mode) else db
        name = remove_backtick_quoting(name, self.sql_mode) \
            if is_quoted_with_backticks(name, self.sql_mode) else name

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
                typ = 'PROCEDURE'
            else:
                typ = 'FUNCTION'
            condition += " AND ROUTINE_TYPE = '%s'" % typ
        elif obj_type == _EVENT:
            columns = ('EVENT_SCHEMA, EVENT_NAME, DEFINER, EVENT_DEFINITION, '
                       'EVENT_TYPE, INTERVAL_FIELD, INTERVAL_VALUE, STATUS, '
                       'ON_COMPLETION, STARTS, ENDS')
            from_name = 'EVENTS'
            condition = "EVENT_SCHEMA = '%s' AND EVENT_NAME = '%s'" % \
                        (db, name)

        if from_name is None:
            raise UtilError('Attempting to get definition from unknown object '
                            'type = %s.' % obj_type)

        values = {
            'columns': columns,
            'table_name': from_name,
            'conditions': condition,
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
                part_def = self.source.exec_query(_PARTITION_QUERY % values)
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
        oper = 'NOT REGEXP' if self.use_regexp else 'NOT LIKE'
        string = ""
        for pattern in self.exclude_patterns:
            # Check use of qualified object names (with backtick support).
            if pattern.find(".") > 0:
                use_backtick = is_quoted_with_backticks(pattern, self.sql_mode)
                db, name = parse_object_name(pattern, self.sql_mode, True)
                if use_backtick:
                    # Remove backtick quotes.
                    db = remove_backtick_quoting(db, self.sql_mode)
                    name = remove_backtick_quoting(name, self.sql_mode)
                if db == self.db_name:  # Check if database name matches.
                    value = name  # Only use the object name to exclude.
                else:
                    value = pattern
            # Otherwise directly use the specified pattern.
            else:
                value = pattern
            if value:
                # Append exclude condition to previous one(s).
                string = "{0} AND {1} {2} {3}".format(string, exclude_param,
                                                      oper, obj2sql(value))

        return string

    def get_object_type(self, object_name):
        """Return the object type of an object

        This method attempts to locate the object name among the objects
        in the database. It returns the object type if found or None
        if not found.
        Note: different types of objects with the same name might exist in the
        database.

        object_name[in]    Name of the object to find

        Returns (list of strings) with the object types or None if not found
        """
        object_types = None

        # Remove object backticks if needed
        obj_name = remove_backtick_quoting(object_name, self.sql_mode) \
            if is_quoted_with_backticks(object_name, self.sql_mode) else \
            object_name

        res = self.source.exec_query(_OBJTYPE_QUERY %
                                     {'db_name': self.db_name,
                                      'obj_name': obj_name})

        if res:
            object_types = ['TABLE' if row[0] == 'BASE TABLE' else row[0]
                            for row in res]

        return object_types

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
                KEY_COLUMN_USAGE.CONSTRAINT_NAME AS KEY_CONSTRAINT_NAME,
                KEY_COLUMN_USAGE.COLUMN_NAME AS COL_NAME,
                KEY_COLUMN_USAGE.REFERENCED_TABLE_SCHEMA,
                KEY_COLUMN_USAGE.REFERENCED_COLUMN_NAME
            """
            full_pos_to_quote = (1, 2, 22, 27, 28, 29, 30, 33, 34, 35, 36)
            full_pos_split_quote = (34, 36)
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
                KEY_COLUMN_USAGE.CONSTRAINT_NAME AS KEY_CONSTRAINT_NAME,
                KEY_COLUMN_USAGE.COLUMN_NAME AS COL_NAME,
                KEY_COLUMN_USAGE.REFERENCED_TABLE_SCHEMA,
                KEY_COLUMN_USAGE.REFERENCED_COLUMN_NAME
            """
            minimal_pos_to_quote = (0, 1, 4, 11, 12, 13, 16, 17, 18, 19)
            minimal_pos_split_quote = (17, 19)
            _OBJECT_QUERY = """
            FROM INFORMATION_SCHEMA.TABLES JOIN INFORMATION_SCHEMA.COLUMNS ON
                TABLES.TABLE_SCHEMA = COLUMNS.TABLE_SCHEMA AND
                TABLES.TABLE_NAME = COLUMNS.TABLE_NAME
            LEFT JOIN INFORMATION_SCHEMA.REFERENTIAL_CONSTRAINTS ON
                TABLES.TABLE_SCHEMA = REFERENTIAL_CONSTRAINTS.CONSTRAINT_SCHEMA
                AND
                TABLES.TABLE_NAME = REFERENTIAL_CONSTRAINTS.TABLE_NAME
            LEFT JOIN (
                  SELECT CONSTRAINT_SCHEMA, TABLE_NAME, CONSTRAINT_NAME,
                         GROUP_CONCAT(COLUMN_NAME ORDER BY ORDINAL_POSITION)
                         AS COLUMN_NAME, REFERENCED_TABLE_SCHEMA,
                         GROUP_CONCAT(REFERENCED_COLUMN_NAME ORDER BY
                         ORDINAL_POSITION) AS REFERENCED_COLUMN_NAME
                  FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
                  GROUP BY CONSTRAINT_SCHEMA, TABLE_NAME, CONSTRAINT_NAME,
                           REFERENCED_TABLE_SCHEMA
            ) AS KEY_COLUMN_USAGE ON
                TABLES.TABLE_SCHEMA = KEY_COLUMN_USAGE.CONSTRAINT_SCHEMA
                AND
                TABLES.TABLE_NAME = KEY_COLUMN_USAGE.TABLE_NAME
            WHERE TABLES.TABLE_SCHEMA = '%s' AND TABLE_TYPE <> 'VIEW' %s
            """
            _ORDER_BY_DEFAULT = """
            ORDER BY TABLES.TABLE_SCHEMA, TABLES.TABLE_NAME,
                     COLUMNS.ORDINAL_POSITION
            """
            _ORDER_BY_NAME = """
            ORDER BY TABLES.TABLE_NAME
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
            full_pos_split_quote = ()
            _MINIMAL = """
            SELECT TABLE_SCHEMA, TABLE_NAME, DEFINER, SECURITY_TYPE,
                   VIEW_DEFINITION, CHECK_OPTION, IS_UPDATABLE,
                   CHARACTER_SET_CLIENT, COLLATION_CONNECTION
            """
            minimal_pos_to_quote = (0, 1)
            minimal_pos_split_quote = ()
            _OBJECT_QUERY = """
            FROM INFORMATION_SCHEMA.VIEWS
            WHERE TABLE_SCHEMA = '%s' %s
            """
            _ORDER_BY_DEFAULT = ""
            _ORDER_BY_NAME = ""
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
            full_pos_split_quote = ()
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
            minimal_pos_split_quote = ()
            _OBJECT_QUERY = """
            FROM INFORMATION_SCHEMA.TRIGGERS
            WHERE TRIGGER_SCHEMA = '%s' %s
            """
            _ORDER_BY_DEFAULT = ""
            _ORDER_BY_NAME = ""
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
            full_pos_split_quote = ()
            _MINIMAL = """
            SELECT NAME, LANGUAGE, SQL_DATA_ACCESS, IS_DETERMINISTIC,
                   SECURITY_TYPE, DEFINER, PARAM_LIST, RETURNS,
                   BODY, SQL_MODE,
                   CHARACTER_SET_CLIENT, COLLATION_CONNECTION,
                   DB_COLLATION
            """
            minimal_pos_to_quote = (0,)
            minimal_pos_split_quote = ()
            _OBJECT_QUERY = """
            FROM mysql.proc
            WHERE DB = '%s' AND TYPE = 'PROCEDURE' %s
            """
            _ORDER_BY_DEFAULT = ""
            _ORDER_BY_NAME = ""
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
            full_pos_split_quote = ()
            _MINIMAL = """
            SELECT NAME, LANGUAGE, SQL_DATA_ACCESS, IS_DETERMINISTIC,
                   SECURITY_TYPE, DEFINER, PARAM_LIST, RETURNS,
                   BODY, SQL_MODE,
                   CHARACTER_SET_CLIENT, COLLATION_CONNECTION,
                   DB_COLLATION
            """
            minimal_pos_to_quote = (0,)
            minimal_pos_split_quote = ()
            _OBJECT_QUERY = """
            FROM mysql.proc
            WHERE DB = '%s' AND TYPE = 'FUNCTION' %s
            """
            _ORDER_BY_DEFAULT = ""
            _ORDER_BY_NAME = ""
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
            full_pos_split_quote = ()
            _MINIMAL = """
            SELECT NAME, DEFINER, BODY, STATUS,
                   EXECUTE_AT, INTERVAL_VALUE, INTERVAL_FIELD, SQL_MODE,
                   STARTS, ENDS, STATUS, ON_COMPLETION, ORIGINATOR,
                   CHARACTER_SET_CLIENT, COLLATION_CONNECTION,
                   DB_COLLATION
            """
            minimal_pos_to_quote = (0,)
            minimal_pos_split_quote = ()
            _OBJECT_QUERY = """
            FROM mysql.event
            WHERE DB = '%s' %s
            """
            _ORDER_BY_DEFAULT = ""
            _ORDER_BY_NAME = ""
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
            'columns': get_columns
        }
        pos_to_quote = ()
        pos_split_quote = ()
        # pylint: disable=R0101
        if obj_type == _GRANT:
            query = _OBJECT_QUERY % (self.db_name, self.db_name,
                                     self.db_name, self.db_name)
            return self.source.exec_query(query, col_options)
        else:
            if columns == "names":
                prefix = _NAMES
                if need_backtick:
                    pos_to_quote = names_pos_to_quote
                sufix = _ORDER_BY_NAME
            elif columns == "full":
                prefix = _FULL
                if need_backtick:
                    pos_to_quote = full_pos_to_quote
                    pos_split_quote = full_pos_split_quote
                sufix = _ORDER_BY_DEFAULT
            else:
                prefix = _MINIMAL
                if need_backtick:
                    pos_to_quote = minimal_pos_to_quote
                    pos_split_quote = minimal_pos_split_quote
                sufix = _ORDER_BY_DEFAULT
            # Form exclusion string
            exclude_str = ""
            if self.exclude_patterns:
                exclude_str = self.__build_exclude_patterns(exclude_param)
            query = (prefix + _OBJECT_QUERY + sufix) % (self.db_name,
                                                        exclude_str)
            res = self.source.exec_query(query, col_options)

            # Quote required identifiers with backticks
            if need_backtick:
                new_rows = []
                for row in res[1]:
                    # Recreate row tuple quoting needed elements with backticks
                    # Note: handle elements that can hold multiple values
                    # quoting them separately (e.g., multiple column names).
                    r = []
                    for i, data in enumerate(row):
                        if data and i in pos_to_quote:
                            if i in pos_split_quote:
                                cols = data.split(',')
                                data = ','.join(
                                    [quote_with_backticks(col, self.sql_mode)
                                     for col in cols]
                                )
                                r.append(data)
                            else:
                                r.append(quote_with_backticks(data,
                                                              self.sql_mode))
                        else:
                            r.append(data)
                    new_rows.append(tuple(r))

                # set new result with with required data quoted with backticks
                res = (res[0], new_rows)

            if res and obj_type == _VIEW:
                res = self._get_views_sorted_by_dependencies(res, columns,
                                                             not need_backtick)

            return res

    def _check_user_permissions(self, uname, host, access):
        """Check user permissions for a given privilege

        uname[in]          user name to check
        host[in]           host name of connection
        access[in]         privilege to check (e.g. "SELECT")

        Returns True if user has permission, False if not
        """
        user = User(self.source, uname + '@' + host)
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
        # if procs, funcs, events or grants are included, we need read on
        # mysql db
        if not options.get('skip_procs', False) or \
           not options.get('skip_funcs', False) or \
           not options.get('skip_events', False) or \
           not options.get('skip_grants', False):
            priv_tuple = ("mysql", "SELECT")
            source_privs.append(priv_tuple)
        # if events, we need event
        if not options.get('skip_events', False):
            priv_tuple = (self.db_name, "EVENT")
            source_privs.append(priv_tuple)
        # if triggers, we need trigger
        if not options.get('skip_triggers', False):
            priv_tuple = (self.db_name, "TRIGGER")
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

    def check_write_access(self, user, host, options, source_objects=None,
                           do_drop=False):
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
        source_objects[in] Dictionary containing the list of objects from
                           source database
        do_drop[in]        True if the user is using --drop-first option

        Returns True if user has permissions and raises a UtilDBError if the
                     user does not have permission with a message that includes
                     the server context.
        """
        if source_objects is None:
            source_objects = {}

        dest_privs = [(self.db_name, "CREATE"),
                      (self.db_name, "ALTER"),
                      (self.db_name, "SELECT"),
                      (self.db_name, "INSERT"),
                      (self.db_name, "UPDATE"),
                      (self.db_name, "LOCK TABLES")]

        # Check for the --drop-first
        if do_drop:
            dest_privs.append((self.db_name, "DROP"))

        extra_privs = []
        super_needed = False

        try:
            res = self.source.exec_query("SELECT CURRENT_USER()")
            dest_user = res[0][0]
        except UtilError as err:
            raise UtilError("Unable to execute SELECT current_user(). Error: "
                            "{0}".format(err.errmsg))

        # CREATE VIEW is needed for views
        if not options.get("skip_views", False):
            views = source_objects.get("views", None)
            if views:
                extra_privs.append("CREATE VIEW")
                for item in views:
                    # Test if DEFINER is equal to the current user
                    if item[6] != dest_user:
                        super_needed = True
                        break

        # CREATE ROUTINE and EXECUTE are needed for procedures
        if not options.get("skip_procs", False):
            procs = source_objects.get("procs", None)
            if procs:
                extra_privs.append("CREATE ROUTINE")
                extra_privs.append("EXECUTE")
                if not super_needed:
                    for item in procs:
                        # Test if DEFINER is equal to the current user
                        if item[11] != dest_user:
                            super_needed = True
                            break

        # CREATE ROUTINE and EXECUTE are needed for functions
        # pylint: disable=R0101
        if not options.get("skip_funcs", False):
            funcs = source_objects.get("funcs", None)
            if funcs:
                if "CREATE ROUTINE" not in extra_privs:
                    extra_privs.append("CREATE ROUTINE")
                if "EXECUTE" not in extra_privs:
                    extra_privs.append("EXECUTE")
                if not super_needed:
                    trust_function_creators = False
                    try:
                        res = self.source.show_server_variable(
                            "log_bin_trust_function_creators"
                        )
                        if res and isinstance(res, list) and \
                                res[0][1] in ("ON", "1"):
                            trust_function_creators = True
                        # If binary log is enabled and
                        # log_bin_trust_function_creators is 0, we need
                        # SUPER privilege
                        super_needed = self.source.binlog_enabled() and \
                            not trust_function_creators
                    except UtilError as err:
                        raise UtilDBError("ERROR: {0}".format(err.errmsg))

                    if not super_needed:
                        for item in funcs:
                            # Test if DEFINER is equal to the current user
                            if item[11] != dest_user:
                                super_needed = True
                                break

        # EVENT is needed for events
        if not options.get("skip_events", False):
            events = source_objects.get("events", None)
            if events:
                extra_privs.append("EVENT")
                if not super_needed:
                    for item in events:
                        # Test if DEFINER is equal to the current user
                        if item[3] != dest_user:
                            super_needed = True
                            break

        # TRIGGER is needed for events
        if not options.get("skip_triggers", False):
            triggers = source_objects.get("triggers", None)
            if triggers:
                extra_privs.append("TRIGGER")
                if not super_needed:
                    for item in triggers:
                        # Test if DEFINER is equal to the current user
                        if item[18] != dest_user:
                            super_needed = True
                            break

        # Add SUPER privilege if needed
        if super_needed:
            dest_privs.append(("*", "SUPER"))

        # Add extra privileges needed
        for priv in extra_privs:
            dest_privs.append((self.db_name, priv))

        if not options.get('skip_grants', False):
            priv_tuple = (self.db_name, "GRANT OPTION")
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

    def check_auto_increment(self, tbl=None):
        """Check for any tables in the database with auto_increment values
        of 0. This will require a special sql_mode to copy or export. The
        method returns True if any table has an auto_increment value of 0.
        If tbl provided, use that table in the query otherwise check all
        tables.

        tbl[in]      If provided, use this table name

        Returns True if any table has 0 in auto_increment, False if not
        """
        FIND_AUTO_INC_COLS = """
            SELECT table_name, column_name FROM INFORMATION_SCHEMA.COLUMNS
            WHERE table_schema = '{0}' AND extra LIKE '%auto_increment%'
        """
        AUTO_INC_ZERO = "SELECT * FROM {0}.`{1}` WHERE {2} < 1;"
        # Watchout for weird tick marks in the name
        if self.db_name.count("`") > 0:
            query = FIND_AUTO_INC_COLS.format(self.q_db_name)
        else:
            query = FIND_AUTO_INC_COLS.format(self.db_name)
        if tbl:
            query = "{0} AND table_name = '{1}'".format(query, tbl)
        res = self.source.exec_query(query)
        for row in res:
            # Watchout for weird tick marks.
            column = row[1]
            # pylint: disable=W0125
            if (i in row[1] for i in ('`', '"', "'")):
                column = "`{0}`".format(row[1])
            query = AUTO_INC_ZERO.format(self.q_db_name, row[0], column)
            res = self.source.exec_query(query)
            if res:
                return True
        return False
