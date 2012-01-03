.. _`mysqluserclone`:

#####################################################################
``mysqluserclone`` - Create New Users Using Existing User as Template
#####################################################################


SYNOPSIS
--------

::

  mysqluserclone --source=<user>[<passwd>]@<host>:[<port>][:<socket>]
                 --destination=<user>[<passwd>]@<host>:[<port>][:<socket>]
                 [[--help | --version | --list | --format=<format>] |
                 [ --dump  | --verbose | --force | --quiet |
                 --include-global-privileges ] <base_user>
                 <new_user>[:<password>] [,<new_user>[:<password>]]]

DESCRIPTION
-----------

This utility permits a database administrator to use an existing user
account on one server as a template, clone a MySQL user such that one
or more new user accounts are created on another (or the same) server
with the same privileges as the original user.

You must provide connection parameters such as user, host, password,
and so forth, for a user that has the appropriate rights to access
all objects in the operation.
See :ref:`mysqluserclone-notes` for more details.

You can also use the utility to list users for a server by specifying the
--list option. This prints a list of the users on the source (no destination is
needed). You can also control the output of the list using the
:option:`--format` option.

OPTIONS
-------

**mysqluserclone** accepts the following command-line options:

.. option:: --help

   Display a help message and exit.

.. option:: --copy-dir=<directory>

   Path to use when copying data (stores temporary files) - default =
   current directory.

.. option:: --destination=<destination>

   Connection information for the destination server in the format:
   <user>:<password>@<host>:<port>:<socket> where <password> is
   optional and either <port> or <socket> must be provided.

.. option:: --dump, -d 

   Dump GRANT statements for user.

.. option::  --format=<list_format>

   Display the list of users in either GRID (default), TAB, CSV, or VERTICAL
   format - valid only for :option:`--list` option.

.. option:: --force, -f

   Drop the new user if it exists.

.. option:: --include-global-privileges

   Include privileges that match ``base_user@%`` as well as ``base_user@host``.

.. option:: --list

   List all users on the source - does not require a destination.

.. option:: --quiet, -q

   Turn off all messages for quiet execution.

.. option:: --source=<source>

   Connection information for the source server in the format:
   <user>:<password>@<host>:<port>:<socket> where <password> is
   optional and either <port> or <socket> must be provided.

.. option:: --verbose, -v

   Control how much information is displayed. This option can be used
   multiple times to increase the amount of information.  For example, -v =
   verbose, -vv = more verbose, -vvv = debug.

.. option:: --version

   Display version information and exit.

.. _mysqluserclone-notes:

NOTES
-----

The login user must have the appropriate permissions to create new
users, access (read) the mysql database, and grant privileges. At a
minimum, this requires the login user to have read privileges on the mysql
database, the **GRANT OPTION** privilege for all databases listed in the
**GRANT** statements found, and the ability to create a user account.

EXAMPLES
--------

To clone 'joe' as 'sam' and 'sally' with passwords and logging in as root on
the local machine, use this command::

    $ mysqluserclone --source=root@localhost \
      --destination=root@localhost \
      joe@localhost sam:secret1@localhost sally:secret2@localhost
    # Source on localhost: ... connected.
    # Destination on localhost: ... connected.
    # Cloning 2 users...
    # Cloning joe@localhost to user sam:secret1@localhost
    # Cloning joe@localhost to user sally:secret2@localhost
    # ...done.

The following shows all of the users on the localhost server in the most
verbose output in CSV format::

    $ mysqluserclone --source=root@localhost --list --format=CSV -vvv
    # Source on localhost: ... connected.
    user,host,database
    joe,localhost,util_test
    rpl,localhost,
    sally,localhost,util_test
    sam,localhost,util_test
    joe,user,util_test

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
