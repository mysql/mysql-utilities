.. _`mysqlreplicate`:

####################################################################
``mysqlreplicate`` - Setup and start replication between two servers
####################################################################

SYNOPSIS
--------

::

  mysqlreplicate --master=<user>[<passwd>]@<host>:[<port>][:<socket>]
                 --slave=<user>[<passwd>]@<host>:[<port>][:<socket>]
                 [[--help | --version] | 
                 [--verbose | --testdb=<test database>]
                 --rpl_user=<uid:passwd>]

DESCRIPTION
-----------

This utility permits an administrator to start replication among two
servers. The user provides login information to the slave and provides
connection information for connecting to the master.

For example, to setup replication between a MySQL instance on two different
hosts using the default settings, use this command::

  mysqlreplicate --master=root@localhost:3306 --slave=root@localhost:3307
                 --rpl-user=rpl:rpl

You can also specify a database to be used to test replication as well as
a unix socket file for connecting to a master running on a local host.

OPTIONS
-------

.. option:: --version 

   show version number and exit

.. option:: --help 

   show help page

.. option:: --master <master>

   connection information for master server in the form:
   <user>:<password>@<host>:<port>:<socket>

.. option:: --slave <slave>

   connection information for slave server in the form:
   <user>:<password>@<host>:<port>:<socket>

.. option:: --rpl-user <replication-user> 

   the user and password for the replication user requirement -
   e.g. rpl:passwd - default = rpl:rpl

.. option:: --test-db <test database>

   database name to use in testing replication setup (optional)

.. option:: -v, --verbose

   control how much information is displayed. e.g., -v =
   verbose, -vv = more verbose, -vvv = debug


NOTES
-----

The login user must have the appropriate permissions to grant access to all
databases and the ability to create a user account.

The server ID on the master and slave must be unique. The utility will
report an error if the server ID is 0 or is the same on the master and
slave. Set these values before starting this utility.

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
