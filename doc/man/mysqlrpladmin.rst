.. `mysqlrpladmin`:

################################################################
``mysqlrpladmin`` - Administration utility for MySQL replication
################################################################

SYNOPSIS
--------

::

 mysqlrpladmin [options]

DESCRIPTION
-----------

This utility permits users to perform administrative actions on a replication
topology consisting of a master and its slaves. The utility is designed to make
it easy to recover from planned maintenance of the master or from an event that
takes the master offline unexpectedly.

The act of taking the master offline intentionally and switching control to
another slave is called switchover. In this case, there is no loss of
transactions as the master is locked and all slaves are allowed to catch up to
the master. Once the slaves have read all events from the master, the master is
shutdown and control switched to a slave (in this case called a candidate
slave).

Recovering from the loss of a downed master is more traumatic and since there
is no way to know what transactions the master may have failed to send, the new
master (called a candidate slave) must be the slave that is most up-to-date.
How this is determined depends on the version of the server (see below).
However, it can result in the loss of some transactions that were executed on
the downed master but not sent. The utility accepts a list of slaves to be
considered the candidate slave. If no slave is found to meet the requirements,
the operation will search the list of known slaves.

The utility also provides a number of useful commands for managing a
replication topology including the following.

**elect**
This command is available to only those servers supporting global transaction
identifiers (GTIDs), perform best slave election and report best slave to use
in the event a switchover or failover is required. Best slave election is
simply the first slave to meet the prerequisites. GTIDs are supported in
version 5.6.5 and higher. 

**failover**
This command is available to only those servers supporting GTIDs. Conduct
failover to the best slave. The command will test each candidate slave listed
for the prerequisites. Once a candidate slave is elected, it is made a slave of
each of the other slaves thereby collecting any transactions executed on other
slaves but not the candidate. In this way, the candidate becomes the most
up-to-date slave.

**gtid**
This command is available to only those servers supporting GTIDs. It displays
the contents of the GTID variables, @@GLOBAL.GTID_DONE, @@GLOBAL.GTID_LOST, and
@@GLOBAL.GTID_OWNED. The command also displays universally unique identifiers
(UUIDs) for all servers.

**health**
Display the replication health of the topology. By default, this includes the
host name, port, role (MASTER or SLAVE) of the server, state of the server (UP
= is connected, WARN = not connected but can ping, DOWN = not connected and
cannot ping), the GTID_MODE, and health state.

The master health state is based on the following; if GTID_MODE=ON, the server
must have binary log enabled, and there must exist a user with the REPLICATE
SLAVE privilege.

The slave health state is based on the following; the IO_THREAD and SQL_THREADS
must be running, it must be connected to the master, there are no errors, the
slave delay for non-gtid enabled scenarios is not more than the threshold
provided by the :option:`--max-position` and the slave is reading the correct
master log file, and slave delay is not more than the
:option:`--seconds-behind` threshold option. 
  
**reset**
Execute the STOP SLAVE and RESET SLAVE commands on all slaves.

**start**
Execute the START SLAVE command on all slaves.

**stop**
Execute the STOP SLAVE command on all slaves.

**switchover**
Perform slave promotion to a specified candidate slave as designated by the
:option:`--new-master` option. This command is available for both gtid-enabled
servers and non-gtid-enabled scenarios.

Detection of a downed master is performed as follows. If the connection to the
master is lost, wait :option:`--timeout` seconds and check again. If the master
connection is lost and the master cannot be pinged or reconnected, the failover
event occurs.
  
For all commands that require specifying multiple servers, the options require
a comma-separated list of connection parameters in the following form where the
password, port, and socket are optional.::

<*user*>[:<*passwd*>]@<*host*>[:<*port*>][:<*socket*>],

The utility permits users to discover slaves connected to the master. In
order to use the discover slaves feature, all slaves must use the --report-host
and --report-port startup variables to specify the correct hostname and ip
port of the slave. If these are missing or report the incorrect information,
the slaves health may not be reported correctly or the slave may not be listed
at all. The discover slaves feature ignores any slaves it cannot connect to.

The utility permits the user to demote a master to a slave during the
switchover operation. The :option:`--demote-master` option tells the utility
to, once the new master is established, make the old master a slave of the
new master. This permits rotation of the master role among a set of servers.

The utility permits the user to specify an external script to execute
before and after the switchover and failover commands. The user can specify
these with the :option:`--exec-before` and :option:`--exec-after` options.
The return code of the script is used to determine success thus each script
must report 0 (success) to be considered successful. If a script returns a
value other than 0, the result code is presented in an error message.

