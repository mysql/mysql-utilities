.. _`mysqldbcopy`:

#######################################################
``mysqldbcopy`` - Copy Database Objects Between Servers
#######################################################

SYNOPSIS
--------

::

 mysqldbcopy [options] db_name[:new_db_name]

DESCRIPTION
-----------

This utility copies a database on a source server to a database on a
destination server. If the source and destination servers are different, the
database names can be the same or different. If the source and destination
servers are the same, the database names must be different.

The utility accepts one or more database pairs on the command line. To name a
database pair, use *db_name*:*new_db_name* syntax to specify the source and
destination names explicitly. If the source and destination database names are
the same, *db_name* can be used as shorthand for *db_name*:*db_name*.

By default, the operation copies all objects (tables, views, triggers,
events, procedures, functions, and database-level grants) and data to the
destination server.  There are options to turn off copying any or all of the
objects as well as not copying the data.

To exclude specific objects by name, use the :option:`--exclude` option with
a name in *db*.*obj* format, or you can supply a search pattern. For example,
:option:`--exclude=db1.trig1` excludes the single trigger and
:option:`--exclude=trig_` excludes all objects from all databases having a
name that begins with ``trig`` and has a following character.

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

By default, the operation uses a consistent snapshot to read the source
databases. To change the locking mode, use the :option:`--locking` option
with a locking type value.  Use a value of **no-locks** to turn off locking
altogether or **lock-all** to use only table locks. The default value is
**snapshot**. Additionally, the utility uses WRITE locks to lock the
destination tables during the copy.

OPTIONS
-------

:command:`mysqldbcopy` accepts the following command-line options:

.. option:: --help

   Display a help message and exit.

.. option:: --default-storage-engine=<def_engine>

   The engine to use for tables if the destination server does not support
   the original storage engine on the source server.

.. option:: --destination=<destination>

   Connection information for the destination server in the format:
   <user>[:<passwd>]@<host>[:<port>][:<socket>]
   where <passwd> is
   optional and either <port> or <socket> must be provided.

.. option:: --exclude=<exclude>, -x<exclude>

   Exclude one or more objects from the operation using either a specific name
   such as db1.t1 or a search pattern.  Use this option multiple times
   to specify multiple exclusions. By default, patterns use **LIKE** matching.
   With the :option:`--regexp` option, patterns use **REGEXP** matching.

   This option does not apply to grants.

.. option:: --force

   Drop each database to be copied if exists before copying anything into
   it. Without this option, an error occurs if you attempt to copy objects
   into an existing database.
   
.. option:: --locking=<locking>

   Choose the lock type for the operation. Permitted lock values are
   **no-locks** (do not use any table locks), **lock-all** (use table locks
   but no transaction and no consistent read), and **snaphot** (consistent
   read using a single transaction). The default is **snapshot**.

.. option::  --new-storage-engine=<new_engine>

   The engine to use for all tables created on the destination server.

.. option:: --quiet, -q

   Turn off all messages for quiet execution.

.. option:: --regexp, --basic-regexp, -G

   Perform pattern matches using the **REGEXP** operator. The default is
   to use **LIKE** for matching.

.. option:: --skip=<objects>

   Specify objects to skip in the operation as a comma-separated list
   (no spaces). Permitted values are CREATE_DB, DATA, EVENTS, FUNCTIONS,
   GRANTS, PROCEDURES, TABLES, TRIGGERS, and VIEWS.

.. option:: --source=<source>

   Connection information for the source server in the format:
   <user>[:<passwd>]@<host>[:<port>][:<socket>]
   where <passwd> is
   optional and either <port> or <socket> must be provided.

.. option:: --threads

    Use multiple threads for cross-server copy. The default is 1.

.. option:: --verbose, -v

   Specify how much information to display. Use this option
   multiple times to increase the amount of information.  For example, -v =
   verbose, -vv = more verbose, -vvv = debug.

.. option:: --version

   Display version information and exit.


.. _mysqldbcopy-notes:

NOTES
-----

You must provide connection parameters (user, host, password, and
so forth) for an account that has the appropriate privileges to
access all objects in the operation.

To copy all objects from a source, the user must have these privileges:
**SELECT** and **SHOW VIEW** for the database, and **SELECT** for the
``mysql`` database.

To copy all objects to a destination, the user must have these privileges:
**CREATE** for the database, **SUPER** (when binary logging is enabled) for
procedures and functions, and **GRANT OPTION** to copy grants.

Actual privileges required may differ from installation to installation
depending on the security privileges present and whether the database
contains certain objects such as views or events and whether binary
logging is enabled.

The :option:`--new-storage-engine` and :option:`--default-storage-engine`
options apply to all destination tables in the operation.

Some option combinations may result in errors during the
operation.  For example, eliminating tables but not views may result
in an error a the view is copied.

EXAMPLES
--------

The following example demonstrates how to use the utility to copy a database
named ``util_test`` to a new database named ``util_test_copy`` on the same
server::

    $ mysqldbcopy \
      --source=root:pass@localhost:3310:/test123/mysql.sock \
      --destination=root:pass@localhost:3310:/test123/mysql.sock \
      util_test:util_test_copy
    # Source on localhost: ... connected.
    # Destination on localhost: ... connected.
    # Copying database util_test renamed as util_test_copy
    # Copying TABLE util_test.t1
    # Copying table data.
    # Copying TABLE util_test.t2
    # Copying table data.
    # Copying TABLE util_test.t3
    # Copying table data.
    # Copying TABLE util_test.t4
    # Copying table data.
    # Copying VIEW util_test.v1
    # Copying TRIGGER util_test.trg
    # Copying PROCEDURE util_test.p1
    # Copying FUNCTION util_test.f1
    # Copying EVENT util_test.e1
    # Copying GRANTS from util_test
    #...done.
    
If the database to be copied does not contain only InnoDB tables and you
want to ensure data integrity of the copied data by locking the tables
during the read step, add a :option:`--locking=lock-all` option to the
command::

    $ mysqldbcopy \
      --source=root:pass@localhost:3310:/test123/mysql.sock \
      --destination=root:pass@localhost:3310:/test123/mysql.sock \
      util_test:util_test_copy --locking=lock-all
    # Source on localhost: ... connected.
    # Destination on localhost: ... connected.
    # Copying database util_test renamed as util_test_copy
    # Copying TABLE util_test.t1
    # Copying table data.
    # Copying TABLE util_test.t2
    # Copying table data.
    # Copying TABLE util_test.t3
    # Copying table data.
    # Copying TABLE util_test.t4
    # Copying table data.
    # Copying VIEW util_test.v1
    # Copying TRIGGER util_test.trg
    # Copying PROCEDURE util_test.p1
    # Copying FUNCTION util_test.f1
    # Copying EVENT util_test.e1
    # Copying GRANTS from util_test
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
