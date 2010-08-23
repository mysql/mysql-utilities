=========
mysqlproc
=========

----------------------------------------------------------
Search for processes on a MySQL server and perform actions
----------------------------------------------------------

:Author: Mats Kindahl <mats.kindahl@oracle.com>
:Manual section: 1


SYNOPSIS
========

  mysqlproc [options] 

DESCRIPTION
===========

This utility scan the process lists for all the servers provided on
the command line and will either print the result (the default) or
execute certain actions on it. The match conditions are given as
options to the tool and in order for a row to match, all the
conditions given have to match.


Options
-------

-h HOST, --host=HOST
  Connect to the MySQL server on the given host. Default is 'localhost'.

-u USER, --user=USER
  The MySQL user name to use when connecting to the server. Default is
  to use the login name of the user.

-S SOCKET, --socket=SOCKET
  For connections to localhost, the Unix socket file to use.

-p PASSWORD, --password=PASSWORD
  The password to use when connecting to the server.

-P PORT, --port=PORT
 The TCP/IP port number to use for the connection.

--match-user=PATTEN
  Match all rows where the ``User`` field matches PATTERN

--match-host=PATTERN
  Match all rows where the ``Host`` field matches PATTERN

--match-db=PATTERN
  Match all rows where the ``Db`` field matches PATTERN

--match-time=PERIOD
  Match all rows where the ``Time`` field is within PERIOD

--match-command=PATTERN
  Match all rows where the ``Command`` field matches PATTERN

--match-state=PATTERN
  Match all rows where the ``State`` field matches PATTERN

--match-info=PATTERN
  Match all rows where the ``Info`` field matches PATTERN

--kill
  Kill the connection for all matching processes

--kill-query
  Kill the query for all matching processes

--print
  Print information about the matching processes

--verbose
  Be more verbose and print messages about execution. Can be given
  multiple times, in which case the verbosity level increases.

--help
  Print help

Specifying time periods
-----------------------

A time period specification consists of a number with an optional
suffix denoting the size of the period and there can be an optional +
or - sign as prefix. A + sign before the period means greater than the
given period, a - sign means less than the given period, while no sign
means within that period.

The allowable suffixes are ``s`` (second), ``m`` (minute), ``h``
(hour), ``d`` (day), and ``w`` (week).


EXAMPLES
========

For all the examples, we assume that the ``root`` user on
``localhost`` has sufficient privileges to kill queries and
connections.

To kill all connections created by user "mats" that are younger than 1 minute::

  mysqlproc --user=root --host=localhost --match-user=mats --match-time=-1m --kill-query

To kill all queries that has been idle for more than 1 hour::

  mysqlproc --user=root --host=localhost --match-command=sleep --match-time=+1h --kill
