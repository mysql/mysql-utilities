.. _`mysqluserclone`:

########################################################################
``mysqluserclone`` - Create new users using an existing user as template
########################################################################


SYNOPSIS
--------

::

  mysqluserclone --source=<user>[<passwd>]@<host>:[<port>][:<socket>]
                 --destination=<user>[<passwd>]@<host>:[<port>][:<socket>]
                 [[--help | --version] | [ --dump  | --verbose | --force |
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

.. option:: -d, --dump

   dump GRANT statements for user

.. option:: -f, --force

   drop the new user if it exists

.. option:: -v, --verbose

   display additional information during operation

.. option:: --silent

   do not display feedback information during operation

.. option:: --include-global-privileges

    include privileges that match ``base_user@%`` as well as
    ``base_user@host``


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
