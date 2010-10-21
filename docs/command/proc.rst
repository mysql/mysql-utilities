##############################################################
command.proc - Search for processes on servers
##############################################################

.. automodule:: mysql.utilities.command.proc

.. data:: ID
.. data:: USER
.. data:: HOST
.. data:: DB
.. data:: COMMAND
.. data:: TIME
.. data:: STATE
.. data:: INFO

Constants for the columns available in the processlist table.

.. autoclass:: ProcessGrep
   :members: sql

   .. automethod:: execute(connections[, output=sys.stdout, connector=MySQLdb])
