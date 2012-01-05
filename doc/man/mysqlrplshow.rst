.. `mysqlrplshow`:

################################################
``mysqlrplshow`` - Show Slaves for Master Server
################################################

SYNOPSIS
--------

::

  mysqlrplshow --master=<user>[:<passwd>]@<host>[:<port>][:<socket>]
              --help | --version | --show-list | --quiet |
              --recurse | --prompt | --num-retries |
              --format=[SQL|S|GRID|G|TAB|T|CSV|C|VERTICAL|V]

DESCRIPTION
-----------

This utility is used to show the slaves for a master. It will print a graph of
the master and its slaves labeling each with the hostname and port.

You can choose to explore the slaves for each client with the
:option:`--recurse` option. This will permit the utility to connect to
each slave found and attempt to find if it has any slaves. If slaves are found,
the process continues until the slave is found in the list of servers serving
as masters (a circular topology). The graph displays the topology with
successive indents. A notation is made for circular topologies.

An example of the graph for a typical topology with relay slaves is shown
here::

  # Replication Topology Graph::

  localhost:3311 (MASTER)
     |
     +--- localhost:3310 - (SLAVE)
     |
     +--- localhost:3312 - (SLAVE + MASTER)
         |
         +--- localhost:3313 - (SLAVE)

A circular replication topology would be shown like the following::

  # Replication Topology Graph

  localhost:3311 (MASTER)
     |
     +--- localhost:3312 - (SLAVE + MASTER)
         |
         +--- localhost:3313 - (SLAVE + MASTER)
             |
             +--- localhost:3311 <--> (SLAVE)

You can specify the :option:`--show-list` option to produce a column list of
the graph. You also have the choice to view the output in one of the following
formats using the :option:`--format` option.

**GRID** (default)
  Display output formatted like that of the mysql monitor in a grid
  or table layout.

**CSV**
  Display output in comma-separated values format.

**TAB**
  Display output in tab-separated format.

**VERTICAL**
  Display output in a single column similar to the ``\G`` command
  for the mysql monitor.


If you elect to use the :option:`--recurse` option, the utility will
attempt to connect to the slaves using the user name and password provided for
the master. If these credentials do not work (the connection fails), the
utility will thrown an error and stop. This behavior can be changed using the
:option:`--prompt` option which will permit the utility to prompt for the user
name and password for each slave that fails to connect. You can also use the
:option:`--num-retries=n` option to reattempt a failed connection 'n' times
before the utility fails.

The utility reports slaves by use of the **SHOW SLAVE HOSTS** statement whereby the
slaves should be started with the --report-host and --report-port options
specified. If you want to use the :option:`--recurse` option, the values for
these options must be set to the actual port and host of the slaves else the
utility may not be able to connect to the slaves to find their slaves.

OPTIONS
-------

**mysqlrplshow** accepts the following command-line options:

.. option:: --help

   Display a help message and exit.

.. option:: --format=<format>, -f<format>

   Specify the output display format. Permitted format values are
   GRID, CSV, TAB, and VERTICAL. The default is GRID.

.. option:: --master=<source>

   Connection information for the master server in the format:
   <user>[:<passwd>]@<host>[:<port>][:<socket>]
   
.. option:: --num-retries=<num_retries>, -n<num_retries>

   Number of retries permitted for failed slave login attempts. Valid only with
   :option:`--prompt`.
   
.. option:: --prompt, -p

   Prompt for slave user and password if different from master login.

.. option:: --quiet, -q

   Turn off all messages for quiet execution. Note: Errors and warnings are
   not suppressed.
   
.. option:: --recurse, -r

   Traverse the list of slaves to find additional master/slave connections.
   User this option to map a replication topology.
   
.. option:: --show-list, -l

   Print a list of the topology.

.. option:: --version

   Display version information and exit.

NOTES
-----

The login user must have the **REPLICATE SLAVE** and **REPLICATE CLIENT**
privileges to successfully execute this utility. Specifically, the login user
must have appropriate permissions to execute **SHOW SLAVE STATUS**, **SHOW MASTER
STATUS**, and **SHOW SLAVE HOSTS**.

When using the :option:`--prompt` option, the utility sets the
:option:`--num-retries` option to 1 if not set explicitly. This ensures at
least one attempt to retry and prompt for the user name and password should a
connection fail.

EXAMPLES
--------

To show the slaves for a master running on the local host, use the following
command::

    $ mysqlrplshow  --master=root@localhost:3311 
    # master on localhost: ... connected.
    # Finding slaves for master: localhost:3311
    
    # Replication Topology Graph
    localhost:3311 (MASTER)
       |
       +--- localhost:3310 - (SLAVE)
       |
       +--- localhost:3312 - (SLAVE)

As shown in the example, you must provide valid login information
for the master.

To show the full replication topology of a master running on the local host,
use the following command::

    $ mysqlrplshow  --master=root@localhost:3311 
                    --recurse
    # master on localhost: ... connected.
    # Finding slaves for master: localhost:3311
    
    # Replication Topology Graph
    localhost:3311 (MASTER)
       |
       +--- localhost:3310 - (SLAVE)
       |
       +--- localhost:3312 - (SLAVE + MASTER)
           |
           +--- localhost:3313 - (SLAVE)

To show the full replication topology of a master runnin on the local host,
prompting for the user name and password for slaves that do not have the same
user name and password credentials as the master, use the following command::

    $ mysqlrplshow --recurse --prompt --num-retries=1
      --master=root@localhost:3331
     
    Server localhost:3331 is running on localhost.
    # master on localhost: ... connected.
    # Finding slaves for master: localhost:3331
    Server localhost:3332 is running on localhost.
    # master on localhost: ... FAILED.
    Connection to localhost:3332 has failed.
    Please enter the following information to connect to this server.
    User name: root
    Password: 
    # master on localhost: ... connected.
    # Finding slaves for master: localhost:3332
    Server localhost:3333 is running on localhost.
    # master on localhost: ... FAILED.
    Connection to localhost:3333 has failed.
    Please enter the following information to connect to this server.
    User name: root
    Password: 
    # master on localhost: ... connected.
    # Finding slaves for master: localhost:3333
    Server localhost:3334 is running on localhost.
    # master on localhost: ... FAILED.
    Connection to localhost:3334 has failed.
    Please enter the following information to connect to this server.
    User name: root
    Password: 
    # master on localhost: ... connected.
    # Finding slaves for master: localhost:3334
    
    # Replication Topology Graph
    localhost:3331 (MASTER)
       |
       +--- localhost:3332 - (SLAVE)
       |
       +--- localhost:3333 - (SLAVE + MASTER)
           |
           +--- localhost:3334 - (SLAVE)

COPYRIGHT
---------

Copyright (c) 2011, Oracle and/or its affiliates. All rights reserved.

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
