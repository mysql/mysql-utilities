================
 mysqlreplicate
================

--------------------------------------
start replication with a master server
--------------------------------------

:Author: The Oracle MySQL Utilities team
:Date: 2010-09-09
:Copyright: GPL
:Version: 1.0.0
:Manual group: database 

SYNOPSIS
========

::

  mysqlreplicate --master=<user>[<passwd>]@<host>:[<port>][:<socket>]
                 --slave=<user>[<passwd>]@<host>:[<port>][:<socket>]
                 [[--help | --version] | 
                 [--verbose | --testdb=<test database>]
                 --rpl_user=<uid:passwd>]

DESCRIPTION
===========

This document describes the mysqlreplicate utility. This utility
permits an administrator to start replication among two servers. The user
provides login information to the slave and provides connection information
for connecting to the master. 

For example, to setup replication between a MySQL instance on two different
hosts using the default settings, use this command:

::

  mysqlreplicate --master=root@localhost:3306 --slave=root@localhost:3307
                 --rpl-user=rpl:rpl

You can also specify a database to be used to test replication as well as
a unix socket file for connecting to a master running on a local host.

OPTIONS
=======

--version             show version number and exit

--help                show help page

--master=MASTER       connection information for master server in the form:
                      <user>:<password>@<host>:<port>:<socket>

--slave=SLAVE         connection information for slave server in the form:
                      <user>:<password>@<host>:<port>:<socket>

--rpl-user=RPL_USER   the user and password for the replication user
                      requirement - e.g. rpl:passwd - default = rpl:rpl

--test-db=TEST_DB     database name to use in testing  replication setup
                      (optional)

-v, --verbose         display additional information during operation


FILES
=====

- ``mysqlreplicate.py``  the utility script
- ``mysql``              the MySQL utilities library


NOTES
=====

The login user must have the appropriate permissions to grant access to all
databases and the ability to create a user account.

The server_id on the master and slave must be unique. The utility will report
an error if the server_id is 0 or is the same on the master and slave. Set
these values before starting this utility.

