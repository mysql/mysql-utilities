================
 mysqluserclone
================

---------------------------------------------------
clone a MySQL user account to one or more new users
---------------------------------------------------

:Author: The Oracle MySQL Utilities team
:Date: 2010-09-09
:Copyright: GPL
:Version: 1.0.0
:Manual group: database 

SYNOPSIS
========

::

  mysqluserclone --source=<user>[<passwd>]@<host>:[<port>][:<socket>]
                 --destination=<user>[<passwd>]@<host>:[<port>][:<socket>]
                 [[--help | --version] | [ --dump  | --verbose | --force ]
                 <base_user> <new_user> [ :<password>]
                 [ ,<new_user> [ :<password>]]]

DESCRIPTION
===========

This document describes the ''mysqluserclone'' utility. This utility
permits a database administrator to use an existing user account on one
server as a template, clone a MySQL user such that one or more new user
accounts are created on another (or the same) server with the same
privileges as the original user.

For example, to clone 'joe' as 'sam' and 'sally' with passwords and logging in
as root on the local machine, use this command:

::

  mysqluserclone --source=root@localhost:3306 joe@localhost \\
                 sam:secret1@somehost, sally:secret2@localhost

You must provide login information (e.g., user, host, password, etc.
for a user that has the appropriate rights to access all objects
in the operation. 

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

-d, --dump            dump GRANT statements for user

-f, --force           drop the new user if it exists

-v, --verbose         display additional information during operation

--silent              do not display feedback information during operation

--include-globals     include privileges that match base_user@% as well as
                      base_user@host


FILES
=====

- ''mysqlusercopy.py''  the utility script
- ''mysql''             the MySQL utilities library

NOTES
=====

The login user must have the appropriate permissions to create new users,
access (read) the mysql database, and grant privileges. At a minimum, this
requires the login user to have read on the mysql database, the
''WITH GRANT OPTION'' for all databases listed in the ''GRANT'' statements
found, and the ability to create a user account.
