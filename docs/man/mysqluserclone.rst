.. _`mysqluserclone`:

########################################################################
``mysqluserclone`` - Create new users using an existing user as template
########################################################################


SYNOPSIS
--------

::

  mysqluserclone --source=<user>[<passwd>]@<host>:[<port>][:<socket>]
                 --destination=<user>[<passwd>]@<host>:[<port>][:<socket>]
                 [[--help | --version | --list | --format=<format>] |
                 [ --dump  | --verbose | --force |
                 --include-global-privileges ] <base_user>
                 <new_user>[:<password>] [,<new_user>[:<password>]]]

DESCRIPTION
-----------

This utility permits a database administrator to use an existing user
account on one server as a template, clone a MySQL user such that one
or more new user accounts are created on another (or the same) server
with the same privileges as the original user.

For example, to clone 'joe' as 'sam' and 'sally' with passwords and logging in
as root on the local machine, use this command::

  mysqluserclone --source=root@localhost:3306 joe@localhost \\
                 sam:secret1@somehost, sally:secret2@localhost

You must provide login information (e.g., user, host, password, etc.
for a user that has the appropriate rights to access all objects
in the operation.

You can also use the utility to list users for a server by specifying the
--list option. This prints a list of the users on the source (no destination
is needed). You can also control the output of the list using the --format
option. For example, the following shows all of the users on the localhost
server in the most verbose output in a TAB format.

  mysqluserclone --source=root@localhost --list --format=TAB

OPTIONS
-------

.. option:: --version

   show version number and exit

.. option:: --help

   show the help page

.. option:: --source <source>

   connection information for source server in the form:
   <user>:<password>@<host>:<port>:<socket> where <password> is
   optional and either <port> or <socket> must be provided.

.. option:: --destination <destinatio>

   connection information for destination server in the form:
   <user>:<password>@<host>:<port>:<socket> Where <password> is
   optional and either <port> or <socket> must be provided.

.. option:: --copy-dir <directory>

   Path to use when copying data (stores temporary files) - default =
   current directory

.. option:: -d, --dump - does not require a destination

   dump GRANT statements for user

.. option:: -f, --force

   drop the new user if it exists

.. option:: --silent

   turn off all messages for silent execution

.. option:: -v, --verbose

   control how much information is displayed. e.g., -v =
   verbose, -vv = more verbose, -vvv = debug

.. option:: --include-global-privileges

   include privileges that match ``base_user@%`` as well as ``base_user@host``

.. option:: --list

   list all users on the source - does not require a destination

.. option::  --format=LIST_FORMAT

   display the list of users in either GRID (default), TAB, CSV, or VERTICAL
   format - valid only for --list option


NOTES
-----

The login user must have the appropriate permissions to create new
users, access (read) the mysql database, and grant privileges. At a
minimum, this requires the login user to have read on the mysql
database, the **WITH GRANT OPTION** for all databases listed in the
**GRANT** statements found, and the ability to create a user account.

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
