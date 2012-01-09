.. _`mysqlserverclone`:

#################################################################
``mysqlserverclone`` - Clone Existing Server to Create New Server
#################################################################

SYNOPSIS
--------

::

 mysqlserverclone [[ --help | --version] | --quiet |
                  --server=<user>[:<passwd>]@<host>[:<port>][:<socket>]
                  [ --new-data=<datadir> | --new-port=<port> |
                  --new-id=<server_id> ] | --root-password=<passwd> ]

DESCRIPTION
-----------

This utility permits an administrator to start a new instance of a
running server.  The utility will create a new datadir (--new-data),
and start the server with a socket file. You can optionally add a
password for the login user account on the new instance.

OPTIONS
-------

:command:`mysqlserverclone` accepts the following command-line options:

.. option:: --help, -h

   Display a help message and exit.

.. option:: --mysqld=<options>

   Additional options for mysqld.

.. option:: --new-data=<path_to_new_datadir>

   The full path to the location of the data directory for the new
   instance.

.. option:: --new-id=<server_id>

   The server_id for the new instance - default=2.

.. option:: --new-port=<port>

   The new port for the new instance - default=3307.

.. option:: --quiet, -q

   Turn off all messages for quiet execution.

.. option:: --root-password=<password>

   Password for the root user.

.. option:: --server=<source>

   Connection information for the source server in the format:
   <user>[:<passwd>]@<host>[:<port>][:<socket>]

.. option:: --verbose, -v

   Specify how much information to display. Use this option
   multiple times to increase the amount of information.  For example, -v =
   verbose, -vv = more verbose, -vvv = debug.

.. option:: --version

   Display version information and exit.

NOTES
-----

The login user must have the appropriate permissions to grant access
to all databases and the ability to create a user account.

EXAMPLES
--------

The following demonstrates how to create a new instance of a running server
and setting the root password and turning binary logging on::

    $ mkdir /source/test123
    $ mysqlserverclone --server=root:pass@localhost \
      --new-data=/Users/cbell/source/test123 --new-port=3310 \
      --root-password=pass --mysqld=--log-bin=mysql-bin
    # Cloning the MySQL server running on localhost.
    # Creating new data directory...
    # Configuring new instance...
    # Locating mysql tools...
    # Setting up empty database and mysql tables...
    # Starting new instance of the server...
    # Testing connection to new instance...
    # Success!
    # Setting the root password...
    # ...done.

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
