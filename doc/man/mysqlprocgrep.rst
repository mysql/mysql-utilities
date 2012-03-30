.. _`mysqlprocgrep`:

###############################################
``mysqlprocgrep`` - Search Server Process Lists
###############################################

SYNOPSIS
--------

::

 mysqlprocgrep [options]

DESCRIPTION
-----------

This utility scans the process lists for the servers specified using
instances of the :option:`--server` option and selects those that match the
conditions specified using the :option:`--age` and ``--match-xxx`` options. For
a process to match, all conditions given must match.  The utility then
either prints the selected processes (the default) or executes certain
actions on them.

If no :option:`--age` or ``--match-xxx`` options are given, the utility
selects all processes.

The ``--match-xxx`` options correspond to the columns in the
**INFORMATION_SCHEMA.PROCESSLIST** table. For example,
:option:`--match-command` specifies a matching condition for
**PROCESSLIST.COMMAND** column values.  There is no ``--match-time`` option.
To specify a condition based on process time, use :option:`--age`.

Processes that can be seen and killed are subject to whether the
account used to connect to the server has the **PROCESS** and
**SUPER** privileges.  Without **PROCESS**, the account cannot see
processes belonging to other accounts Without **SUPER**, the account
cannot kill processes belonging to other accounts

To specify how to display output, use one of the following values
with the :option:`--format` option:

**grid** (default)
  Display output in grid or table format like that of the
  :command:`mysql` monitor.

**csv**
  Display output in comma-separated values format.

**tab**
  Display output in tab-separated format.

**vertical**
  Display output in single-column format like that of the ``\G`` command
  for the :command:`mysql` monitor.


Options
-------

:command:`mysqlprocgrep` accepts the following command-line options:

.. option:: --help

   Display a help message and exit.

.. option:: --age=<time>

   Select only processes that have been in the current state more than
   a given time. The time value can be specified in two formats:
   either using the ``hh:mm:ss`` format, with hours and minutes optional,
   or as a sequence of numbers with a suffix giving the period size.

   The permitted suffixes are **s** (second), **m** (minute), **h** (hour),
   **d** (day), and **w** (week). For example, **4h15m** mean 4 hours and
   15 minutes.

   For both formats, the specification can optionally be preceded by 
   ``+`` or ``-``, where ``+`` means older than the given time, and
   ``-`` means younger than the given time.

.. option::  --format=<format>, -f<format>

   Specify the output display format. Permitted format values are **grid**,
   **csv**, **tab**, and **vertical**. The default is **grid**.

.. option:: --kill-connection

   Kill the connection for all matching processes (like the **KILL
   CONNECTION** statement).

.. option:: --kill-query

   Kill the query for all matching processes (like the **KILL QUERY**
   statement).

.. option:: --match-command=<pattern>

   Match all processes where the **Command** field matches the pattern.

.. option:: --match-db=<pattern>

   Match all processes where the **Db** field matches the pattern.

.. option:: --match-host=<pattern>

   Match all processes where the **Host** field matches the pattern.

.. option:: --match-info=<pattern>

   Match all processes where the **Info** field matches the pattern.

.. option:: --match-state=<pattern>

   Match all processes where the **State** field matches the pattern.

.. option:: --match-user=<pattern>

   Match all processes where the **User** field matches the pattern.

.. option:: --print

   Print information about the matching processes. This is the default
   if no :option:`--kill-connection` or :option:`--kill-query` option
   is given. If a kill option is given, :option:`--print` prints
   information about the processes before killing them.

.. option:: --regexp, --basic-regexp, -G

   Perform pattern matches using the **REGEXP** operator. The default is
   to use **LIKE** for matching.  This affects the ``--match-xxx`` options.

.. option:: --server=<source>

   Connection information for a server to search in
   <*user*>[:<*passwd*>]@<*host*>[:<*port*>][:<*socket*>] format.
   Use this option multiple times to search multiple servers.

.. option:: --sql, --print-sql, -Q

   Instead of displaying the selected processes, emit the **SELECT**
   statement that retrieves information about them. If the
   :option:`--kill-connection` or :option:`--kill-query` option is
   given, the utility generates a stored procedure named ``kill_processes()``
   for killing the queries rather than a **SELECT** statement.

.. option:: --sql-body

   Like :option:`--sql`, but produces the output as the body of a stored
   procedure without the **CREATE PROCEDURE** part of the definition.
   This could be used, for example, to generate an event for the server
   Event Manager.

   When used with a kill option, code for killing the matching queries
   is generated. Note that it is not possible to execute the emitted
   code unless it is put in a stored routine, event, or trigger. For
   example, the following code could be generated to kill all idle
   connections for user ``www-data``::

     $ mysqlprocgrep --kill-connection --sql-body \
     >   --match-user=www-data --match-state=sleep
     DECLARE kill_done INT;
     DECLARE kill_cursor CURSOR FOR
       SELECT
             Id, User, Host, Db, Command, Time, State, Info
           FROM
             INFORMATION_SCHEMA.PROCESSLIST
           WHERE
               user LIKE 'www-data'
             AND
               State LIKE 'sleep'
     OPEN kill_cursor;
     BEGIN
        DECLARE id BIGINT;
        DECLARE EXIT HANDLER FOR NOT FOUND SET kill_done = 1;
        kill_loop: LOOP
           FETCH kill_cursor INTO id;
           KILL CONNECTION id;
        END LOOP kill_loop;
     END;
     CLOSE kill_cursor;

.. option:: --verbose, -v

   Specify how much information to display. Use this option
   multiple times to increase the amount of information.  For example,
   :option:`-v` = verbose, :option:`-vv` = more verbose, :option:`-vvv` =
   debug.

.. option:: --version

   Display version information and exit.



NOTES
-----

For the :option:`--format` option, the permitted values are not case
sensitive. In addition, values may be specified as any unambiguous prefix of
a valid value.  For example, :option:`--format=g` specifies the grid format.
An error occurs if a prefix matches more than one valid value.


EXAMPLES
--------

For each example, assume that the ``root`` user on ``localhost`` has
sufficient privileges to kill queries and connections.

Kill all queries created by user ``mats`` that are younger than 1 minute::

  mysqlprocgrep --server=root@localhost \
    --match-user=mats --age=-1m --kill-query

Kill all connections that have been idle for more than 1 hour::

  mysqlprocgrep --server=root@localhost \
    --match-command=sleep --age=1h --kill-connection

COPYRIGHT
---------

Copyright (c) 2010, 2012, Oracle and/or its affiliates. All rights reserved.

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; version 2 of the License.

This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301 USA
