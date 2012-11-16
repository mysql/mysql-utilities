.. `mysqlauditgrep`:

##############################################
``mysqlauditgrep`` - Audit Log Search Utility
##############################################

SYNOPSIS
--------

::

 mysqlauditgrep [OPTIONS]... AUDIT_LOG_FILE
 mysqlauditgrep --file-stats [--format=FORMAT] AUDIT_LOG_FILE
 mysqlauditgrep --format=FORMAT AUDIT_LOG_FILE
 mysqlauditgrep [--users=USERS] [--start-date=START_DATE] [--end-date=END_DATE]  [--pattern=PATTERN [--regexp]] [--query-type=QUERY_TYPE] [--event-type=EVENT_TYPE] [--format=FORMAT] AUDIT_LOG_FILE

 
DESCRIPTION
-----------

This utility allows users to search the current or an archived audit log,
allowing them to display data from the audit log file according to the defined
search criterion. It also allows the user to output the resulting audit log
records in different formats, namely GRID (default), TAB, CSV, VERTICAL and RAW
(i.e., original XML format).

In more detail, the utility allows the users to search/filter the returned
audit log records by: users (:option:`--users`), date/time ranges 
(:option:`--start-date` and :option:`--end-date`), SQL query types 
(:option:`--query-type`), logged event/record types (:option:`--event-type`), 
and matching patterns (:option:`--pattern`). Any of those search criteria can 
be combined and used at the same time, with the retrieved records resulting 
from the intersection of the application of all the used search criterion. 

The :option:`--pattern` supports two types of pattern matching: standard SQL, 
used with the SQL **LIKE** operator (:ref:`SQL_patterns`), and standard 
**REGEXP** (:ref:`regexp_patterns`).

The utility always requires the specification of the **AUDIT_LOG_FILE** to be
searched as argument (i.e., full path and file name for the audit log file).
If no option is specified the utility outputs a message notifying that no
search criteria was defined. However, if only the :option:`--format` option is
defined, then all the records of the audit log are displayed in the specified
format.

The :option:`--file-stats` option is not considered a search criteria, being
used to display the file statistics of the specified audit log. Other search
options will be ignored if the :option:`--file-stats` option is used, except
the :option:`--format` option that will format the output data according to
the specified value.

To specify the format of the output results, use one of the following values
with the :option:`--format` option:

**GRID** (default)
  Display output in grid or table format like that of the
  :command:`mysql` monitor.

**CSV**
  Display output in comma-separated values format.

**TAB**
  Display output in tab-separated format.

**VERTICAL**
  Display output in single-column format like that of the ``\G`` command
  for the :command:`mysql` monitor.

**RAW**
  Display output results in the original raw format of the audit log records,
  i.e. XML.


.. _SQL_patterns:

Standard SQL Pattern Matching
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The simple patterns defined by the SQL standard enable users to use two
characters with special meaning: ``%`` (percent) matches zero or more
characters and ``_`` (underscore) matches exactly one arbitrary character. In
standard SQL, this kind of patterns are used with the **LIKE** comparison
operator and they are case-insensitive by default. Thus, in context of this
utility it is assumed that they are case-insensitive.

For example:

``'audit%'``
  Match any string that starts with 'audit'.
``'%log%'``
  Match any string containing the word 'log'.
``'%_'``
  Match any string consisting of one or more characters.


More details about the standard SQL pattern matching syntax can be found in
the `MySQL manual`_.

.. _`MySQL manual`: http://dev.mysql.com/doc/mysql/en/pattern-matching.html


.. _regexp_patterns:

REGEXP Pattern Matching
^^^^^^^^^^^^^^^^^^^^^^^

Standard **REGEXP** patterns are more powerful than the simple patterns
defined in the SQL standard. A regular expression is a string of ordinary and
special characters specified to match other strings. Unlike SQL Patterns,
**REGEXP** patterns are case-sensitive. The **REGEXP** syntax defines the
following characters with special meaning:

**.**
   Match any character.
**^**
   Match the beginning of a string.
**$**
   Match the end of a string.
**\***
   Match zero or more repetitions of the preceding regular expression.
