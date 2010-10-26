==================
 mysqlserverclone
==================

SYNOPSIS
========

::

 mysqlcloneserver  [[ --help | --version] | <login information>
                   [ --new-data=<datadir> | --new-port=<port> |
                     --new-id=<server_id> ] | --root-password=<passwd> ]

DESCRIPTION
===========

This document describes the ``mysqlcloneserver`` utility. This utility
permits an administrator to start a new instance of a running server.
The utility will create a new datadir (--new-data), and start the
server with a socket file. You can optionally add a password for the
login user account on the new instance.

For example, to create a new instance of a typical MySQL instances,
use this command:

::

 mysqlcloneserver --u root -p xxxx -h localhost --new-id=3 \
                  --new-data=/Users/joe/data --root-password=xxxx  

OPTIONS
=======

--version             show version number and exit

--help                show the help page       

-u <login user>, --user=<login user>
                      user name for server login

-p <login password>, --password=<login password>
                      password for server login

-h <host>, --host=<host>
                      hostname of server to connect default: localhost

-P <port>, --port=<port>
                      port for server login

-S <socket>, --socket=<socket>
                      socket for server login

--verbose             display additional information during operation

--new-data=<path to new datadir>
                      the full path to the location of the data directory for
                      the new instance

--new-port=<port>     the new port for the new instance - default=3307

--new-id=<server_id>  the server_id for the new instance - default=2

--root-password=<password>
                      password for the root user

--mysqld=<options>    additional options for mysqld

FILES
=====

- **mysqlcloneserver.py**  the utility script

- **mysql**                the MySQL utilities library

NOTES
=====

The login user must have the appropriate permissions to grant access to all
databases and the ability to create a user account.
