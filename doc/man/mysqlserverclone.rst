.. _`mysqlserverclone`:

#################################################################
``mysqlserverclone`` - Clone Existing Server to Create New Server
#################################################################

SYNOPSIS
--------

::

 mysqlserverclone [options]

DESCRIPTION
-----------

This utility permits an administrator to clone an existing MySQL server
instance to start a new server instance
on the same host.  The utility creates a new datadir (:option:`--new-data`),
and starts the server with a socket file. You can optionally add a
password for the login user account on the new instance.

OPTIONS
-------

:command:`mysqlserverclone` accepts the following command-line options:

.. option:: --help

   Display a help message and exit.

.. option:: --mysqld=<options>

   Additional options for :command:`mysqld`. To specify multiple options,
   separate them by spaces. Use appropriate quoting as necessary. For example,
   to specify ``--log-bin=binlog`` and ``--general-log-file="my log file"``,
   use::

   --mysqld="--log-bin=binlog --general-log-file='my log file'"

.. option:: --new-data=<path_to_new_datadir>

   The full path name of the location of the data directory for the new
   server instance. If the directory does not exist, the utility will create
   it.

.. option:: --new-id=<server_id>

   The ``server_id`` value for the new server instance. The default is 2.

.. option:: --new-port=<port>

   The port number for the new server instance. The default is 3307.

.. option:: --quiet, -q

   Turn off all messages for quiet execution.

.. option:: --root-password=<password>

   The password for the ``root`` user of the new server instance.

.. option:: --server=<source>

   Connection information for the server to be cloned in
   <*user*>[:<*passwd*>]@<*host*>[:<*port*>][:<*socket*>] format.

.. option:: --verbose, -v

   Specify how much information to display. Use this option
   multiple times to increase the amount of information.  For example,
   :option:`-v` = verbose, :option:`-vv` = more verbose, :option:`-vvv` =
   debug.

.. option:: --version

   Display version information and exit.

.. option:: --write-command=<file_name>, -w<file_name>

   Path name of file in which to write the command used to launch the new
   server instance.


EXAMPLES
--------

The following command demonstrates how to create a new instance of a running
server, set the ``root`` user password and enable binary logging::

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