**+**
   Match one or more repetitions of the preceding regular expression.
**?**
   Match zero or one repetition of the preceding regular expression.
**|**
   Match either the regular expressions from the left or right of '|'.
**[]**
   Indicates a set of characters to match. Note that, special characters lose
   their special meaning inside sets. In particular, '^' acquires a different
   meaning if it is the first character of the set, matching the
   complementary set (i.e., all the characters that are not in the set will be
   matched).
**{m}**
   Match *m* repetitions of the preceding regular expression.
**{m,n}**
   Match from *m* to *n* repetitions of the preceding regular expression.
**()**
   Define a matching group, and matches the regular expression inside the
   parentheses.

For example:

``'a\*'``
  Match a sequence of zero or more 'a'.
``'a+'``
  Match a sequence of one or more 'a'.
``'a?'``
  Match zero or one 'a'.
``'ab|cd'``
  Match 'ab' or 'cd'
``'[axy]'``
  Match 'a', 'x', or 'y'.
``'[a-f]'``
  Match any character in the range 'a' to  'f' (that is, 'a', 'b', 'c', 'd',
  'e', or 'f').
``'[^axy]'``
  Match any character *except* 'a', 'x',  or 'y'.
``'a{5}'``
  Match exactly five copies of 'a'.
``'a{2,5}'``
  Match from two to five copies of 'a'.
``'(abc)+'``
  Match one or more repetitions of 'abc'.


This is a brief overview of regular expressions that can be used to define
this type of patterns. The full syntax is described in the 
`Python re module docs`_, supporting the definition of much more complex 
pattern matching expression.

.. _`Python re module docs`: http://docs.python.org/library/re.html#regular-expression-syntax


OPTIONS
-------

:command:`mysqlauditgrep` accepts the following command-line options:

.. option:: --end-date=END_DATE

   End date/time to retrieve log entries until the specified date/time
   range. If not specified or the value is 0, all entries to the end of
   the log are displayed. Accepted formats: yyyy-mm-ddThh:mm:ss or yyyy-mm-dd.

.. option:: --event-type=EVENT_TYPE

   Comma-separated list of event types to search for all audit log records
   matching the specified types. Supported values: Audit, Binlog Dump, Change
   user, Close stmt, Connect Out, Connect, Create DB, Daemon, Debug, Delayed
   insert, Drop DB, Execute, Fetch, Field List, Init DB, Kill, Long Data,
   NoAudit, Ping, Prepare, Processlist, Query, Quit, Refresh, Register Slave,
   Reset stmt, Set option, Shutdown, Sleep, Statistics, Table Dump, Time.

.. option:: --file-stats

   Display the audit log file statistics.

.. option:: --format=FORMAT, -f FORMAT

   Output format to display the resulting data. Supported format values: GRID,
   TAB, CSV, VERTICAL and RAW. By default the output format is GRID.

.. option:: --help

   Display a help message and exit.

.. option:: --pattern=PATTERN, -e PATTERN
   
   Search pattern to retrieve all entries with at least one attribute value
   matching the specified pattern. By default the standard SQL **LIKE**
   patterns are used for matching. If the :option:`--regexp` option is set, 
   then **REGEXP** patterns must be specified for matching.

.. option:: --query-type=QUERY_TYPE

   Comma-separated list of SQL statements/commands to search for all log
   entries matching the specified query types. Supported values: CREATE,
   ALTER, DROP, TRUNCATE, RENAME, GRANT, REVOKE, SELECT, INSERT, UPDATE,
   DELETE, COMMIT, SHOW, SET, CALL, PREPARE, EXECUTE, DEALLOCATE.

.. option:: --regexp, --basic-regexp, -G

   Indicates that pattern matching will be performed using regular expression
   **REGEXP** (from Python re module). By default the simple standard SQL
   **LIKE** patterns are used for matching. This affects how the value
   specified by the :option:`--pattern` option is interpreted.

.. option:: --start-date=START_DATE

   Starting date/time to retrieve log entries from the specified date/time
   range. If not specified or the value is 0, all entries from the start of
   the log are displayed. Accepted formats: yyyy-mm-ddThh:mm:ss or yyyy-mm-dd.

