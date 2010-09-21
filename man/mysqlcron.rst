=========
mysqlcron
=========

-------------------------------------------------------------
Cron-like utility to schedule execution of SQL-code on server
-------------------------------------------------------------

:Author: Mats Kindahl <mats.kindahl@oracle.com>
:Manual section: 1

SYNOPSIS
========

  mysqlcron [ <options> ] [ <file> ] ...

DESCRIPTION
===========

This utility allow a developer to schedule execution of SQL code on a
server. The utility will read code either from standard input, one or
more files, or from a command-line option and build a ``CREATE EVENT``
statement that can be sent to a server.

The code to execute can be supplied in various ways.

* If an ``--execute`` option is given, the code supplied with that
  option will be used inside the event. This is useful for short
  pieces of code.

* If one or more file names are provided on the command line, one
  event will be generated for each file and the contents of each file
  will be used body of each event.

If no ``--execute`` option is provided and no file names are given,
the body of the event is read from standard input. This allow the
utility to be combined with other utilities::

  nifty-utility | mysqlcron --interval=1h --start-time=+1d


Options
-------

-i, --interval
  The interval between executions. This is a mandatory argument.

--start-time
  Optional start time when the action will start repeating. This
  option supports relative times by using an interval prefixed with
  either a plus (``+``) or a minus (``-``). In that case, the start
  time is relative the current time as returned by ``NOW()``.

--end-time
  Optional end time when the action will stop repeating. This option
  also supports relative times in the same manner as ``--start-time``,
  but the end time is then computed relative the start time.

-e, --execute
  Code to execute. If this option is provided, nothing is read from
  standard input.

--comment
  Comment to add to the event. Useful for adminstrative purposes.

