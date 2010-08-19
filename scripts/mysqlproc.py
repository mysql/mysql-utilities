#!/usr/bin/python

"""
=========
mysqlproc
=========

----------------------------------------------------------
Search for processes on a MySQL server and perform actions
----------------------------------------------------------


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
  Connect to the MySQL server on the given host.

-u USER, --user=USER
  The MySQL user name to use when connecting to the server.

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
"""

import optparse
import mysql.command

# The structure of all the scripts are such that the main processing
# is done in the commands class, while the "view" part, representing
# the external interface to the world, is handled in the script.
#
# - Parsing options
# - Formatting output

# Parse options
parser = optparse.OptionParser(version="0.1", add_help_option=False)

parser.add_option("-h", "--host", dest="host",
                  help="Connect to the MySQL server on the given host.")
parser.add_option("-u", "--user", dest="user",
                  help="The MySQL user name to use when connecting to the server.")
parser.add_option("-S", "--socket", dest="socket",
                  help="For connections to localhost, the Unix socket file to use.")
parser.add_option("-p", "--password", dest="password",
                  help="The password to use when connecting to the server.")
parser.add_option("-P", "--port", dest="port", type="int", 
                  help="The TCP/IP port number to use for the connection.")
parser.add_option("--help", action="help")
# We could probably switch to use a callback and append the compiled
# regexps instead, but we leave this for later.
parser.add_option("--match-user", dest="match_user", metavar="PATTERN",
                  help="Match the User column of the PROCESSLIST table")
parser.add_option("--match-host", dest="match_host", metavar="PATTERN",
                  help="Match the Host column of the PROCESSLIST table")
parser.add_option("--match-db", dest="match_db", metavar="PATTERN",
                  help="Match the Db column of the PROCESSLIST table")
parser.add_option("--match-command", dest="match_command", metavar="PATTERN",
                  help="Match the Command column of the PROCESSLIST table")
parser.add_option("--match-info", dest="match_info", metavar="PATTERN",
                  help="Match the Info column of the PROCESSLIST table")
parser.add_option("--match-state", dest="match_state", metavar="PATTERN",
                  help="Match the State column of the PROCESSLIST table")
parser.add_option("--match-time", dest="match_time", metavar="PERIOD",
                  help="Match the Time column of the PROCESSLIST table")
parser.add_option("-v", "--verbose", action="count", dest="verbosity",
                  default=0,
                  help="Print debugging messages about progress to STDOUT. Multiple -v options increase the verbosity.")
parser.add_option("--kill", action="append_const",
                  const=mysql.command.KILL_CONNECTION,
                  dest="action_list",
                  help="Kill all matching connections.")
parser.add_option("--kill-query", action="append_const",
                  const=mysql.command.KILL_QUERY,
                  dest="action_list",
                  help="Kill query for all matching processes.")
parser.add_option("--print", action="append_const",
                  const=mysql.command.PRINT_PROCESS,
                  dest="action_list",
                  help="Print all matching processes.")
(options, args) = parser.parse_args()

# Construct execution object
command = mysql.command.ProcessListProcessor(options)
# Execute command
command.execute(args)

