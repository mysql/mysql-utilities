####################################
command.grep - Searching for Objects
####################################

.. automodule:: mysql.utilities.command.grep

.. data:: ROUTINE
.. data:: EVENT
.. data:: TRIGGER
.. data:: TABLE
.. data:: DATABASE
.. data:: VIEW
.. data:: USER

   Constants that can be used to denote the different object types.

.. autodata:: OBJECT_TYPES

.. autoclass:: ObjectGrep(pattern[, database_pattern=None, types=OBJECT_TYPES, check_body=False, use_regexp=False])
   :members: sql

   .. automethod:: execute(connections[, output=sys.output, connector=MySQLdb])
