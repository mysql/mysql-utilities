.. _`mysqldbimport`:

#####################################################################
``mysqldbimport`` - Import Object Definitions or Data into a Database
#####################################################################

SYNOPSIS
--------

::

 mysqldbimport --server=<user>[:<passwd>]@<host>[:<port>][:<socket>]
             [--quiet | --help | --no-headers | --dryrun |
             --skip=(TABLES,TRIGGERS,VIEWS,PROCEDURES,FUNCTIONS,
             EVENTS,GRANTS,DATA,CREATE_DB)* | --skip-blobs | --verbose |
             --version | --bulk-insert | --drop-first ]
             --import=[definitiions|data|both] |
             --format=[sql|grid|tab|csv|vertical] |
             --new-storage-engine=<engine> | --default-storage-engine=<engine>
             <file> [|,<file>]

DESCRIPTION
-----------

This utility imports the metadata (object definitions) or data for
one or more databases from one or more files in any of SQL, CSV,
TAB, GRID, or VERTICAL formats. These formats are the output of the
:command:`mysqldbexport` utility.  For a list of databases, the :command:`mysqldbimport`
utility enables you to import the object definitions, the data, or
both.

If an object exists on the destination server with the same name as an
imported object, it is dropped first before importing the new object.

You can also skip objects by type using the :option:`--skip` option
with a list of the objects to skip. This enables you to extract a
and listing the objects to skip. This enables you to extract a
particular set of objects, say, for importing only events (by
excluding all other types). Similarly, you can skip creating blob
UPDATE commands by specifying the :option:`--skip-blobs` option.

To specify the input format, use one of the following values
with the :option:`--format` option:

**sql** (default)
  Input consists of SQL statements. For definitions, this consists of
  the appropriate **CREATE** and **GRANT** statements. For data, this
  is an **INSERT** statement (or bulk insert if the
  :option:`--bulk-insert` option is specified).

**grid**
  Display output in grid or table format like that of the
  :command:`mysql` monitor.

**csv**
  Input is formatted in comma-separated values format.

**tab**
  Input is formatted in tab-separated format.

**vertical**
  Display output in single-column format like that of the ``\G`` command
  for the :command:`mysql` monitor.

To indicate that input in CSV or TAB format does not contain column headers,
specify the :option:`--no-headers` option.

To turn off all feedback information, specify the :option:`--quiet` option.

By default, each table is created on the destination server using the same
storage engine as the original table.  To override this and specify the
storage engine to be used for all tables created on the destination server,
use the :option:`--new-storage-engine` option. If the destination server
supports the new engine, all tables will use that engine.

To specify the storage engine to use for tables for which the destination
server does not support the original storage engine on the source server,
use the :option:`--default-storage-engine` option.

The :option:`--new-storage-engine` option takes precedence over
:option:`--default-storage-engine` if both are given.

If the :option:`--new-storage-engine` or :option:`--default-storage-engine`
option is given and the destination server does not support the
specified storage engine, a warning is issued and the server's default storage
engine setting is used instead.

You must provide connection parameters (user, host, password, and
so forth) for an account that has the appropriate privileges to
access all objects in the operation.
For details, see :ref:`mysqldbimport-notes`.

OPTIONS
-------

:command:`mysqldbimport` accepts the following command-line options:

.. option:: --help

   Display a help message and exit.

.. option:: --bulk-insert, -b

   Use bulk insert statements for data (default:False).

.. option:: --default-storage-engine=<def_engine>

   The engine to use for tables if the destination server does not support
   the original storage engine on the source server.

.. option:: --drop-first, -d

   Drop each database to be imported if exists before importing anything into
   it.

.. option:: --dryrun

   Import the files and generate the statements but do not execute
   them. This is useful for testing input file validity.

.. option:: --format=<format>, -f<format>

   Specify the input format. Permitted format values are
   sql, grid, tab, csv, and vertical. The default is sql.
   
.. option:: --import=<import_type>, -i<import_type>

   Specify the import format. Permitted format values are definitions =
   import only the definitions (metadata) for the objects in the database list,
   data = import only the table data for the tables in the database list,
   and both = import the definitions and the data. The default is
   definitions.

   If you attempt to import objects into an existing database, the result
   depends on the import format. If the format is definitions or both, an
   error occurs unless :option:`--drop-first` is given. If the format is
   data, imported table data is added to existing table data.
   
.. option:: --new-storage-engine=<new_engine>

   The engine to use for all tables created on the destination server.

.. option::  --no-headers, -h

   Input does not contain column headers. This option applies only for
   CSV and TAB input.

.. option:: --quiet, -q

   Turn off all messages for quiet execution.

.. option:: --server=<SERVER>

   Connection information for the server in the format:
   <user>[:<passwd>]@<host>[:<port>][:<socket>]

.. option:: --skip=<skip_objects>

   Specify objects to skip in the operation as a comma-separated list
   (no spaces). Permitted values are CREATE_DB, DATA, EVENTS, FUNCTIONS,
   GRANTS, PROCEDURES, TABLES, TRIGGERS, and VIEWS.

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
objects, access (read) the mysql database, and grant privileges.
If a database to be imported already exists, the user must have read
permission for it, which is needed to check the existence of objects in the
database.

Actual privileges needed may differ from installation to installation
depending on the security privileges present and whether the database
contains certain objects such as views or events and whether binary
logging is turned on (hence the need for **SUPER**).

Some combinations of the options may result in errors during the
operation.  For example, eliminating tables but not views may result
in an error when the view is imported on another server.

The :option:`--new-storage-engine` and :option:`--default-storage-engine`
options apply to all tables in the operation.

The permitted values for the :option:`--format` and :option:`--import` options
are case insensitive. The option also permits the user to specify a prefix for
a valid value. For example, --format=g will specify the grid format. An error
will be generated if a prefix matches more than one valid value.

EXAMPLES
--------

To import the metadata of the database 'util_test' to server1 on port 3306
using a file in CSV format, use this command::

    $ mysqldbimport --server=root@localhost --import=definitions \
      --format=csv data.csv
    # Source on localhost: ... connected.
    # Importing definitions from data.csv.
    #...done.

Similarly, to import the data of the database 'util_test' to server1 on port
3306, importing the data using bulk insert statements, use this command::

    $ mysqldbimport --server=root@localhost --import=data \
      --bulk-insert --format=csv data.csv
    # Source on localhost: ... connected.
    # Importing data from data.csv.
    #...done.

Also, to import both the data and definitions of the database 'util_test' to
server1 on port 3306, importing the data using bulk insert statements from a
file that contains SQL statements, use this command::

    $ mysqldbimport --server=root@localhost --import=both \
      --bulk-insert --format=sql data.sql
    # Source on localhost: ... connected.
    # Importing definitions and data from data.sql.
    #...done.

COPYRIGHT
---------

Copyright (c) 2010, 2012, Oracle and/or its affiliates. All rights reserved.

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
