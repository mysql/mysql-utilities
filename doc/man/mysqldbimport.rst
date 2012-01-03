.. _`mysqldbimport`:

#####################################################################
``mysqldbimport`` - Import Object Definitions or Data into a Database
#####################################################################

SYNOPSIS
--------

::

 mysqldbimport --server=<user>[<passwd>]@<host>:[<port>][:<socket>]
             [--quiet | --help | --no-headers | --dryrun |
             --skip=(TABLES,TRIGGERS,VIEWS,PROCEDURES,FUNCTIONS,
             EVENTS,GRANTS,DATA,CREATE_DB)* | --skip-blobs | --verbose |
             --version | --bulk-insert | --drop-first ]
             --import=[DEFINITIIONS|DATA|BOTH] |
             --format=[SQL|S|GRID|G|TAB|T|CSV|C|VERTICAL|V] |
             --new-storage-engine=<engine> | --default-storage-engine=<engine>
             <file> [|,<file>]

DESCRIPTION
-----------

This utility permits a database administrator to import the metadata
(objects) or data for one or more databases from one or more files in
either SQL, CSV, TAB, GRID, or VERTICAL formats. These formats are the
output of the mysqldbexport utility. The utility enables you to import
either the object definitions, the data, or both for a list of databases.

You can also skip objects by type using the :option:`--skip` option
and list the objects you want to skip. This enables you to extract a
particular set of objects, say, for importing only events (by
excluding all other types). Similarly, you can skip creating blob
UPDATE commands by specifying the :option:`--skip-blobs` option.

To specify how to display output, use one of the following values
with the :option:`--format` option:

**SQL** (default)
  Display output using SQL statements. For definitions, this consists of
  the appropriate **CREATE** and **GRANT** statements. For data, this
  is an **INSERT** statement (or bulk insert if the
  :option:`--bulk-insert` option is specified).

**GRID**
  Display output formatted like that of the mysql monitor in a grid
  or table layout.

**CSV**
  Display output in comma-separated values format.

**TAB**
  Display output in tab-separated format.

**VERTICAL**
  Display output in a single column similar to the ``\G`` command
  for the mysql monitor.

To turn off the headers when using CSV or TAB display format, specify
the :option:`--no-headers` option.

To turn off all feedback information, specify the :option:`--quiet` option.

To change the storage engine for all tables on the destination, specify the
new engine with the :option:`--new-storage-engine` option. If the new engine
specified is available on the destination, all tables will be changed to use
the engine.

Similarly, you can specify a different default storage engine with the
:option:`--default-storage-engine` option. If the engine specified is
available on the destination, any table that specifies a storage engine that
is not on the destination will use the new default engine. Note that this
overrides the default storage engine mechanism on the server.

If the option :option:`--default-storage-engine` or
:option:`--new-storage-engine` is supplied and the storage engine specified
does not exist, a warning shall be issued and the default storage engine
setting on the server shall be used instead.

You must provide connection parameters (user, host, password, and
so forth), for an account that has the appropriate privileges to
access all objects in the operation.
See :ref:`mysqldbimport-notes` for more details.

OPTIONS
-------

**mysqldbimport** accepts the following command-line options:

.. option:: --help

   Display a help message and exit.

.. option:: --bulk-insert, -b

   Use bulk insert statements for data (default:False).

.. option:: --default-storage-engine=<def_engine>

   Change all tables to use this storage engine if the original storage engine
   does not exist on the destination.

.. option:: --drop-first, -d

   Drop database before importing.

.. option:: --dryrun

   Import the files and generate the statements but do not execute
   them - useful for testing file validity.

.. option:: --format=<format>, -f<format>

   Display the output in either SQL|S (default), GRID|G, TAB|T, CSV|C,
   or VERTICAL|V format.

.. option:: --import=<import_type>, -i<import_type>

   Control the import of either DATA|D = only the table data for the
   tables in the database list, DEFINITIONS|F = import only the
   definitions for the objects in the database list, or BOTH|B =
   import the metadata followed by the data (default: import metadata).
   
.. option:: --new-storage-engine=<new_engine>

   Change all tables to use this storage engine if storage engine exists on the
   destination.

.. option::  --no-headers, -h

   Do not display the column headers. This option is ignored for GRID-format
   output.

.. option:: --quiet, -q

   Turn off all messages for quiet execution.

.. option:: --server=<SERVER>

   Connection information for the server in the format:
   <user>:<password>@<host>:<port>:<socket>

.. option:: --skip=<skip_objects>

   Specify objects to skip in the operation as a comma-separated list
   (no spaces). Permitted values are CREATE_DB, DATA, EVENTS, FUNCTIONS,
   GRANTS, PROCEDURES, TABLES, TRIGGERS, VIEWS.

.. option:: --skip-blobs

   Do not import BLOB data.

.. option:: --verbose, -v

   Specify how much information to display. Use this option
   multiple times to increase the amount of information.  For example, -v =
   verbose, -vv = more verbose, -vvv = debug.

.. option:: --version

   Display version information and exit.

.. _`mysqldbimport-notes`:

NOTES
-----

The login user must have the appropriate permissions to create new
objects, read the old database, access (read) the mysql database, and
grant privileges.

Actual privileges needed may differ from installation to installation
depending on the security privileges present and whether the database
contains certain objects such as views or events and whether binary
logging is turned on (hence the need for **SUPER**).

Some combinations of the options may result in errors during the
operation.  For example, eliminating tables but not views may result
in an error when the view is imported on another server.

The --new-storage-engine and --default-storage-engine options apply to all
tables in the operation.

EXAMPLES
--------

To import the metadata of the database 'util_test' to server1 on port 3306
using a file in CSV format, use this command::

    $ mysqldbimport --import=definitions --server=root@localhost \
      --format=csv data.csv
    # Source on localhost: ... connected.
    # Importing definitions from data.csv.
    #...done.

Similarly, to import the data of the database 'util_test' to server1 on port
3306 producing bulk insert statements, use this command::

    $ mysqldbimport --import=data --bulk-insert \
      --server=root@localhost --format=csv data.csv
    # Source on localhost: ... connected.
    # Importing data from data.csv.
    #...done.

Also, to import both the data and definitions of the database 'util_test' to
server1 on port 3306 producing bulk insert statements from a file that contains
SQL statements, use this command::

    $ mysqldbimport --import=both --bulk-insert \
      --server=root@localhost --format=sql data.sql
    # Source on localhost: ... connected.
    # Importing definitions and data from data.sql.
    #...done.

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
