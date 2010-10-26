=============
 mysqlexport
=============

SYNOPSIS
========

::

 mysqlexport --server=<user>[<passwd>]@<host>:[<port>][:<socket>]
             (<db_name>[, <db_name>])+ [--silent | --help | --no-headers | 
             --skip=(TABLES,TRIGGERS,VIEWS,PROCEDURES,FUNCTIONS,
             EVENTS,GRANTS,DATA,CREATE_DB)* | --skip-blobs | --help |
             --version | --bulk-insert]

DESCRIPTION
===========

This document describes the ''mysqlexport'' utility. This utility
permits a database administrator to export the metadata (objects) or data
from one or more databases.

The utility allows you to export either the object definitions, the data, or
both for a list of databases. For example, to export the metadata of  the
database 'dev' from server1 on port 3306 producing CREATE statements, use
this command:

::

  mysqlexport --server=root@server1:3306 --export=definitions dev
  
Similarly, to export the data of the database 'dev' from server1 on port 3306
producing bulk insert statements, use this command:

::

  mysqlexport --server=root@server1:3306 --bulk-insert --export=data dev

Also, to export both the data and definitions of the database 'dev' from
server1 on port 3306 producing bulk insert statements, use this command:

::

  mysqlexport --server=root@server1:3306 --bulk-insert --export=both dev

You can also skip objects by type using the --skip option and list the objects
you want to skip. This can allow you to extract a particular set of objects,
say, for exporting only events (by excluding all other types). Similarly, you
can skip creating blob UPDATE commands by specifying the --skip-blobs option.

You also have the choice to view the output in one of the following formats
using the --format option.

* SQL : Displays the output using SQL statements. For definitions, this is
  the appropriate CREATE and GRANT statements. For data, this is an INSERT
  statement (or bulk insert if the --bulk-insert options is specified).

* GRID : Displays output formatted like that of the mysql monitor in a grid
  or table layout.

* CSV : Displays the output in a comma-separated list.

* TAB : Displays the output in a tab-separated list.

* VERTICAL : Displays the output in a single column similar to the \G option
  for the mysql monitor commands.
  
You also have the option to specify how much data to display in one of the
following displays using the --display option.

* BRIEF : Show only the minimal columns for recreating the objects.

* FULL : Show the complete column list for recreating the objects. 

* NAMES : Show only the names of the objects.

Note: When combining --format and --display, the --display option is ignored
for SQL generation (--format=SQL). 

You can turn off the headers when using formats CSV and TAB by specifying
the --no-headers option.

You can turn off all feedback information by specifying the --silent option.

You must provide login information (e.g., user, host, password, etc.
for a user that has the appropriate rights to access all objects
in the operation. See **notes** below for more details.

OPTIONS
=======

--version             show program's version number and exit

--help                

--server=SERVER       connection information for the server in the form:
                      <user>:<password>@<host>:<port>:<socket>

-f FORMAT, --format=FORMAT
                      display the output in either SQL|S (default), GRID|G,
                      TAB|T, CSV|C, or VERTICAL|V format

-d DISPLAY, --display=DISPLAY
                      control the number of columns shown: BRIEF = minimal
                      columns for object creation (default), FULL = all
                      columns, NAMES = only object names (not valid for
                      --format=SQL)

-e EXPORT, --export=EXPORT
                      control the export of either DATA|D = only the table
                      data for the tables in the database list,
                      DEFINITIONS|F = export only the definitions for the
                      objects in the database list, or BOTH|B = export the
                      metadata followed by the data (default: export
                      metadata)

-b, --bulk-insert     Use bulk insert statements for data (default:False)

-h, --no-headers      do not display the column headers - ignored for GRID
                      format

--silent              do not display feedback information during operation

--debug               print debug information

--skip=SKIP_OBJECTS   specify objects to skip in the operation in the form
                      of a comma-separated list (no spaces). Valid values =
                      TABLES, VIEWS, TRIGGERS, PROCEDURES, FUNCTIONS,
                      EVENTS, GRANTS, DATA, CREATE_DB

--skip-blobs          Do not export blob data.


FILES
=====

- ''mysqlexport.py''    the utility script
- ''mysql''             the MySQL utilities library

NOTES
=====

The login user must have the appropriate permissions to create new objects,
read the old database, access (read) the mysql database, and grant privileges. 

To export all objects from a source, the user must have ''SELECT'' and
''SHOW VIEW'' privileges on the database as well as ''SELECT'' on the mysql
database.

Actual privileges needed may differ from installation to installation
depending on the security privileges present and whether the database contains
certain objects (e.g. views, events) and whether binary logging is turned
on (i.e. the need for ''SUPER'').

NOTICE
======

Some combinations of the options may result in errors during the operation.
For example, eliminating tables but not views may result in an error when the
view is imported on another server.

