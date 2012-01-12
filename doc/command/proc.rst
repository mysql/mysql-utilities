###################################################################
:mod:`mysql.utilities.command.proc` --- Search Processes on Servers
###################################################################

.. module:: mysql.utilities.command.proc

Module for searching processes on a server and optionally killing either
the query or the connection for all matching processes.

The processes are searched by matching the fields in the
`INFORMATION_SCHEMA.PROCESSLIST`_ table in the server (this means that
the module only works for servers with version 5.1.7 and later). The
module operates internally by constructing a `SELECT`_ statement for
finding matching processes, and then sending it to the server.
Instead of performing the search, SQL code performing the query can be
printed on standard output, which can be useful if you want to execute
the query later, or feed it into some other program that process SQL
queries further.


Constants
---------

The following constants correspond to columns in the
`INFORMATION_SCHEMA.PROCESSLIST`_ table. They indicate which columns to
examine when searching for processes matching the search conditions.

.. data:: ID
          USER
          HOST
          DB
          COMMAND
          TIME
          STATE
          INFO

The following constants indicate actions to perform on processes that match
the search conditions.

.. data:: KILL_QUERY

   Kill the process query

.. data:: KILL_CONNECTION

   Kill the process connection

.. data:: PRINT_PROCESS

   Print the processes


Classes
-------

.. class:: ProcessGrep(matches, actions=[], use_regexp=False)

   This class searches the `INFORMATION_SCHEMA.PROCESSLIST`_ table for
   processes on MySQL servers and optionally kills them. It can both be used
   to actually perform the search or kill operation, or to generate the SQL
   statement for doing the job.

   To kill all queries with user 'mats', the following code can be used:

   >>> from mysql.utilities.command.proc import *
   >>> grep = ProcessGrep(matches=[(USER, "mats")], actions=[KILL_QUERY])
   >>> grep.execute("root@server-1.example.com", "root@server-2.example.com")

   :param matches: Sequence of field comparison conditions. In each
                   condition, *var* is one of the constants listed earlier
                   and *pat* is a pattern. All field conditions must
                   match for the process to match.

   :type matches: List of *(var, pat)* pairs

   .. method:: sql([only_body=False])

      Return the SQL code for executing the search (and optionally, the
      kill).

      If *only_body* is ``True``, only the body of the function is
      shown. This is useful if the SQL code is to be used with
      other utilities that generate the routine declaration. If
      *only_body* is ``False``, a complete procedure will be generated if
      there is any kill action supplied, and just a select statement
      if it is a plain search.

      :type only_body: boolean
      :param only_body: Show only the body of the procedure. If this
                        is ``False``, a complete procedure is returned.
      :returns: SQL code for executing the operation specified by the
                options.
      :rtype: string

   .. method:: execute(connection, ...[, output=sys.stdout, connector=mysql.connector])

      Execute the search on each of the connections supplied. If
      *output* is not ``None``, the value is treated as a
      file object and the result of the execution is printed on that
      stream. Note that the output and connector arguments *must* 
      be supplied as keyword arguments. All other arguments
      are treated as connection specifiers.

      :type connection: A :ref:`connection specifiers`
      :param output: File object for printing output to
      :param connector: Connector to use


.. References
.. ----------
.. _`INFORMATION_SCHEMA.PROCESSLIST`: http://dev.mysql.com/doc/mysql/en/processlist-table.html
.. _`SELECT`: http://dev.mysql.com/doc/mysql/en/select.html
