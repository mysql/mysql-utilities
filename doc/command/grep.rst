####################################################################
:mod:`mysql.utilities.command.grep` --- Search Databases for Objects
####################################################################

.. module:: mysql.utilities.command.grep

This module provides utilities to search for objects on a server. The module
defines a set of *object types* that can be searched by searching the
*fields* of each object. The notion of an object field is
very loosely defined and means any names occurring as part of the
object definition. For example, the fields of a table include the table
name, the column names, and the partition names (if it is a partitioned
table).


Constants
---------

The following constants denote the object types that can be searched.

.. data:: ROUTINE
          EVENT
          TRIGGER
          TABLE
          DATABASE
          VIEW
          USER

The following constant is a sequence of all the object types that are
available. It can be used to generate a version-independent list of object
types that can be searched; for example, options and help texts.

.. data:: OBJECT_TYPES

Classes
-------

.. class:: ObjectGrep(pattern[, database_pattern=None, types=OBJECT_TYPES, check_body=False, use_regexp=False])

   Search MySQL server instances for objects where the name (or content, for
   routines, triggers, or events) matches a given pattern.

   .. method:: sql() -> string

      Return the SQL code for executing the search in the form of a
      `SELECT`_ statement.

      :returns: SQL code for executing the operation specified by the
                options.
      :rtype: string

   .. method:: execute(connections[, output=sys.output, connector=mysql.connector])

      Execute the search on each of the connections in turn and print an
      aggregate of the result as a grid table.

      :param connections: Sequence of connection specifiers to send the query to
      :param output: File object to use for writing the result
      :param connector: Connector to use for connecting to the servers


.. References
.. ----------
.. _`SELECT`: http://dev.mysql.com/doc/mysql/en/select.html
