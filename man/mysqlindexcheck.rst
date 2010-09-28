=================
 mysqlindexcheck
=================

----------------------------------------
check for duplicate or redundant indexes
----------------------------------------

:Author: The Oracle MySQL Utilities team
:Date: 2010-09-09
:Copyright: GPL
:Version: 1.0.0
:Manual group: database 

SYNOPSIS
========

::

 mysqlcheckindex --source=<user>[<passwd>]@<host>:[<port>][:<socket>]
                 [[ --help | --version ] |
                 [ --show-drops | --skip | --verbose | --show-indexes |
                   --silent | --index-format=[TABLE|SQL|TAB|CSV] |
                   --best | --worst ]
                 <db> | [ ,<db> | ,<db.table> | , <db.table>]]

DESCRIPTION
===========

This document describes the mysqlcheckindex utility. This utility
is used to read the indexes for one or more tables and identify duplicate
and potentially redundant indexes. The following rules are applied during
the operation.

* BTREE : idx_b is redundant to idx_a iff the first n columns in idx_b
  also appear in idx_a. Order and uniqueness count.

* HASH : idx_a and idx_b are duplicates iff they contain the same
  columns in the same order and uniqueness counts.

* SPATIAL : idx_a and idx_b are duplicates iff they contain the same 
  column (only 1 column is permitted)

* FULLTEXT : idx_b is redundant to idx_a iff all columns in idx_b are 
  included in idx_a (order is not important)

You can specify scanning all databases (except the internal databases
mysql, INFORMATION_SCHEMA, PERFORMANCE_SCHEMA) by not specifying any
databases or tables, or you can specify a list of databases or tables
(in the form db.tablename) which will limit the scan to only those tables
in the databases listed and those tables listed.

If you want to see the example DROP statements to drop the redundant
indexes, you can specify the -d option (see below). You can also
examine the existing indexes using the -v option which prints
the equivalent CREATE INDEX (or ALTER TABLE for primary keys). 

For example, to scan all of the tables in my_db, tables db1.t1 and db2.t2
and see the indexes and the DROP statements for the duplicate and
redundant indexes, use this command:

::

   mysqlcheckindex --source=root@localhost:3306 -i \
                   my_db db1.t1 db2.t2 

You can also display the best and worst non-primary key indexes for each table
with the --best and --worst options. The data will show the top 5 indexes from
tables with 10 or more rows.

You can change the display format of the index lists for --show-indexes,
--best, and --worst in one of the following formats:

* TABLE (default) : print a mysql-like table output

* TAB : print using tabs for separation

* CSV : print using commas for separation

* SQL : print SQL statements rather than a list.

Note: the --best and --worst lists cannot be printed as SQL statements.

You must provide login information (e.g., user, host, password, etc.
for a user that has the appropriate rights to access all objects
in the operation.

OPTIONS
=======

--version
  show version number and exit

--help
  show the help page

--source=SOURCE
  connection information for source server in the form:
  <user>:<password>@<host>:<port>:<socket>

-d, --show-drops
  display DROP statements for dropping indexes

-i, --show-indexes
  display indexes for each table

-s, --skip
  skip tables that do not exist

-v, --verbose
  display additional information during operation

--silent
  do not display informational messages

--index-format=INDEX_FORMAT
  display the list of indexes per table in either SQL, TABLE (default), TAB,
  or CSV format

--stats
show index performance statistics

--first=FIRST
limit index statistics to the best N indexes

--last=LAST
limit index statistics to the worst N indexes


FILES
=====

- mysqlindexcheck.py  the utility script
- mysql               the MySQL utilities library


NOTES
=====

The login user must have the appropriate permissions to read all databases
and tables listed.
