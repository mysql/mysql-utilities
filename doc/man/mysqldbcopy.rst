.. _`mysqldbcopy`:

#######################################################
``mysqldbcopy`` - Copy Database Objects Between Servers
#######################################################

SYNOPSIS
--------

::

 mysqldbcopy --source=<user>[:<passwd>]@<host>[:<port>][:<socket>]
             --destination=<user>[:<passwd>]@<host>[:<port>][:<socket>]
             (<db_name>[:<new_name>])+ [--verbose | --quiet |
             --skip=(TABLES,TRIGGERS,VIEWS,PROCEDURES,FUNCTIONS,
             EVENTS,GRANTS,DATA,CREATE_DB)* | --help | --version |
             --new-storage-engine=<engine> | --default-storage-engine=<engine> |
             --threads=<num threads>] | --exclude=<name>[|,--exclude=<name>]

DESCRIPTION
-----------

This utility permits a database administrator to copy a database from
one server (source) either to another server (destinaton) as the same
name or a different name or to the same server (destination) as the same or
as a different name (clone).

The operation copies all objects (tables, views, triggers, events, procedures,
functions, and database-level grants) to the destination server. The utility
also copies all data. There are options to turn off copying any or all of
the objects as well as not copying the data.

You can exclude specific objects by name using the :option:`--exclude` option
whereby you specify a name in the form of <db>.<object> or you can supply a
regex search pattern. For example, :option:`--exclude=db1.trig1` excludes
the single trigger and :option:`--exclude=trig_` excludes all objects from
all databases whose name begins with trig and has a following character or
digit.

To change the storage engine for all tables on the destination, specify the
new engine with the :option:`--new-storage-engine` option. If the destination
server supports the new engine, all tables will use that engine.

Similarly, you can specify a different default storage engine with
the :option:`--default-storage-engine` option. If the destination
server supports the engine, any table that specifies a storage
engine that the server does not support will use the new default
engine. Note that this overrides the default storage engine mechanism
on the server.

If the :option:`--default-storage-engine` or :option:`--new-storage-engine`
option is given and the destination server does not support the
specified storage engine, a warning is issued and the default storage
engine setting on the server is used instead.

The operation uses a consistent snapshot by default to read from the
database(s) selected. You can change the locking mode by using the
:option:`--locking` option. You can turn off locking altogether ('no-locks') or
use only table locks ('lock-all'). The default value is 'snapshot'.
Additionally, WRITE locks are used to lock the destination tables during the
copy.

You must provide connection parameters (user, host, password, and
so forth) for an account that has the appropriate privileges to
access all objects in the operation.
For details, see :ref:`mysqldbcopy-notes`.

OPTIONS
-------

**mysqldbcopy** accepts the following command-line options:

.. option:: --help

   Display a help message and exit.

.. option:: --copy-dir=<copy_directory>

   Path to use when copying data (stores temporary files). Default
   = current directory.

.. option:: --default-storage-engine=<def_engine>

   Change all tables to use this storage engine if the destination server
   does not support the original storage engine.

.. option:: --destination=<destination>

   Connection information for the destination server in the format:
   <user>[:<passwd>]@<host>[:<port>][:<socket>]
   where <passwd> is
   optional and either <port> or <socket> must be provided.

.. option:: --exclude=<exclude>, -x<exclude>

   Exclude one or more objects from the operation using either a specific name
   such as db1.t1 or a search pattern.  Use this option multiple times
   to specify multiple exclusions. By default, patterns use LIKE matching.
   With the :option:`--regexp` option, patterns use REGEXP matching.

.. option:: --force, -f

   Drop the new database or object if it exists.
   
.. option:: --locking=<locking>

   Choose the lock type for the operation: no-locks = do not use any table
   locks, lock-all = use table locks but no transaction and no consistent read,
   snaphot (default): consistent read using a single transaction.

.. option::  --new-storage-engine=<new_engine>

   Change all tables to use this storage engine if the destiation server
   supports the storage engine.

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

    Use multiple threads for cross-server copy (default = 1).

.. option:: --verbose, -v

   Specify how much information to display. Use this option
   multiple times to increase the amount of information.  For example, -v =
   verbose, -vv = more verbose, -vvv = debug.

.. option:: --version

   Display version information and exit.


.. _mysqldbcopy-notes:

NOTES
-----

The login user must have the appropriate permissions to create new
objects, read the old database, access (read) the mysql database, and
grant privileges.

To copy all objects from a source, the user must have the **SELECT** and
**SHOW VIEW** privileges on the database as well as the **SELECT** privilege
on the mysql database.

To copy all objects to a destination, the user must have these privileges:
**CREATE** for the database, **SUPER** for procedures and functions
(when binary logging is enabled), and **GRANT OPTION** to copy
grants.

Actual privileges needed may differ from installation to installation
depending on the security privileges present and whether the database
contains certain objects such as views or events and whether binary
logging is turned on (hence the need for the **SUPER** privilege).

The :option:`--new-storage-engine` and :option:`--default-storage-engine`
options apply to all tables in the operation.

Some option combinations may result in errors during the
operation.  For example, eliminating tables but not views may result
in an error when the view is copied.

The :option:`--exclude` option does not apply to grants.

EXAMPLES
--------

The following example demonstrates how to use the utility to copy a database
named 'util_test' to a new name 'util_test_copy' on the same server::

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
want to ensure data integrity of the copy by locking the tables during the
read step, add a :option:`--locking=lock-all` option to the command::

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
