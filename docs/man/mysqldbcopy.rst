.. _`mysqldbcopy`:

#######################################################
``mysqldbcopy`` - Copy database objects between servers
#######################################################

SYNOPSIS
--------

::

 mysqldbcopy --source=<user>[<passwd>]@<host>:[<port>][:<socket>]
             --destination=<user>[<passwd>]@<host>:[<port>][:<socket>]
             (<db_name>[:<new_name>])+ [--verbose | --quiet |
             --skip=(TABLES,TRIGGERS,VIEWS,PROCEDURES,FUNCTIONS,
             EVENTS,GRANTS,DATA,CREATE_DB)* | --help | --version |
             --threads=<num threads>] | --exclude=<name>[|,--exclude=<name>]

DESCRIPTION
-----------

This utility permits a database administrator to copy a database from
one server (source) either to another server (destinaton) as the same
name or a different name or to the same server (destination) as the same or
as a different name (e.g. clone).

The operation copies all objects (tables, views, triggers, events, procedures,
functions, and database-level grants) to the destination server. The utility
will also copy all data. There are options to turn off copying any or all of
the objects as well as not copying the data.

You can exclude specific objects by name using the --exclude option whereby you
specify a name in the form of <db>.<object> or you can supply a regex search
pattern. For example, --exclude=db1.trig1 will exclude the single trigger and
--exlude=trig_ will exclude all objects from all databases whose name begins
with trig and has a following character or digit.

You must provide login information (e.g., user, host, password, etc.
for a user that has the appropriate rights to access all objects in
the operation. See :ref:`mysqldb-notes` below for more details.

OPTIONS
-------

The following command line options are accepted by **mysqldbcopy**:

.. option:: --version

   show version number and exit

.. option:: --help

   show the help page

.. option:: --source <source>

   connection information for source server in the form:
   <user>:<password>@<host>:<port>:<socket> where <password> is
   optional and either <port> or <socket> must be provided.

.. option:: --destination <destination>

   connection information for destination server in the form:
   <user>:<password>@<host>:<port>:<socket> Where <password> is
   optional and either <port> or <socket> must be provided.

.. option:: --copy-dir <copy directory>

   a path to use when copying data (stores temporary files) - default
   = current directory

.. option:: --skip <objects>

   specify objects to skip in the operation in the form of a
   comma-separated list (no spaces). Valid values = TABLES, VIEWS,
   TRIGGERS, PROCEDURES, FUNCTIONS, EVENTS, GRANTS, DATA, CREATE_DB

.. option:: -e EXCLUDE, --exclude=EXCLUDE

   exclude one or more objects from the operation using either a specific name
   (e.g. db1.t1) or a REGEXP search pattern. Repeat option for multiple
   exclusions.

.. option:: -f, --force

   drop the new database or object if it exists

.. option:: -q, --quiet

   turn off all messages for quiet execution

.. option:: -v, --verbose

   control how much information is displayed. e.g., -v =
   verbose, -vv = more verbose, -vvv = debug

.. option:: --threads

    use multiple threads for cross-server copy (default = 1)

.. _mysqldbcopy-notes:

NOTES
-----

The login user must have the appropriate permissions to create new
objects, read the old database, access (read) the mysql database, and
grant privileges.

To copy all objects from a source, the user must have **SELECT** and
**SHOW VIEW** privileges on the database as well as **SELECT** on the
mysql database.

To copy all objects to a destination, the user must have **CREATE**
for the database as well as **SUPER** for procedures and functions
(when binary logging is enabled) and **WITH GRANT OPTION** to copy
grants.

Actual privileges needed may differ from installation to installation
depending on the security privileges present and whether the database
contains certain objects (e.g. views, events) and whether binary
logging is turned on (i.e. the need for **SUPER**).

Some combinations of the options may result in errors during the
operation.  For example, eliminating tables but not views may result
in an error when the view is copied.

The --exclude option does not apply to grants.

EXAMPLES
--------

The following example demonstrates how to use the utility to copy a database
named 'util_test' to a new name 'util_test_copy' on the same server.::

    $ python mysqldbcopy.py \\
      --source=root:pass@localhost:3310:/test123/mysql.sock \\
      --destination=root:pass@localhost:3310:/test123/mysql.sock \\
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
