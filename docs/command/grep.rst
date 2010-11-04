#############################################################
:mod:`mysql.utilities.command.grep` --- Searching for Objects
#############################################################

.. module:: mysql.utilities.command.grep

This module provide utilities to search objects on server. The module
define a set of *object types* that can be searched by searching the
*fields* of each object. The notion of a field of an object is in this
case very loosly defined and basically means any names occuring as
part of the definition of an object. For example, the fields of a
table include the table name, the column names, and the partition
names (if it is a partition table).


Module Contents
---------------

.. data:: ROUTINE
.. data:: EVENT
.. data:: TRIGGER
.. data:: TABLE
.. data:: DATABASE
.. data:: VIEW
.. data:: USER

   Constants that can be used to denote the different object types.

.. data:: OBJECT_TYPES

   This is a sequence of all the object types that are available. It
   can be used to generate a version-independent list of object types
   that can be searched in, for example, options and help texts.

.. class:: ObjectGrep(pattern[, database_pattern=None, types=OBJECT_TYPES, check_body=False, use_regexp=False])

   Search for objects on a MySQL server by name or content.

   This command class is used to search one or more MySQL server
   instances for objects where the name (or the contents of routines,
   triggers, or events) match a given pattern.

   .. method:: sql() -> string

      This will return SQL code for executing the search in the form of a
      `SELECT`_ statement.

   .. method:: execute(connections[, output=sys.output, connector=MySQLdb])

      Execute the search on each of the connections in turn and print an
      aggregate of the result as a grid table.

      :param connections: Sequence of :ref:`connection specifiers` to send the query to.
      :param output: Output stream where the result will be written.
      :param connector: Connector to use when connecting to the servers.


.. References
.. ----------
.. _`SELECT`: http://dev.mysql.com/doc/refman/5.1/en/select.html