The utility permits the user to log all actions taken during the commands. The
:option:`--log` option requires a valid path and file name of the file to use
for logging operations. The log is active only when this option is specified.
The option :option:`--log-age` specifies the age in days that log entries are
kept. The default is seven (7) days. Older entries are automatically deleted
from the log file (but only if the :option:`--log` option is specified).

The format of the log file includes the date and time of the event, the level
of the event (informational - INFO, warning - WARN, error - ERROR, critical
failure - CRITICAL), and the message reported by the utility.

The utility has a number of options each explained in more detail below.
Some of the options are specific to certain commands. Warning messages are
issued whenever an option is used that does not apply to the command requested.
A brief overview of each command and its options is presented in the following
paragraphs.

The elect, failover, start, stop, and reset commands require either the
:option:`--slaves` option to list all of the slaves in the topology or the
:option:`--discover-slaves-login` option to provide the user name and password
to discover any slaves in the topology that are registered to the master but
are not listed in the :option:`--slaves` option.

The options required for the health and gtid commands include the
:option:`--master` option to specify the existing master, and either the
:option:`--slaves` option to list all of the slaves in the topology or the
:option:`--discover-slaves-login` option to provide the user name and password
to discover any slaves in the topology that are registered to the master but
are not listed in the :option:`--slaves` option.

Use the :option:`--verbose` option to see additional information in the
health report and additional messages during switchover or failover.

