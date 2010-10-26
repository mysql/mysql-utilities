##############################################################
command.proc - Search for processes on servers
##############################################################

.. module:: mysql.utilities.command.proc

Module for searching processes on a server and operating on them.

.. data:: KILL_QUERY
.. data:: KILL_CONNECTION
.. data:: PRINT_PROCESS

   Constants for the different actions that can be done on processes.

.. data:: ID
.. data:: USER
.. data:: HOST
.. data:: DB
.. data:: COMMAND
.. data:: TIME
.. data:: STATE
.. data:: INFO

   Constants for the columns available in the processlist table.

.. class:: ProcessGrep(matches, actions=[], use_regexp=False)

   Class for searching the **INFORMATION_SCHEMA.PROCESSLIST** table on
   MySQL servers. It can both be used to do the actual search as well
   as generate a statement for doing the job.

   To kill all queries with user 'mats', the following code can be used:

   >>> from mysql.utilities.command.proc import *
   >>> grep = ProcessGrep(matches=[(USER, "mats")], actions=[KILL_QUERY])
   >>> grep.execute("root@server-1.example.com", "root@server-2.example.com")

   :param matches: Sequence of fields to compare. All fields have to
                   match for the process to match.

   :type matches: List of pairs *(var, pat)* where *var* is one of the
                  variables above and *pat* is a pattern.

   .. method:: sql([only_body=False])

      Get SQL code for executing the search (and optionally, the
      kill).

      If **only_body** is ``True``, only the body of the function is
      shown. This is useful if the SQL code is going to be used with
      other utilities that generate the routine declaration. If
      **only_body** is false, a complete procedure will be generated
      if there is any kill action supplied, and just a select
      statement if it is a plain search.

      :type only_body: boolean
      :param only_body: Only show the body of the procedure. If this
                        is ``False``, then a complete procedure will
                        be returned.
      :returns: SQL code for executing the operation given by the
                options.
      :rtype: string

   .. method:: execute(connections[, output=sys.stdout, connector=MySQLdb])

      Execute the search on each of the connections supplied. If
      **output** is not ``None``, then the value will be treated as a
      file object and the result of the execution printed on that
      stream.

      :param connections: Sequence of connections to query.
      :type connections: Sequence of :ref:`connection specificers`
      :param output: File object for printing output to
      :param connector: Connector to use.

