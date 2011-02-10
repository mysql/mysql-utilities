.. _`mysqlserverclone`:

########################################################################
``mysqlserverclone`` - Cloning an existing server to create a new server
########################################################################

SYNOPSIS
--------

::

 mysqlserverclone  [[ --help | --version] | --quiet |
                   --server=<user>[<passwd>]@<host>:[<port>][:<socket>]
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

.. option:: --version

   show version number and exit

.. option:: --help, -h

   show the help page

.. option:: --server <source>

   connection information for source server in the form:
   <user>:<password>@<host>:<port>:<socket>

.. option:: --verbose, -v

   control how much information is displayed. For example, -v =
   verbose, -vv = more verbose, -vvv = debug

.. option:: --quiet, -q

   turn off all messages for quiet execution

.. option:: --new-data <path to new datadir>

   the full path to the location of the data directory for the new
   instance

.. option:: --new-port <port>

   the new port for the new instance - default=3307

.. option:: --new-id <server_id>

   the server_id for the new instance - default=2

.. option:: --root-password <password>

   password for the root user

.. option:: --mysqld <options>

   additional options for mysqld

NOTES
-----

The login user must have the appropriate permissions to grant access
to all databases and the ability to create a user account.

EXAMPLES
--------

The following demonstrates how to create a new instance of a running server
and setting the root password and turning binary logging on.::

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
