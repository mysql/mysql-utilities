.. _`mysqlprocgrep`:

###############################################
``mysqlprocgrep`` - Search Server Process Lists
###############################################

SYNOPSIS
--------

::

  mysqlprocgrep [ --version | --help ] | --format=<format> |
                --kill-connection | --kill-query | --regexp | --sql-body |
                --print | --verbose | --match-user=<pattern> |
                --match-host=<pattern> | --match-command=<pattern> |
                --match-info=<pattern> | --match-state=<pattern> |
                --server=<user>[:<passwd>]@<host>[:<port>][:<socket>]

DESCRIPTION
-----------

This utility scans the process lists for all the servers specified
using instances of the :option:`--server` option and either prints
the result (the default) or executes certain actions on it. The
process-matching conditions are specified as command options. For
a process to match, all conditions must match.

To specify how to display output, use one of the following values
with the :option:`--format` option:

**GRID** (default)
  Display output formatted like that of the mysql monitor in a grid
  or table layout.

**CSV**
  Display output in comma-separated values format.

**TAB**
  Display output in tab-separated format.

**VERTICAL**
  Display output in a single column similar to the ``\G`` command
  for the mysql monitor.


Options
-------

**mysqlprocgrep** accepts the following command-line options:

.. option:: --help, -h

   Display a help message and exit.

.. option:: --age=<time>

   Display only processes that have been in the current state more than a given
   time

.. option::  --format=<format>, -f<format>

   Specify the display format. Permitted format values are
   GRID, CSV, TAB, and VERTICAL. The default is GRID.

.. option:: --kill-connection

   Kill the connection for all matching processes.

.. option:: --kill-query

   Kill the query for all matching processes.

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

.. option:: --match-time=<pattern>

   Match all processes where the **Time** field matches the pattern.

.. option:: --match-user=<pattern>

   Match all processes where the **User** field matches the pattern.

.. option:: --print

   Print information about the matching processes. This is the default
   if no :option:`--kill-connection` or :option:`--kill-query` option
   is given. If a kill option is given, :option:`--print` prints
   information about the processes before killing them.

.. option:: --regexp, --basic-regexp, -G

   Perform pattern matches using the **REGEXP** operator. The default is
   to use **LIKE** for matching.

.. option:: --server=<source>

   Connection information for the servers to search in the format:
   <user>[:<passwd>]@<host>[:<port>][:<socket>]
   The option may be repeated to form a list of servers to search.

.. option:: --sql, --print-sql, -Q

   Emit the SQL for matching or killing the queries. If the
   :option:`--kill-connection` or :option:`--kill-query` option is
   given, a routine for killing the queries are generated.

.. option:: --sql-body

   Emit SQL statements for performing the search or kill of the
   **INFORMATION_SCHEMA.PROCESSLIST** table.  This is useful together
   with :manpage:`mysqlmkevent(1)` to generate an event for the server
   scheduler.

   When used with a kill option, code for killing the matching queries
   is generated. Note that it is not possible to execute the emitted
   code unless it is put in a stored routine, event, or trigger. For
   example, the following code could be generated to kill all
   connections for user **www-data** that is idle::

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
   multiple times to increase the amount of information.  For example, -v =
   verbose, -vv = more verbose, -vvv = debug.

.. option:: --version

   Display version information and exit.


Specifying time
~~~~~~~~~~~~~~~

Time for the :option:`--age` option can be specified in two formats:
either using the ``hh:mm:ss`` format, with hours and minutes optional,
or as a sequence of numbers with a suffix giving the period size.

The permitted suffixes are **s** (second), **m** (minute), **h**
(hour), **d** (day), and **w** (week), so **4h15m** mean 4 hours and
15 minutes.

For both formats, the specification can optionally be preceeded by a
``+`` or a ``-``, where a ``+`` means older than the given time, and
``-`` means younger than the given age.

EXAMPLES
--------

For all the examples, we assume that the **root** user on
**localhost** has sufficient privileges to kill queries and
connections.

To kill all connections created by user "mats" that are younger than 1
minute::

  mysqlprocgrep --server=root@localhost --match-user=mats --age=1m --kill-query

To kill all queries that has been idle for more than 1 hour::

  mysqlprocgrep --server=root@localhost --match-command=sleep --age=1h --kill

COPYRIGHT
---------

Copyright (c) 2010, Oracle and/or its affiliates. All rights reserved.

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
