.. _`mysqldbcopy`:

#######################################################
``mysqldbcopy`` - Copy database objects between servers
#######################################################

SYNOPSIS
--------

::

 mysqldbcopy --source=<user>[<passwd>]@<host>:[<port>][:<socket>]
             --destination=<user>[<passwd>]@<host>:[<port>][:<socket>]
             (<db_name>[:<new_name>])+ [--verbose | --overwrite |
             --skip=(TABLES,TRIGGERS,VIEWS,PROCEDURES,FUNCTIONS,
             EVENTS,GRANTS,DATA,CREATE_DB)* | --help | --version]

DESCRIPTION
-----------

This utility permits a database administrator to copy a database from
one server (source) either to another server (destinaton) as the same
name or a different name or to the same server (destination) as a
different name (e.g. clone).

The operation copies all objects (tables, views, triggers, events, procedures,
functions, and database-level grants) to the destination server. The utility
will also copy all data. There are options to turn off copying any or all of
the objects as well as not copying the data. 

For example, to copy the database 'dev' from server1 on port 3306 to
server2 via a socket connection renaming the database to 'dev_test',
use this command::

  mysqldbcopy --source=root@server1:3306 dev:dev_test \
              --destination=root@server2::/mysql.sock

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

.. option:: -o, --overwrite

   drop the new database or object if it exists

.. option:: -v, --verbose

   display additional information during operation

.. option:: --silent

   do not display feedback/progress information (errors are still
   displayed)


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

NOTICE
------

Some combinations of the options may result in errors during the
operation.  For example, eliminating tables but not views may result
in an error when the view is copied.

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
