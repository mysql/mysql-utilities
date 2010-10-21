=============
 mysqldbcopy
=============

------------------------------------
copy MySQL databases and all objects
------------------------------------

:Author: The Oracle MySQL Utilities team
:Date: 2010-08-27
:Copyright: GPL
:Version: 1.0.0
:Manual group: database 

SYNOPSIS
========

::

 mysqldbcopy --source=<user>[<passwd>]@<host>:[<port>][:<socket>]
             --destination=<user>[<passwd>]@<host>:[<port>][:<socket>]
             (<db_name>[:<new_name>])+ [--verbose | --overwrite |
             --skip=(TABLES,TRIGGERS,VIEWS,PROCEDURES,FUNCTIONS,
             EVENTS,GRANTS,DATA,CREATE_DB)* | --help | --version]

DESCRIPTION
===========

This document describes the ''mysqldbcopy'' utility. This utility
permits a database administrator to copy a database from one server (source)
either to another server (destinaton) as the same name or a different name or
to the same server (destination) as a different name (e.g. clone).

The operation copies all objects (tables, views, triggers, events, procedures,
functions, and database-level grants) to the destination server. The utility
will also copy all data. There are options to turn off copying any or all of
the objects as well as not copying the data. 

For example, to copy the database 'dev' from server1 on port 3306 to
server2 via a socket connection renaming the database to 'dev_test', use this
command:

::

  mysqldbcopy --source=root@server1:3306 dev:dev_test \
              --destination=root@server2::/mysql.sock

You must provide login information (e.g., user, host, password, etc.
for a user that has the appropriate rights to access all objects
in the operation. See **notes** below for more details.

OPTIONS
=======

--version             show version number and exit

--help                show the help page       

--source=SOURCE       connection information for source server in the form:
                      <user>:<password>@<host>:<port>:<socket>
                      Where <password> is optional and either <port> or
                      <socket> must be provided.

--destination=DEST    connection information for destination server in the
                      form: <user>:<password>@<host>:<port>:<socket>
                      Where <password> is optional and either <port> or
                      <socket> must be provided.

--copy-dir=COPY_DIR   a path to use when copying data (stores temporary
                      files) - default = current directory

--skip=SKIP_OBJECTS   specify objects to skip in the operation in the form
                      of a comma-separated list (no spaces). Valid values =
                      TABLES, VIEWS, TRIGGERS, PROCEDURES, FUNCTIONS,
                      EVENTS, GRANTS, DATA, CREATE_DB

-o, --overwrite       drop the new database or object if it exists

-v, --verbose         display additional information during operation

--silent              do not display feedback/progress information
                      (errors are still displayed)

FILES
=====

- ''mysqldbcopy.py''    the utility script
- ''mysql''             the MySQL utilities library

NOTES
=====

The login user must have the appropriate permissions to create new objects,
read the old database, access (read) the mysql database, and grant privileges. 

To copy all objects from a source, the user must have ''SELECT'' and
''SHOW VIEW'' privileges on the database as well as ''SELECT'' on the mysql
database.

To copy all objects to a destination, the user must have ''CREATE'' for the
database as well as ''SUPER'' for procedures and functions (when binary logging
is enabled) and ''WITH GRANT OPTION'' to copy grants.

Actual privileges needed may differ from installation to installation
depending on the security privileges present and whether the database contains
certain objects (e.g. views, events) and whether binary logging is turned
on (i.e. the need for ''SUPER'').

NOTICE
======

Some combinations of the options may result in errors during the operation.
For example, eliminating tables but not views may result in an error when the
view is copied.

