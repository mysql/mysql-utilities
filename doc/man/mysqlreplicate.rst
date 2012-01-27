.. _`mysqlreplicate`:

#####################################################################
``mysqlreplicate`` - Set Up and Start Replication Between Two Servers
#####################################################################

SYNOPSIS
--------

::

 mysqlreplicate [options]

DESCRIPTION
-----------

This utility permits an administrator to start replication from one server
(the master) to another (the slave).  The user provides login information
for the slave and connection information for connecting to the master. It
is also possible to specify a database to be used to test replication.

The utility reports conditions where the storage engines on the master and
the slave differ. It also reports a warning if the InnoDB storage engine
differs on the master and slave. For InnoDB to be the same, both servers
must be running the same "type" of InnoDB (built-in or the InnoDB Plugin),
and InnoDB on both servers must have the same major and minor version
numbers and enabled state.

By default, the utility issues warnings for mismatches between the sets of
storage engines, the default storage engine, and the InnoDB storage engine.
To produce errors instead, use the :option:`--pedantic` option, which
requires storage engines to be the same on the master and slave.

The :option:`-vv` option displays any discrepancies between the storage
engines and InnoDB values, with or without the :option:`--pedantic` option.

Replication can be started using one of the following strategies.

Start from the current position (default)
  Start replication from the current master binary log file and position. The
  utility uses the **SHOW MASTER STATUS** statement to retrieve this
  information.

Start from the beginning
  Start replication from the first event recorded in the master binary log.
  To do this, use the :option:`--start-from-beginning` option.
  
Start from a binary log file
  Start replication from the first event in a specific master binary log file.
  To do this, use the :option:`--master-log-file` option.
  
Start from a specific event
  Start replication from specific event coordinates (specific binary log file
  and position). To do this, use the :option:`--master-log-file` and
  :option:`--master-log-pos` options.

OPTIONS
-------

:command:`mysqlreplicate` accepts the following command-line options:

.. option:: --help

   Display a help message and exit.

.. option:: --master=<master>

   Connection information for the master server in
   <*user*>[:<*passwd*>]@<*host*>[:<*port*>][:<*socket*>] format.

.. option:: --master-log-file=<master_log_file>

   Begin replication from the beginning of this master log file.

.. option:: --master-log-pos=<master_log_pos>

   Begin replication from this position in the master log file. This option
   is not valid unless :option:`--master-log-file` is given.

.. option:: --pedantic, -p

   Fail if both servers do not have the same set of storage engines, the same
   default storage engine, and the same InnoDB storage engine.

.. option:: --rpl-user=<replication_user>

   The user and password for the replication user, in *name:passwd* format.
   The default is ``rpl:rpl``.

.. option:: --slave=<slave>

   Connection information for the slave server in
   <*user*>[:<*passwd*>]@<*host*>[:<*port*>][:<*socket*>] format.

.. option:: --start-from-beginning, -b

   Start replication at the beginning of events logged in the master binary
   log. This option is not valid unless both :option:`--master-log-file` and
   :option:`--master-log-pos` are given.

.. option:: --test-db=<test_database>

   The database name to use for testing the replication setup. If this option
   is not given, no testing is done, only error checking.

.. option:: --verbose, -v

   Specify how much information to display. Use this option
   multiple times to increase the amount of information.  For example,
   :option:`-v` = verbose, :option:`-vv` = more verbose, :option:`-vvv` =
   debug.

.. option:: --version

   Display version information and exit.


NOTES
-----

The login user for the master server must have the appropriate permissions
to grant access to all databases and the ability to create a user account.
For example, the user account used to connect to the master must have the
**WITH GRANT OPTION** privilege.

The server IDs on the master and slave must be nonzero and unique. The
utility reports an error if the server ID is 0 on either server or the same
on the master and slave. Set these values before starting this utility.

EXAMPLES
--------

To set up replication between two MySQL instances running on different ports
of the same host using the default settings, use this command::

    $ mysqlreplicate --master=root@localhost:3306 \
      --slave=root@localhost:3307 --rpl-user=rpl:rpl
    # master on localhost: ... connected.
    # slave on localhost: ... connected.
    # Checking for binary logging on master...
    # Setting up replication...
    # ...done.

The following command uses :option:`--pedantic` to ensure that
replication between the master and slave is successful if and only
if both servers have the same storage engines available, the same
default storage engine, and the same InnoDB storage engine::

    $ mysqlreplicate --master=root@localhost:3306 \
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
master (which is the default)::

   $ mysqlreplicate --master=root@localhost:3306 \
        --slave=root@localhost:3307 --rpl-user=rpl:rpl
    # master on localhost: ... connected.
    # slave on localhost: ... connected.
    # Checking for binary logging on master...
    # Setting up replication...
    # ...done.

The following command starts replication from the beginning of recorded events
on the master::

   $ mysqlreplicate --master=root@localhost:3306 \
        --slave=root@localhost:3307 --rpl-user=rpl:rpl \
        --start-from-beginning
    # master on localhost: ... connected.
    # slave on localhost: ... connected.
    # Checking for binary logging on master...
    # Setting up replication...
    # ...done.

The following command starts replication from the beginning of a
specific master binary log file::

   $ mysqlreplicate --master=root@localhost:3306 \
        --slave=root@localhost:3307 --rpl-user=rpl:rpl \
        --master-log-file=my_log.000003 
    # master on localhost: ... connected.
    # slave on localhost: ... connected.
    # Checking for binary logging on master...
    # Setting up replication...
    # ...done.

The following command starts replication from specific master binary log
coordinates (specific log file and position)::

   $ mysqlreplicate --master=root@localhost:3306 \
        --slave=root@localhost:3307 --rpl-user=rpl:rpl \
        --master-log-file=my_log.000001 --master-log-pos=96
    # master on localhost: ... connected.
    # slave on localhost: ... connected.
    # Checking for binary logging on master...
    # Setting up replication...
    # ...done.


RECOMMENDATIONS
---------------

You should set ``read_only = 1`` in the ``my.cnf`` file for the slave to
ensure that no accidental data changes, such as **INSERT**, **DELETE**,
**UPDATE**, and so forth, are permitted on the slave other than those
produced by events read from the master.

Use the :option:`--pedantic` and :option:`-vv` options for setting up
replication on production servers to avoid possible problems with differing
storage engines.

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
