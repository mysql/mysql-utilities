#############
mysqlprocgrep
#############

SYNOPSIS
========

  mysqlprocgrep [options] server ...

DESCRIPTION
===========

This utility scan the process lists for all the servers provided on
the command line and will either print the result (the default) or
execute certain actions on it. The match conditions are given as
options to the tool and in order for a row to match, all the
conditions given have to match.


Options
-------

.. option:: --match-user=PATTEN

   Match all rows where the **User** field matches PATTERN

.. option:: --match-host=PATTERN

   Match all rows where the **Host** field matches PATTERN

.. option:: --match-db=PATTERN

   Match all rows where the **Db** field matches PATTERN

.. option:: --match-time=PERIOD

   Match all rows where the **Time** field is within PERIOD

.. option:: --match-command=PATTERN

   Match all rows where the **Command** field matches PATTERN

.. option:: --match-state=PATTERN

   Match all rows where the **State** field matches **PATTERN**.

.. option:: --match-info=PATTERN

   Match all rows where the **Info** field matches **PATTERN**.

.. option:: --kill-connection

   Kill the connection for all matching processes.

.. option:: --kill-query

   Kill the query for all matching processes.

.. option:: --print

   Print information about the matching processes. This is the default
   if no :option:`--kill-*` option is given. If a :option:`--kill-*`
   option is given, this option will print information about the
   processes before killing them.

.. option:: -v, --verbose

   Be more verbose and print messages about execution. Can be given
   multiple times, in which case the verbosity level increases.

.. option:: -G, --basic-regexp, --regexp

   Use 'REGEXP' operator to match patterns instead of 'LIKE'.

.. option:: -Q, --sql, --print-sql

   Emit the SQL for matching or killing the queries. If the
   :option:`--kill-*` option is given, a routine for killing the queries
   are generated.

.. option:: --sql-body

   Emit SQL statements for performing the search or kill of the
   **INFORMATION_SCHEMA.PROCESSLIST** table.  This is useful together
   with :manpage:`mysqlmkevent(1)` to generate an event for the server
   scheduler.

   When used with the :option:`--kill-*` option, code for killing the
   matching queries are generated. Note that it is not possible to
   execute the emitted code unless it is put in a stored routine,
   event, or trigger. For example, the following code could be
   generated to kill all connections for user **www-data** that is
   idle::

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

.. option:: -h, --help

   Print help


Specifying time periods
-----------------------

A time period specification consists of a number with an optional
suffix denoting the size of the period and there can be an optional +
or - sign as prefix. A + sign before the period means greater than the
given period, a - sign means less than the given period, while no sign
means within that period.

The allowable suffixes are **s** (second), **m** (minute), **h**
(hour), **d** (day), and **w** (week).


EXAMPLES
========

For all the examples, we assume that the **root** user on
**localhost** has sufficient privileges to kill queries and
connections.

To kill all connections created by user "mats" that are younger than 1 minute::

  mysqlprocgrep --user=root --host=localhost --match-user=mats --match-time=-1m --kill-query

To kill all queries that has been idle for more than 1 hour::

  mysqlprocgrep --user=root --host=localhost --match-command=sleep --match-time=+1h --kill
