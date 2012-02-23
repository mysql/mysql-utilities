.. _`mysqldbimport`:

#####################################################################
``mysqldbimport`` - Import Object Definitions or Data into a Database
#####################################################################

SYNOPSIS
--------

::

 mysqldbimport [options] import_file ...

DESCRIPTION
-----------

This utility imports metadata (object definitions) or data or both for
one or more databases from one or more files.

If an object exists on the destination server with the same name as an
imported object, it is dropped first before importing the new object.

To skip objects by type, use the :option:`--skip` option
with a list of the objects to skip. This enables you to extract a
particular set of objects, say, for importing only events (by
excluding all other types). Similarly, to skip creation of **UPDATE**
statements for ``BLOB`` data, specify the :option:`--skip-blobs` option.

To specify the input format, use one of the following values with the
:option:`--format` option. These correspond to the output formats of the
:command:`mysqldbexport` utility:

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

To indicate that input in **csv** or **tab** format does not contain column
headers, specify the :option:`--no-headers` option.

To turn off all feedback information, specify the :option:`--quiet` option.

By default, the utility creates each table on the destination server using
the same storage engine as the original table.  To override this and specify
the storage engine to use for all tables created on the destination server,
use the :option:`--new-storage-engine` option. If the destination server
supports the new engine, all tables use that engine.

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

   Use bulk insert statements for data.

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
   **sql**, **grid**, **tab**, **csv**, and **vertical**. The default is
   **sql**.
   
.. option:: --import=<import_type>, -i<import_type>

   Specify the import format. Permitted format values are **definitions** =
   import only the definitions (metadata) for the objects in the database list,
   **data** = import only the table data for the tables in the database list,
   and **both** = import the definitions and the data. The default is
   **definitions**.

   If you attempt to import objects into an existing database, the result
   depends on the import format. If the format is **definitions** or **both**,
   an error occurs unless :option:`--drop-first` is given. If the format is
   **data**, imported table data is added to existing table data.
   
.. option:: --new-storage-engine=<new_engine>

   The engine to use for all tables created on the destination server.

.. option::  --no-headers, -h

   Input does not contain column headers. This option applies only for
   **csv** and **tab** output.

.. option:: --quiet, -q

   Turn off all messages for quiet execution.

.. option:: --server=<server>

   Connection information for the server in
   <*user*>[:<*passwd*>]@<*host*>[:<*port*>][:<*socket*>] format.

.. option:: --skip=<skip_objects>

   Specify objects to skip in the operation as a comma-separated list
   (no spaces). Permitted values are **CREATE_DB**, **DATA**, **EVENTS**,
   **FUNCTIONS**, **GRANTS**, **PROCEDURES**, **TABLES**, **TRIGGERS**,
   and **VIEWS**.

.. option:: --skip-blobs

   Do not import ``BLOB`` data.

.. option:: --skip-rpl

   Do not execute replication commands.

.. option:: --verbose, -v

   Specify how much information to display. Use this option
   multiple times to increase the amount of information.  For example,
   :option:`-v` = verbose, :option:`-vv` = more verbose, :option:`-vvv` =
   debug.

.. option:: --version

   Display version information and exit.

.. _`mysqldbimport-notes`:

NOTES
-----

The login user must have the appropriate permissions to create new
objects, access (read) the ``mysql`` database, and grant privileges.
If a database to be imported already exists, the user must have read
permission for it, which is needed to check the existence of objects in the
database.

Actual privileges needed may differ from installation to installation
depending on the security privileges present and whether the database
contains certain objects such as views or events and whether binary
logging is enabled.

Some combinations of the options may result in errors during the
operation.  For example, excluding tables but not views may result
in an error when a view is imported.

The :option:`--new-storage-engine` and :option:`--default-storage-engine`
options apply to all destination tables in the operation.

For the :option:`--format` and :option:`--import` options, the permitted
values are not case sensitive. In addition, values may be specified as any
unambiguous prefix of a valid value.  For example, :option:`--format=g`
specifies the grid format. An error occurs if a prefix matches more
than one valid value.

EXAMPLES
--------

To import the metadata from the ``util_test`` database to the server
on the local host using a file in CSV format, use this command::

    $ mysqldbimport --server=root@localhost --import=definitions \
      --format=csv data.csv
    # Source on localhost: ... connected.
    # Importing definitions from data.csv.
    #...done.

Similarly, to import the data from the ``util_test`` database to the server
on the local host,
importing the data using bulk insert statements, use this command::

    $ mysqldbimport --server=root@localhost --import=data \
      --bulk-insert --format=csv data.csv
    # Source on localhost: ... connected.
    # Importing data from data.csv.
    #...done.

To import both data and definitions from the ``util_test`` database,
importing the data using bulk insert statements from a file that
contains SQL statements, use this command::

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