.. option:: --users=USERS, -u USERS

   Comma-separated list of user names to search for associated log entries.
   Example: joe,sally,nick.

.. option::  --verbose, -v

   Specify how much information to display. Use this option
   multiple times to increase the amount of information.  For example,
   :option:`-v` = verbose, :option:`-vv` = more verbose, :option:`-vvv` =
   debug.

.. option:: --version

   Display version information and exit.


NOTES
-----

This utility can only be applied to valid audit log files from servers with
the audit log plug-in.

This utility requires the use of Python version 2.7 or higher, but does not 
support Python 3.

Single or double quote characters (respectively, **'** or **"**) can be used
around option values. In fact, quotes are required to set some options values
correctly (e.g., values with whitespace). For example, to specify the event
types *Create DB* and *Drop DB* with the :option:`--event-type` option, the
following syntax must be used: ``--event-type='Create DB,Drop DB'`` or 
``--event-type="Create DB,Drop DB"``.


EXAMPLES
--------

To display the audit log file statistics and output the results in CSV format,
run the following command::

  $ mysqlauditgrep --file-stats --format=CSV /SERVER/data/audit.log
  #
  # Audit Log File Statistics:
  #
  File,Size,Created,Last Modified
  audit.log,9101,Thu Sep 27 13:33:11 2012,Thu Oct 11 17:40:35 2012

  #
  # Audit Log Startup Entries:
  #

  SERVER_ID,STARTUP_OPTIONS,NAME,TIMESTAMP,MYSQL_VERSION,OS_VERSION,VERSION
  1,/SERVER/sql/mysqld --defaults-file=/SERVER/my.cnf,Audit,2012-09-27T13:33:11,5.5.29-log,x86_64-Linux,1

To display the audit log entries of specific users, use the following
command::

  $ mysqlauditgrep --users=tester1,tester2 /SERVER/data/audit.log
  +---------+------------+----------+----------------------+----------------+------------+----------+------------+------------+---------------------------------------------------------------------------+
  | STATUS  | SERVER_ID  | NAME     | TIMESTAMP            | CONNECTION_ID  | HOST       | USER     | PRIV_USER  | IP         | SQLTEXT                                                                   |
  +---------+------------+----------+----------------------+----------------+------------+----------+------------+------------+---------------------------------------------------------------------------+
  | 0       | 1          | Connect  | 2012-09-28T11:26:50  | 9              | localhost  | root     | tester1    | 127.0.0.1  | None                                                                      |
  | 0       | 1          | Query    | 2012-09-28T11:26:50  | 9              | None       | root     | tester1    | None       | SET NAMES 'latin1' COLLATE 'latin1_swedish_ci'                            |
  | 0       | 1          | Query    | 2012-09-28T11:26:50  | 9              | None       | root     | tester1    | None       | SET @@session.autocommit = OFF                                            |
  | 0       | 1          | Ping     | 2012-09-28T11:26:50  | 9              | None       | root     | tester1    | None       | None                                                                      |
  | 0       | 1          | Query    | 2012-09-28T11:26:50  | 9              | None       | root     | tester1    | None       | SHOW VARIABLES LIKE 'READ_ONLY'                                           |
  | 0       | 1          | Query    | 2012-09-28T11:26:50  | 9              | None       | root     | tester1    | None       | COMMIT                                                                    |
  | 0       | 1          | Ping     | 2012-09-28T11:26:50  | 9              | None       | root     | tester1    | None       | None                                                                      |
  | 0       | 1          | Query    | 2012-09-28T11:26:50  | 9              | None       | root     | tester1    | None       | SELECT * FROM INFORMATION_SCHEMA.PLUGINS WHERE PLUGIN_NAME LIKE 'audit%'  |
  | 0       | 1          | Query    | 2012-09-28T11:26:50  | 9              | None       | root     | tester1    | None       | COMMIT                                                                    |
  | 0       | 1          | Quit     | 2012-09-28T11:26:50  | 9              | None       | root     | tester1    | None       | None                                                                      |
  | 0       | 1          | Connect  | 2012-10-10T15:55:55  | 11             | localhost  | tester2  | root       | 127.0.0.1  | None                                                                      |
  | 0       | 1          | Query    | 2012-10-10T15:55:55  | 11             | None       | tester2  | root       | None       | select @@version_comment limit 1                                          |
  | 0       | 1          | Query    | 2012-10-10T15:56:10  | 11             | None       | tester2  | root       | None       | show databases                                                            |
  | 1046    | 1          | Query    | 2012-10-10T15:57:26  | 11             | None       | tester2  | root       | None       | show tables test                                                          |
  | 1046    | 1          | Query    | 2012-10-10T15:57:36  | 11             | None       | tester2  | root       | None       | show tables test                                                          |
  | 0       | 1          | Query    | 2012-10-10T15:57:51  | 11             | None       | tester2  | root       | None       | show tables in test                                                       |
  | 0       | 1          | Quit     | 2012-10-10T15:57:59  | 11             | None       | tester2  | root       | None       | None                                                                      |
  | 0       | 1          | Connect  | 2012-10-10T17:35:42  | 12             | localhost  | tester2  | root       | 127.0.0.1  | None                                                                      |
  | 0       | 1          | Query    | 2012-10-10T17:35:42  | 12             | None       | tester2  | root       | None       | select @@version_comment limit 1                                          |
  | 1146    | 1          | Query    | 2012-10-10T17:44:55  | 12             | None       | tester2  | root       | None       | select * from teste.employees where salary > 500 and salary < 1000        |
  | 1046    | 1          | Query    | 2012-10-10T17:47:17  | 12             | None       | tester2  | root       | None       | select * from test_encoding where value = '<>"&'                          |
  | 0       | 1          | Quit     | 2012-10-10T17:47:22  | 12             | None       | tester2  | root       | None       | None                                                                      |
  +---------+------------+----------+----------------------+----------------+------------+----------+------------+------------+---------------------------------------------------------------------------+

To display the audit log entries for a specific date/time range, use the
following command::
  
  $ mysqlauditgrep --start-date=2012-09-27T13:33:47 --end-date=2012-09-28 /SERVER/data/audit.log
  +---------+----------------------+--------+----------------+---------------------------------------------------------------------------+
  | STATUS  | TIMESTAMP            | NAME   | CONNECTION_ID  | SQLTEXT                                                                   |
  +---------+----------------------+--------+----------------+---------------------------------------------------------------------------+
  | 0       | 2012-09-27T13:33:47  | Ping   | 7              | None                                                                      |
  | 0       | 2012-09-27T13:33:47  | Query  | 7              | SELECT * FROM INFORMATION_SCHEMA.PLUGINS WHERE PLUGIN_NAME LIKE 'audit%'  |
  | 0       | 2012-09-27T13:33:47  | Query  | 7              | COMMIT                                                                    |
  | 0       | 2012-09-27T13:34:48  | Quit   | 7              | None                                                                      |
  | 0       | 2012-09-27T13:34:48  | Quit   | 8              | None                                                                      |
  +---------+----------------------+--------+----------------+---------------------------------------------------------------------------+

To display the audit log entries matching a specific SQL **LIKE** pattern, use
the following command::

  $ mysqlauditgrep --pattern="% = ___" /SERVER/data/audit.log
  +---------+----------------------+--------+---------------------------------+----------------+
  | STATUS  | TIMESTAMP            | NAME   | SQLTEXT                         | CONNECTION_ID  |
  +---------+----------------------+--------+---------------------------------+----------------+
  | 0       | 2012-09-27T13:33:39  | Query  | SET @@session.autocommit = OFF  | 7              |
  | 0       | 2012-09-27T13:33:39  | Query  | SET @@session.autocommit = OFF  | 8              |
  | 0       | 2012-09-28T11:26:50  | Query  | SET @@session.autocommit = OFF  | 9              |
  | 0       | 2012-09-28T11:26:50  | Query  | SET @@session.autocommit = OFF  | 10             |
  +---------+----------------------+--------+---------------------------------+----------------+

To display the audit log entries matching a specific **REGEXP** pattern, use
the following command::

  $ mysqlauditgrep --pattern=".* = ..." --regexp /SERVER/data/audit.log
  +---------+----------------------+--------+---------------------------------------------------+----------------+
  | STATUS  | TIMESTAMP            | NAME   | SQLTEXT                                           | CONNECTION_ID  |
  +---------+----------------------+--------+---------------------------------------------------+----------------+
  | 0       | 2012-09-27T13:33:39  | Query  | SET @@session.autocommit = OFF                    | 7              |
  | 0       | 2012-09-27T13:33:39  | Query  | SET @@session.autocommit = OFF                    | 8              |
  | 0       | 2012-09-28T11:26:50  | Query  | SET @@session.autocommit = OFF                    | 9              |
  | 0       | 2012-09-28T11:26:50  | Query  | SET @@session.autocommit = OFF                    | 10             |
  | 1046    | 2012-10-10T17:47:17  | Query  | select * from test_encoding where value = '<>"&'  | 12             |
  +---------+----------------------+--------+---------------------------------------------------+----------------+

To display the audit log entries of specific query types, use the following
command::
  
  $ mysqlauditgrep --query-type=show,SET /SERVER/data/audit.log
  +---------+----------------------+--------+-------------------------------------------------+----------------+
  | STATUS  | TIMESTAMP            | NAME   | SQLTEXT                                         | CONNECTION_ID  |
  +---------+----------------------+--------+-------------------------------------------------+----------------+
  | 0       | 2012-09-27T13:33:39  | Query  | SET NAMES 'latin1' COLLATE 'latin1_swedish_ci'  | 7              |
  | 0       | 2012-09-27T13:33:39  | Query  | SET @@session.autocommit = OFF                  | 7              |
  | 0       | 2012-09-27T13:33:39  | Query  | SHOW VARIABLES LIKE 'READ_ONLY'                 | 7              |
  | 0       | 2012-09-27T13:33:39  | Query  | SHOW VARIABLES LIKE 'datadir'                   | 7              |
  | 0       | 2012-09-27T13:33:39  | Query  | SHOW VARIABLES LIKE 'basedir'                   | 7              |
  | 0       | 2012-09-27T13:33:39  | Query  | SET NAMES 'latin1' COLLATE 'latin1_swedish_ci'  | 8              |
  | 0       | 2012-09-27T13:33:39  | Query  | SET @@session.autocommit = OFF                  | 8              |
  | 0       | 2012-09-27T13:33:39  | Query  | SHOW VARIABLES LIKE 'READ_ONLY'                 | 8              |
  | 0       | 2012-09-27T13:33:39  | Query  | SHOW VARIABLES LIKE 'basedir'                   | 8              |
  | 0       | 2012-09-28T11:26:50  | Query  | SET NAMES 'latin1' COLLATE 'latin1_swedish_ci'  | 9              |
  | 0       | 2012-09-28T11:26:50  | Query  | SET @@session.autocommit = OFF                  | 9              |
  | 0       | 2012-09-28T11:26:50  | Query  | SHOW VARIABLES LIKE 'READ_ONLY'                 | 9              |
  | 0       | 2012-09-28T11:26:50  | Query  | SET NAMES 'latin1' COLLATE 'latin1_swedish_ci'  | 10             |
  | 0       | 2012-09-28T11:26:50  | Query  | SET @@session.autocommit = OFF                  | 10             |
  | 0       | 2012-09-28T11:26:50  | Query  | SHOW VARIABLES LIKE 'READ_ONLY'                 | 10             |
  | 0       | 2012-09-28T11:26:50  | Query  | SET @@GLOBAL.audit_log_flush = ON               | 10             |
  | 0       | 2012-09-28T11:26:50  | Query  | SHOW VARIABLES LIKE 'audit_log_policy'          | 10             |
  | 0       | 2012-09-28T11:26:50  | Query  | SHOW VARIABLES LIKE 'audit_log_rotate_on_size'  | 10             |
  | 0       | 2012-10-10T15:56:10  | Query  | show databases                                  | 11             |
  | 1046    | 2012-10-10T15:57:26  | Query  | show tables test                                | 11             |
  | 1046    | 2012-10-10T15:57:36  | Query  | show tables test                                | 11             |
  | 0       | 2012-10-10T15:57:51  | Query  | show tables in test                             | 11             |
  +---------+----------------------+--------+-------------------------------------------------+----------------+

To display the audit log entries of specific event types, use the following
command::
  
  $ mysqlauditgrep --event-type="Ping,cONNECT" /SERVER/data/audit.log
  +---------+----------+----------------------+----------------+------------+---------+------------+------------+
  | STATUS  | NAME     | TIMESTAMP            | CONNECTION_ID  | HOST       | USER    | PRIV_USER  | IP         |
  +---------+----------+----------------------+----------------+------------+---------+------------+------------+
  | 0       | Connect  | 2012-09-27T13:33:39  | 7              | localhost  | root    | root       | 127.0.0.1  |
  | 0       | Ping     | 2012-09-27T13:33:39  | 7              | None       | None    | None       | None       |
  | 0       | Ping     | 2012-09-27T13:33:39  | 7              | None       | None    | None       | None       |
  | 0       | Ping     | 2012-09-27T13:33:39  | 7              | None       | None    | None       | None       |
  | 0       | Ping     | 2012-09-27T13:33:39  | 7              | None       | None    | None       | None       |
  | 0       | Connect  | 2012-09-27T13:33:39  | 8              | localhost  | root    | root       | 127.0.0.1  |
  | 0       | Ping     | 2012-09-27T13:33:39  | 8              | None       | None    | None       | None       |
  | 0       | Ping     | 2012-09-27T13:33:39  | 8              | None       | None    | None       | None       |
  | 0       | Ping     | 2012-09-27T13:33:47  | 7              | None       | None    | None       | None       |
  | 0       | Connect  | 2012-09-28T11:26:50  | 9              | localhost  | root    | tester     | 127.0.0.1  |
  | 0       | Ping     | 2012-09-28T11:26:50  | 9              | None       | None    | None       | None       |
  | 0       | Ping     | 2012-09-28T11:26:50  | 9              | None       | None    | None       | None       |
  | 0       | Connect  | 2012-09-28T11:26:50  | 10             | localhost  | root    | root       | 127.0.0.1  |
  | 0       | Ping     | 2012-09-28T11:26:50  | 10             | None       | None    | None       | None       |
  | 0       | Ping     | 2012-09-28T11:26:50  | 10             | None       | None    | None       | None       |
  | 0       | Ping     | 2012-09-28T11:26:50  | 10             | None       | None    | None       | None       |
  | 0       | Ping     | 2012-09-28T11:26:50  | 10             | None       | None    | None       | None       |
  | 0       | Ping     | 2012-09-28T11:26:50  | 10             | None       | None    | None       | None       |
  | 0       | Connect  | 2012-10-10T15:55:55  | 11             | localhost  | tester  | root       | 127.0.0.1  |
  | 0       | Connect  | 2012-10-10T17:35:42  | 12             | localhost  | tester  | root       | 127.0.0.1  |
  +---------+----------+----------------------+----------------+------------+---------+------------+------------+

To display the audit log entries matching several search criterion, use the
following command::
  
  $ mysqlauditgrep --users=root --start-date=0 --end-date=2012-10-10 --event-type=Query --query-type=SET --pattern="%audit_log%" /SERVER/data/audit.log
  +---------+------------+--------+----------------------+----------------+-------+------------+------------------------------------+
  | STATUS  | SERVER_ID  | NAME   | TIMESTAMP            | CONNECTION_ID  | USER  | PRIV_USER  | SQLTEXT                            |
  +---------+------------+--------+----------------------+----------------+-------+------------+------------------------------------+
  | 0       | 1          | Query  | 2012-09-28T11:26:50  | 10             | root  | root       | SET @@GLOBAL.audit_log_flush = ON  |
  +---------+------------+--------+----------------------+----------------+-------+------------+------------------------------------+


COPYRIGHT
---------

Copyright (c) 2012, Oracle and/or its affiliates. All rights reserved.

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
