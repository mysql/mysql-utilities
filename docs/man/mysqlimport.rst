.. _`mysqlimport`:

###################################################################
``mysqlimport`` - Import object definitions or data into a database
###################################################################

SYNOPSIS
--------

::

 mysqlimport --server=<user>[<passwd>]@<host>:[<port>][:<socket>]
             (<db_name>[, <db_name>])+ [--silent | --help | --no-headers |
             --skip=(TABLES,TRIGGERS,VIEWS,PROCEDURES,FUNCTIONS,
             EVENTS,GRANTS,DATA,CREATE_DB)* | --skip-blobs | --help |
             --version | --bulk-insert] [<file_name> |, <file_name>]

DESCRIPTION
-----------

This utility permits a database administrator to import the metadata
(objects) or data for one or more databases from one or more files in
either SQL, CSV, TAB, GRID, or VERTICAL formats. These formats are the
output of the mysqlexport utility.

The utility allows you to import either the object definitions, the data, or
both for a list of databases. For example, to import the metadata of the
database 'dev' to server1 on port 3306 using a file containing SQL statements,
use this command::

  mysqlimport --server=root@server1:3306 --import=definitions dev.sql

Similarly, to import the data of the database 'dev' to server1 on port 3306
producing bulk insert statements, use this command::

  mysqlimport --server=root@server1:3306 --bulk-insert --import=data dev.sql

Also, to import both the data and definitions of the database 'dev' to
server1 on port 3306 producing bulk insert statements, use this command::

  mysqlimport --server=root@server1:3306 --bulk-insert --import=both dev.sql

You can also skip objects by type using the :option:`--skip` option
and list the objects you want to skip. This can allow you to extract a
particular set of objects, say, for importing only events (by
excluding all other types). Similarly, you can skip creating blob
UPDATE commands by specifying the :option:`--skip-blobs` option.

You also have the choice to view the output in one of the following formats
using the :option:`--format` option.

**SQL**
  Displays the output using SQL statements. For definitions, this is
  the appropriate CREATE and GRANT statements. For data, this is an
  INSERT statement (or bulk insert if the :option:`--bulk-insert` options is
  specified).

**GRID**
  Displays output formatted like that of the mysql monitor in a grid
  or table layout.

**CSV**
  Displays the output in a comma-separated list.

**TAB**
  Displays the output in a tab-separated list.

**VERTICAL**
  Displays the output in a single column similar to the \G option for
  the mysql monitor commands.

You can turn off the headers when using formats CSV and TAB by
specifying the :option:`--no-headers` option.

You can turn off all feedback information by specifying the
:option:`--silent` option.

You must provide login information (e.g., user, host, password, etc.
for a user that has the appropriate rights to access all objects in
the operation. See :ref:`mysqlimport-notes` below for more details.

OPTIONS
-------

.. option:: --version

   show program's version number and exit

.. option:: --help

.. option:: --server=SERVER

   connection information for the server in the form:
   <user>:<password>@<host>:<port>:<socket>

.. option:: -f FORMAT, --format=FORMAT

   display the output in either SQL|S (default), GRID|G, TAB|T, CSV|C,
   or VERTICAL|V format

.. option:: -i import, --import=import

   control the import of either DATA|D = only the table data for the
   tables in the database list, DEFINITIONS|F = import only the
   definitions for the objects in the database list, or BOTH|B =
   import the metadata followed by the data (default: import metadata)

.. option:: -d, --drop-first

   Drop database before importing.

.. option:: --dryrun

   import the files and generate the statements but do not execute
   them - useful for testing file validity

.. option:: -b, --bulk-insert

   Use bulk insert statements for data (default:False)

.. option:: -h, --no-headers

   do not display the column headers - ignored for GRID format

.. option:: --silent

   do not display feedback information during operation

.. option:: --debug

   print debug information

.. option:: --skip <skip-objects>

   specify objects to skip in the operation in the form of a
   comma-separated list (no spaces). Valid values = TABLES, VIEWS,
   TRIGGERS, PROCEDURES, FUNCTIONS, EVENTS, GRANTS, DATA, CREATE_DB

.. option:: --skip-blobs

   Do not import blob data.


.. _`mysqlimport-notes`:

NOTES
-----

The login user must have the appropriate permissions to create new
objects, read the old database, access (read) the mysql database, and
grant privileges.

Actual privileges needed may differ from installation to installation
depending on the security privileges present and whether the database
contains certain objects (e.g. views, events) and whether binary
logging is turned on (i.e. the need for **SUPER**).

NOTICE
------

Some combinations of the options may result in errors during the
operation.  For example, eliminating tables but not views may result
in an error when the view is imported on another server.

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
