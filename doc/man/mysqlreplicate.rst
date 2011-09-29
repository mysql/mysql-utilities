.. _`mysqlreplicate`:

####################################################################
``mysqlreplicate`` - Setup and start replication between two servers
####################################################################

SYNOPSIS
--------

::

  mysqlreplicate --master=<user>[<passwd>]@<host>:[<port>][:<socket>]
                 --slave=<user>[<passwd>]@<host>:[<port>][:<socket>]
                 [[--help | --version] | --quiet |
                 --verbose | --testdb=<test database> | --pedantic
                 --rpl_user=<uid:passwd> | --master-log-file=<log_file> |
                 --master-log-pos=<pos> | --start-from-beginning]

DESCRIPTION
-----------

This utility permits an administrator to start replication among two
servers. The user provides login information to the slave and provides
connection information for connecting to the master.

You can also specify a database to be used to test replication as well as
a unix socket file for connecting to a master running on a local host.

The utility will report conditions where the storage engines on the master
and the slave differ. Warnings are issued by default or you can use the
--pedantic option to require the storage engines to be the same on both
the master and slave. This would include not only that both servers have
the same storage engines enabled but also that the default storage engine
is the same.

Furthermore, the utility will also report a warning if the InnoDB storage
engine differs from the master and slave. Similarly, :option:`--pedantic`
requires the InnoDB storage engine to the be the same on the master and slave.

The utility will setup replication to start from the current binary log file
and position of the master. However, you can instruct the utility to start from
the beginning of recorded events by using the :option:`--start-from-beginning`
option. You can also provide a binary log file from the master with the
:option:`--master-log-file` option which will start replication from the first
event in that binary log file. Or you can start replication from a specific
binary log file and position with the :option:`--master-log-file` and
:option:`--master-log-pos` options. In summary, replication can be started
using one of the following strategies.

Start from current position (default)
  Start replication from last known binary log file and position from the
  master. The *SHOW MASTER STATUS* command is used to retrieve this
  information.

Start from the beginning
  Start replication from the first event recorded in the binary logging of the
  master.
  
Start from a binary log file
  Start replication at the first event in a specific binary log file.
  
Start from a specific event
  Start replication from a specific position (event) in a specific binary log
  file.
  
The :option:`-vv` option will also display any discrepancies among the storage
engines and InnoDB values with or without the :option:`--pedantic` option.

OPTIONS
-------

.. option:: --version

   show version number and exit

.. option:: --help

   show help page

.. option:: --master <master>

   connection information for master server in the form:
   <user>:<password>@<host>:<port>:<socket>

.. option:: --slave <slave>

   connection information for slave server in the form:
   <user>:<password>@<host>:<port>:<socket>

.. option:: --rpl-user <replication-user>

   the user and password for the replication user requirement -
   For example, rpl:passwd - default = rpl:rpl

.. option:: --test-db <test database>

   database name to use in testing replication setup (optional)

.. option:: --master-log-file=<MASTER_LOG_FILE>

   use this master log file to initiate the slave.

.. option:: --master-log-pos=<MASTER_LOG_POS>

   use this position in the master log file to initiate the slave

.. option:: --start-from-beginning, -b

   start replication at the beginning of logged events. Not valid with
   --master-log-file or --master-log-pos

.. option:: --verbose, -v

   control how much information is displayed. For example, -v =
   verbose, -vv = more verbose, -vvv = debug

.. option:: --pedantic, -p

   fail if storage engines differ among master and slave (optional)


NOTES
-----

The login user must have the appropriate permissions to grant access to all
databases and the ability to create a user account. For example, the user
account used to connect to the master must have the WITH GRANT OPTION
privilege.

The server ID on the master and slave must be unique. The utility will
report an error if the server ID is 0 or is the same on the master and
slave. Set these values before starting this utility.

EXAMPLES
--------

To setup replication between a MySQL instance on two different hosts using
the default settings, use this command::

    $ mysqlreplicate --master=root@localhost:3306 \\
      --slave=root@localhost:3307 --rpl-user=rpl:rpl
    # master on localhost: ... connected.
    # slave on localhost: ... connected.
    # Checking for binary logging on master...
    # Setting up replication...
    # ...done.

The following command ensures the replication between the master and slave is
successful if and only if the InnoDB storage engines are the same and both
servers have the same storage engines with the same default specified.::

    $ mysqlreplicate --master=root@localhost:3306 \\
      --slave=root@localhost:3307 --rpl-user=rpl:rpl -vv --pedantic
    # master on localhost: ... connected.
    # slave on localhost: ... connected.
    # master id = 2
    #  slave id = 99
    # Checking InnoDB statistics for type and version conflicts.
    # Checking storage engines...
    # Checking for binary logging on master...
    # Setting up replication...
    # Flushing tables on master with read lock...
    # Connecting slave to master...
    # CHANGE MASTER TO MASTER_HOST = [...omitted...]
    # Starting slave...
    # status: Waiting for master to send event
    # error: 0:
    # Unlocking tables on master...
    # ...done.

The following command starts replication from the current position of the
master (default).::

   $ mysqlreplicate --master=root@localhost:3306 \\
        --slave=root@localhost:3307 --rpl-user=rpl:rpl
    # master on localhost: ... connected.
    # slave on localhost: ... connected.
    # Checking for binary logging on master...
    # Setting up replication...
    # ...done.

The following command tarts replication from the beginning of recorded events.::

   $ mysqlreplicate --master=root@localhost:3306 \\
        --slave=root@localhost:3307 --rpl-user=rpl:rpl \\
        --start-from-beginning
    # master on localhost: ... connected.
    # slave on localhost: ... connected.
    # Checking for binary logging on master...
    # Setting up replication...
    # ...done.

The following starts replication from the beginning of a specific binary log
file.::

   $ mysqlreplicate --master=root@localhost:3306 \\
        --slave=root@localhost:3307 --rpl-user=rpl:rpl \\
        --master-log-file=my_log.000003 
    # master on localhost: ... connected.
    # slave on localhost: ... connected.
    # Checking for binary logging on master...
    # Setting up replication...
    # ...done.

The following starts replication from an arbitrary binary log file and
position.::

   $ mysqlreplicate --master=root@localhost:3306 \\
        --slave=root@localhost:3307 --rpl-user=rpl:rpl \\
        --master-log-file=my_log.000001 --master-log-pos=96
    # master on localhost: ... connected.
    # slave on localhost: ... connected.
    # Checking for binary logging on master...
    # Setting up replication...
    # ...done.


RECOMMENDATIONS
---------------

You should use read_only = True in the my.cnf file for the slave to ensure no
accidental data changes such as INSERT, DELETE, UPDATE, etc. are permitted
on the slave.

Use the :option:`--pedantic` and :option:`-vv` options for setting up
replication on production servers to avoid possible problems with differing
storage engines.

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
