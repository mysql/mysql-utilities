.. `mysqlrplshow`:

################################################
``mysqlrplshow`` - Show Slaves for Master Server
################################################

SYNOPSIS
--------

::

 mysqlrplshow [options]

DESCRIPTION
-----------

This utility shows the replication slaves for a master. It prints a graph of
the master and its slaves labeling each with the host name and port number.

To explore the slaves for each client, use the :option:`--recurse` option.
This causes the utility to connect to each slave found and attempt to
determine whether it has any slaves. If slaves are found, the process
continues until the slave is found in the list of servers serving as masters
(a circular topology). The graph displays the topology with successive
indents. A notation is made for circular topologies.

If you use the :option:`--recurse` option, the utility attempts to connect
to the slaves using the user name and password provided for the master. By
default, if the connection attempt fails, the utility throws an error and
stops. To change this behavior, use the :option:`--prompt` option, which
permits the utility to prompt for the user name and password for each slave
that fails to connect. You can also use the :option:`--num-retries=n` option
to reattempt a failed connection 'n' times before the utility fails.

An example graph for a typical topology with relay slaves is shown here::

  # Replication Topology Graph::

  localhost:3311 (MASTER)
     |
     +--- localhost:3310 - (SLAVE)
     |
     +--- localhost:3312 - (SLAVE + MASTER)
         |
         +--- localhost:3313 - (SLAVE)

``MASTER``, ``SLAVE``, and ``SLAVE + MASTER`` indicate that a server
is a master only, slave only, and both slave and master, respectively.

A circular replication topology is shown like this, where ``<-->`` indicates
circularity::

  # Replication Topology Graph

  localhost:3311 (MASTER)
     |
     +--- localhost:3312 - (SLAVE + MASTER)
         |
         +--- localhost:3313 - (SLAVE + MASTER)
             |
             +--- localhost:3311 <--> (SLAVE)

To produce a column list in addition to the graph, specify the
:option:`--show-list` option.  In this case, to specify how to display the
list, use one of the following values with the :option:`--format` option:

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

The utility uses of the **SHOW SLAVE HOSTS** statement to determine which
slaves the master has. If you want to use the :option:`--recurse` option,
slaves should have been started with the ``--report-host`` and
``--report-port`` options set to their actual host name and port number or
the utility may not be able to connect to the slaves to determine their own
slaves.

OPTIONS
-------

:command:`mysqlrplshow` accepts the following command-line options:

.. option:: --help

   Display a help message and exit.

.. option:: --format=<format>, -f<format>

   Specify the display format for column list output.  Permitted format values
   are **grid**, **csv**, **tab**, and **vertical**. The default is **grid**.
   This option applies only if :option:`--show-list` is given.

.. option:: --master=<source>

   Connection information for the master server in
   <*user*>[:<*passwd*>]@<*host*>[:<*port*>][:<*socket*>] format.
   
.. option:: --max-depth=<N>

   The maximum recursion depth. This option is valid only if
   :option:`--recurse` is given.
   
.. option:: --num-retries=<num_retries>, -n<num_retries>

   The number of retries permitted for failed slave login attempts. This
   option is valid only if :option:`--prompt` is given.
   
.. option:: --prompt, -p

   Prompt for the slave user and password if different from the master user
   and password.

   If you give this option, the utility sets :option:`--num-retries` to 1 if
   that option is not set explicitly. This ensures at least one attempt to
   retry and prompt for the user name and password should a connection fail.

.. option:: --quiet, -q

   Turn off all messages for quiet execution. This option does not suppress
   errors or warnings.
   
.. option:: --recurse, -r

   Traverse the list of slaves to find additional master/slave connections.
   User this option to map a replication topology.
   
.. option:: --show-list, -l

   Display a column list of the topology.

.. option:: --version

   Display version information and exit.

NOTES
-----

The login user must have the **REPLICATE SLAVE** and **REPLICATE CLIENT**
privileges to successfully execute this utility. Specifically, the login
user must have appropriate permissions to execute **SHOW SLAVE STATUS**,
**SHOW MASTER STATUS**, and **SHOW SLAVE HOSTS**.

For the :option:`--format` option, the permitted values are not case
sensitive. In addition, values may be specified as any unambiguous prefix of
a valid value.  For example, :option:`--format=g` specifies the grid format.
An error occurs if a prefix matches more than one valid value.

EXAMPLES
--------

To show the slaves for a master running on port 3311 on the local host, use
the following command::

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

    $ mysqlrplshow  --master=root@localhost:3311 --recurse
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

To show the full replication topology of a master running on the local host,
prompting for the user name and password for slaves that do not have the same
user name and password credentials as the master, use the following command::

    $ mysqlrplshow --recurse --prompt --num-retries=1 \
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
