.. _`mysqlprocgrep`:

############################################################
``mysqlprocgrep`` - Search through process lists on a server
############################################################

SYNOPSIS
--------

  mysqlprocgrep [ --version | --help ] | --format=<format> |
                --kill-connection | --kill-query | --regexp | --sql-body |
                --print | --verbose | --match-user=<pattern> |
                --match-host=<pattern> | --match-command=<pattern> |
                --match-info=<pattern> | --match-state=<pattern> |
                --server=<user>[<passwd>]@<host>:[<port>][:<socket>]

DESCRIPTION
-----------

This utility scan the process lists for all the servers provided via repeated
occurrences of the :option:`--server` option and will either print the result
(the default) or execute certain actions on it. The match conditions are given
as options to the tool and in order for a row to match, all the conditions
given have to match.

You also have the choice to view the output in one of the following
formats using the :option:`--format` option.

**GRID**
  Displays output formatted like that of the mysql monitor in a grid
  or table layout. This is the default.

**CSV**
  Displays the output in a comma-separated list.

**TAB**
  Displays the output in a tab-separated list.

**VERTICAL**
  Displays the output in a single column similar to the ``\G`` option
  for the mysql monitor commands.


Options
-------

.. option:: --help, -h

   Print help

.. option:: --match-user <pattern>

   Match all rows where the **User** field matches pattern

.. option:: --match-host <pattern>

   Match all rows where the **Host** field matches pattern

.. option:: --match-db <pattern>

   Match all rows where the **Db** field matches pattern

.. option:: --match-time <pattern>

   Match all rows where the **Time** field matches pattern

.. option:: --match-command <pattern>

   Match all rows where the **Command** field matches pattern

.. option:: --match-state <pattern>

   Match all rows where the **State** field matches pattern.

.. option:: --match-info <pattern>

   Match all rows where the **Info** field matches pattern.

.. option:: --kill-connection

   Kill the connection for all matching processes.

.. option:: --kill-query

   Kill the query for all matching processes.

.. option:: --print

   Print information about the matching processes. This is the default
   if no :option:`--kill-connection` or :option:`--kill-query` option
   is given. If a kill option is given, this option will print
   information about the processes before killing them.

.. option:: --verbose, -v

   Be more verbose and print messages about execution. Can be given
   multiple times, in which case the verbosity level increases.
   For example, -v = verbose, -vv = more verbose, -vvv = debug

.. option:: --regexp, --basic-regexp, -G

   Use **REGEXP** operator to match patterns instead of **LIKE**.

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
   are generated. Note that it is not possible to execute the emitted
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

.. option:: --format <format>, -f <format>

   display the output in either GRID (default), TAB, CSV, or VERTICAL format


Specifying time
~~~~~~~~~~~~~~~

Time for the :option:`--age` option can be specified in two formats:
either using the ``hh:mm:ss`` format, with hours and minutes optional,
or as a sequence of numbers with a suffix giving the period size.

The allowable suffixes are **s** (second), **m** (minute), **h**
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
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
USA