The options required for switchover include the :option:`--master` option to
specify the existing master, the :option:`--new-master` option to specify the
candidate slave (the slave to become the new master.


OPTIONS
-------

:command:`mysqlrpladmin` accepts the following command-line options:

.. option:: --help

   Display a help message and exit.

.. option:: --candidates=<candidate slave connections>

   Connection information for candidate slave servers for failover in the form:
   <*user*>[:<*passwd*>]@<*host*>[:<*port*>][:<*socket*>]. Valid only with
   failover command. List multiple slaves in comma- separated list.

.. option:: --demote-master

   Make master a slave after switchover.

.. option:: --discover-slaves-login=<user:password>

   At startup, query master for all registered slaves and use the user name and
   password specified to connect. Supply the user and password in the form
   <*user*>[:<*passwd*>]. For example, --discover=joe:secret will use 'joe' as
   the user and 'secret' as the password for each discovered slave.

.. option:: --exec-after=<script>

   Name of script to execute after failover or switchover. Script name may
   include the path.

.. option:: --exec-before=<script>

   Name of script to execute before failover or switchover. Script name may
   include the path.

.. option::--force

   Ignore prerequisite check results and execute action.

.. option:: --format=<format>, -f <format>

   Display the replication health output in either grid (default), tab, csv, or
   vertical format.
  
.. option:: --log=<log_file>

   Specify a log file to use for logging messages

.. option:: --log-age=<days>

   Specify maximum age of log entries in days. Entries older than this will be
   purged on startup. Default = 7 days.

.. option:: --master=<connection>

   Connection information for the master server in
   <*user*>[:<*passwd*>]@<*host*>[:<*port*>][:<*socket*>] format.

.. option:: --max-position=<position>

   Used to detect slave delay. The maximum difference between the master's
   log position and the slave's reported read position of the master. A value
   greater than this means the slave is too far behind the master. Default = 0.

.. option:: --new-master=<connection>

   Connection information for the slave to be used to replace the master for
   switchover in the form:
   <*user*>[:<*passwd*>]@<*host*>[:<*port*>][:<*socket*>]. Valid only with
   switchover command.
   
.. option:: --no-health

   Turn off health report after switchover or failover.

.. option:: --ping=<number>

   Number of ping attempts for detecting downed server. Note: on some
   platforms this is the same as number of seconds to wait for ping to
   return.

.. option:: --quiet, -q

   Turn off all messages for quiet execution.

.. option:: --seconds-behind=<seconds>

   Used to detect slave delay. The maximum number of seconds behind the master
   permitted before slave is considered behind the master. Default = 0.

.. option:: --slaves=<slave connections>

   Connection information for slave servers in the form:
   <*user*>[:<*passwd*>]@<*host*>[:<*port*>][:<*socket*>]. List multiple slaves
   in comma-separated list.

.. option:: --timeout=<seconds>

   Maximum timeout in seconds to wait for each replication command to complete.
   For example, timeout for slave waiting to catch up to master. Default = 3.
   Also used to check down status of master. Failover will wait timeout
   seconds to check master response. If no response, failover event occurs.

.. option::  --verbose, -v

   Specify how much information to display. Use this option
   multiple times to increase the amount of information.  For example,
   :option:`-v` = verbose, :option:`-vv` = more verbose, :option:`-vvv` =
   debug.

.. option:: --version

   Display version information and exit.


NOTES
-----

The login user must have the appropriate permissions to execute **SHOW SLAVE
STATUS**, **SHOW MASTER STATUS**, and **SHOW VARIABLES** on the appropriate
servers as well as grant the REPLICATE SLAVE privilege. The utility checks
permissions for the master, slaves, and candidates at startup.

The :option:`--force` option cannot be used with the failover command.


EXAMPLES
--------

To perform best slave election for a topology with GTID_MODE=ON (server version
5.6.5 or higher) where all slaves are specified with the :option:`--slaves1`
option, run the following command.::

  $ mysqlrpladmin --master=root@localhost:3331 \
    --slaves=root@localhost:3332,root@localhost:3333,root@localhost:3334 elect
  # Electing candidate slave from known slaves.
  # Best slave found is located on localhost:3332.
  # ...done.

To perform best slave election supplying a candidate list, use the following
command.::

  $ mysqlrpladmin --master=root@localhost:3331 \
    --slaves=root@localhost:3332,root@localhost:3333,root@localhost:3334 \
    --candidates=root@localhost:3333,root@localhost:3334 elect
  # Electing candidate slave from candidate list then slaves list.
  # Best slave found is located on localhost:3332.
  # ...done.

To perform failover after a master has failed, use the following command.::

  $ mysqlrpladmin  \
    --slaves=root@localhost:3332,root@localhost:3333,root@localhost:3334 \
    --candidates=root@localhost:3333,root@localhost:3334 failover
  # Performing failover.
  # Candidate slave localhost:3333 will become the new master.
  # Preparing candidate for failover.
  # Creating replication user if it does not exist.
  # Stopping slaves.
  # Performing STOP on all slaves.
  # Switching slaves to new master.
  # Starting slaves.
  # Performing START on all slaves.
  # Checking slaves for errors.
  # Failover complete.
  # ...done.

To see the replication health of a topology with GTID_MODE=ON (server version
5.6.5 or higher) and discover all slaves attached to the master, run the
following command. We use the result of the failover command above.::

  $ mysqlrpladmin --master=root@localhost:3333 \
    --slaves=root@localhost:3332,root@localhost:3334 health
  # Getting health for master: localhost:3333.
  #
  # Replication Topology Health:
  +------------+-------+---------+--------+------------+---------+
  | host       | port  | role    | state  | gtid_mode  | health  |
  +------------+-------+---------+--------+------------+---------+
  | localhost  | 3333  | MASTER  | UP     | ON         | OK      |
  | localhost  | 3332  | SLAVE   | UP     | ON         | OK      |
  | localhost  | 3334  | SLAVE   | UP     | ON         | OK      |
  +------------+-------+---------+--------+------------+---------+
  # ...done.
  
To view a detailed replication health report but with all of the replication
health checks revealed, use the :option:`--verbose` option as shown below.
In this example, we use vertical format to make viewing easier.::

  $ mysqlrpladmin --master=root@localhost:3331 \
    --slaves=root@localhost:3332,root@localhost:3333,root@localhost:3334 \
    --verbose health
  # Getting health for master: localhost:3331.
  # Attempting to contact localhost ... Success
  # Attempting to contact localhost ... Success
  # Attempting to contact localhost ... Success
  # Attempting to contact localhost ... Success
  #
  # Replication Topology Health:
  *************************       1. row *************************
              host: localhost
              port: 3331
              role: MASTER
             state: UP
         gtid_mode: ON
            health: OK
           version: 5.6.5-m8-debug-log
   master_log_file: mysql-bin.000001
    master_log_pos: 571
         IO_Thread: 
        SQL_Thread: 
       Secs_Behind: 
   Remaining_Delay: 
      IO_Error_Num: 
          IO_Error: 
  *************************       2. row *************************
              host: localhost
              port: 3332
              role: SLAVE
             state: UP
         gtid_mode: ON
            health: OK
           version: 5.6.5-m8-debug-log
   master_log_file: mysql-bin.000001
    master_log_pos: 571
         IO_Thread: Yes
        SQL_Thread: Yes
       Secs_Behind: 0
   Remaining_Delay: No
      IO_Error_Num: 0
          IO_Error: 
  *************************       3. row *************************
              host: localhost
              port: 3333
              role: SLAVE
             state: UP
         gtid_mode: ON
            health: OK
           version: 5.6.5-m8-debug-log
   master_log_file: mysql-bin.000001
    master_log_pos: 571
         IO_Thread: Yes
        SQL_Thread: Yes
       Secs_Behind: 0
   Remaining_Delay: No
      IO_Error_Num: 0
          IO_Error: 
  *************************       4. row *************************
              host: localhost
              port: 3334
              role: SLAVE
             state: UP
         gtid_mode: ON
            health: OK
           version: 5.6.5-m8-debug-log
   master_log_file: mysql-bin.000001
    master_log_pos: 571
         IO_Thread: Yes
        SQL_Thread: Yes
       Secs_Behind: 0
   Remaining_Delay: No
      IO_Error_Num: 0
          IO_Error: 
  4 rows.
  # ...done.

To run the same failover command above, but specify a log file, use the
following command.::

  $ mysqlrpladmin  \
    --slaves=root@localhost:3332,root@localhost:3333,root@localhost:3334 \
    --candidates=root@localhost:3333,root@localhost:3334 \
    --log=test_log.txt failover
  # Performing failover.
  # Candidate slave localhost:3333 will become the new master.
  # Preparing candidate for failover.
  # Creating replication user if it does not exist.
  # Stopping slaves.
  # Performing STOP on all slaves.
  # Switching slaves to new master.
  # Starting slaves.
  # Performing START on all slaves.
  # Checking slaves for errors.
  # Failover complete.
  # ...done.

After this command, the log file will contain entries like the following::

  2012-03-19 14:44:17 PM INFO Executing failover command...
  2012-03-19 14:44:17 PM INFO Performing failover.
  2012-03-19 14:44:17 PM INFO Candidate slave localhost:3333 will become the new master.
  2012-03-19 14:44:17 PM INFO Preparing candidate for failover.
  2012-03-19 14:44:19 PM INFO Creating replication user if it does not exist.
  2012-03-19 14:44:19 PM INFO Stopping slaves.
  2012-03-19 14:44:19 PM INFO Performing STOP on all slaves.
  2012-03-19 14:44:19 PM INFO Switching slaves to new master.
  2012-03-19 14:44:20 PM INFO Starting slaves.
  2012-03-19 14:44:20 PM INFO Performing START on all slaves.
  2012-03-19 14:44:20 PM INFO Checking slaves for errors.
  2012-03-19 14:44:21 PM INFO Failover complete.
  2012-03-19 14:44:21 PM INFO ...done.

To perform switchover and demote the current master to a slave, use the
following command.::

  $ mysqlrpladmin --master=root@localhost:3331 \
    --slaves=root@localhost:3332,root@localhost:3333,root@localhost:3334 \
    --new-master=root@localhost:3332 --demote-master switchover
  # Performing switchover from master at localhost:3331 to slave at localhost:3332.
  # Checking candidate slave prerequisites.
  # Waiting for slaves to catch up to old master.
  # Stopping slaves.
  # Performing STOP on all slaves.
  # Demoting old master to be a slave to the new master.
  # Switching slaves to new master.
  # Starting all slaves.
  # Performing START on all slaves.
  # Checking slaves for errors.
  # Switchover complete.
  # ...done.
  
If the replication health report is generated on the topology following the
above command, it will display the old master as a slave as shown below.::

  # Replication Topology Health:
  +------------+-------+---------+--------+------------+---------+
  | host       | port  | role    | state  | gtid_mode  | health  |
  +------------+-------+---------+--------+------------+---------+
  | localhost  | 3332  | MASTER  | UP     | ON         | OK      |
  | localhost  | 3331  | SLAVE   | UP     | ON         | OK      |
  | localhost  | 3333  | SLAVE   | UP     | ON         | OK      |
  | localhost  | 3334  | SLAVE   | UP     | ON         | OK      |
  +------------+-------+---------+--------+------------+---------+

To use the discover slaves feature, you can omit the :option:`--slaves` option
if and only if all slaves report their host and port to the master. A sample
command to generate a replication health report with discovery is shown below.
he option:`--discover-slaves-login` option can be used in conjunction with the
:option:`--slaves` option to specify a list of known slaves (or slaves that do
not report their host and ip) and to discover any other slaves connected to the
master.::

  $ mysqlrpladmin --master=root@localhost:3332 \
    --discover-slaves-login=root  health
  # Discovering slaves for master at localhost:3332
  # Getting health for master: localhost:3332.
  #
  # Replication Topology Health:
  +------------+-------+---------+--------+------------+---------+
  | host       | port  | role    | state  | gtid_mode  | health  |
  +------------+-------+---------+--------+------------+---------+
  | localhost  | 3332  | MASTER  | UP     | ON         | OK      |
  | localhost  | 3331  | SLAVE   | UP     | ON         | OK      |
  | localhost  | 3333  | SLAVE   | UP     | ON         | OK      |
  | localhost  | 3334  | SLAVE   | UP     | ON         | OK      |
  +------------+-------+---------+--------+------------+---------+
  # ...done.


COPYRIGHT
---------

Copyright (c) 2011, 2012, Oracle and/or its affiliates. All rights reserved.

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
