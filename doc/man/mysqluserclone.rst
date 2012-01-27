.. _`mysqluserclone`:

###########################################################
``mysqluserclone`` - Clone Existing User to Create New User
###########################################################


SYNOPSIS
--------

::

 mysqluserclone [options] base_user new_user[:password][@host_name] ...

DESCRIPTION
-----------

This utility uses an existing MySQL user account on one server as a
template, and clones it to create one or more new user accounts with the
same privileges as the original user.  The new users can be created on the
original server or a different server.

To list users for a server, specify the :option:`--list` option.  This
prints a list of the users on the source (no destination is needed). To
control how to display list output, use one of the following values with the
:option:`--format` option:

**grid** (default)
  Display output in grid or table format like that of the
  :command:`mysql` monitor.

**csv**
  Display output in comma-separated values format.

**tab**
  Display output in tab-separated format.

**vertical**
  Display output in single-column format like that of the ``\G`` command
  for the :command:`mysql` monitor.

OPTIONS
-------

:command:`mysqluserclone` accepts the following command-line options:

.. option:: --help

   Display a help message and exit.

.. option:: --destination=<destination>

   Connection information for the destination server in
   <*user*>[:<*passwd*>]@<*host*>[:<*port*>][:<*socket*>] format.

.. option:: --dump, -d 

   Display the **GRANT** statements to create the account rather than
   executing them. In this case, the utility does not connect to the
   destination server and no :option:`--destination` option is needed.

.. option::  --format=<list_format>, -f<list_format>

   Specify the user display format.  Permitted format values are **grid**,
   **csv**, **tab**, and **vertical**. The default is **grid**.
   This option is valid only if :option:`--list` is given.

.. option:: --force

   Drop the new user account if it exists before creating the new account.
   Without this option, it is an error to try to create an account that
   already exists.

.. option:: --include-global-privileges

   Include privileges that match ``base_user@%`` as well as ``base_user@host``.

.. option:: --list

   List all users on the source server. With this option, a destination server
   need not be specified.

.. option:: --quiet, -q

   Turn off all messages for quiet execution.

.. option:: --source=<source>

   Connection information for the source server in
   <*user*>[:<*passwd*>]@<*host*>[:<*port*>][:<*socket*>] format.

.. option:: --verbose, -v

   Specify how much information to display. Use this option
   multiple times to increase the amount of information.  For example,
   :option:`-v` = verbose, :option:`-vv` = more verbose, :option:`-vvv` =
   debug.

.. option:: --version

   Display version information and exit.

.. _mysqluserclone-notes:

NOTES
-----

You must provide connection parameters (user, host, password, and
so forth) for an account that has the appropriate privileges to
access all objects in the operation.

The account used to connect to the source server must have privileges to
read the **mysql** database.

The account used to connect to the destination server must have privileges to
execute **CREATE USER** (and **DROP USER** if the :option:`--force` option is
given), and privileges to execute **GRANT** for all privileges to be granted to
the new accounts.

For the :option:`--format` option, the permitted values are not case
sensitive. In addition, values may be specified as any unambiguous prefix of
a valid value.  For example, :option:`--format=g` specifies the grid format.
An error occurs if a prefix matches more than one valid value.

EXAMPLES
--------

To clone ``joe`` as ``sam`` and ``sally`` with passwords and logging in as
``root`` on the local machine, use this command::

    $ mysqluserclone --source=root@localhost \
      --destination=root@localhost \
      joe@localhost sam:secret1@localhost sally:secret2@localhost
    # Source on localhost: ... connected.
    # Destination on localhost: ... connected.
    # Cloning 2 users...
    # Cloning joe@localhost to user sam:secret1@localhost
    # Cloning joe@localhost to user sally:secret2@localhost
    # ...done.

The following command shows all users on the local server in the most
verbose output in CSV format::

    $ mysqluserclone --source=root@localhost --list --format=csv -vvv
    # Source on localhost: ... connected.
    user,host,database
    joe,localhost,util_test
    rpl,localhost,
    sally,localhost,util_test
    sam,localhost,util_test
    joe,user,util_test

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
