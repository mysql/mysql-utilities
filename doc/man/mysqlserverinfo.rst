.. _`mysqlserverinfo`:

#########################################################################
``mysqlserverinfo`` - Display Common Diagnostic Information from a Server
#########################################################################

SYNOPSIS
--------

::

 mysqlserverinfo [options]

DESCRIPTION
-----------

This utility displays critical information about a server for use
in diagnosing problems. The information displayed includes the
following:

* Server connection information
* Server version number
* Data directory path name
* Base directory path name
* Plugin directory path name
* Configuration file location and name
* Current binary log coordinates (file name and position)
* Current relay log coordinates (file name and position)

This utility can be used to see the diagnostic information for servers that
are running or offline.  If you want to see information about an offline
server, the utility starts the server in read-only mode. In this case, you must
specify the :option:`--basedir`, :option:`--datadir`, and :option:`--start`
options to prevent the utility from starting an offline server accidentally.
Note: Be sure to consider the ramifications of starting an offline server on the
error and similar logs. It is best to save this information prior to running
this utility.

To specify how to display output, use one of the following values
with the :option:`--format` option:

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

To turn off the headers for **csv** or **tab** display format, specify
the :option:`--no-headers` option.

To see the common default settings for the local server's configuration
file, use the :option:`--show-defaults` option. This option reads the
configuration file on the machine where the utility is run, not the machine
for the host that the :option:`--server` option specifies.

To run the utility against several servers, specify the
:option:`--server` option multiple times. In this case, the utility 
attempts to connect to each server and read the information.

To see the MySQL servers running on the local machine, use the
:option:`--show-servers` option. This shows all the servers with
their process ID and data directory. On Windows, the utility shows
only the process ID and port.

OPTIONS
-------

:command:`mysqlserverinfo` accepts the following command-line options:

.. option:: --help

   Display a help message and exit.

.. option:: --basedir=<basedir>

   The base directory for the server. This option is required for starting an
   offline server.
  
.. option:: --datadir=<datadir>

   The data directory for the server. This option is required for starting an
   offline server.

.. option:: --format=<format>, -f<format>

   Specify the output display format. Permitted format values are **grid**,
   **csv**, **tab**, and **vertical**. The default is **grid**.

.. option:: --no-headers, -h

   Do not display column headers. This option applies only for **csv** and
   **tab** output.
   
.. option:: --port-range=<start:end>

   The port range to check for finding running servers. This option applies
   only to Windows and is ignored unless :option:`--show-servers` is given.
   The default range is 3306:3333.

.. option:: --server=<server>

   Connection information for a server in
   <*user*>[:<*passwd*>]@<*host*>[:<*port*>][:<*socket*>] format.
   Use this option multiple times to see information for multiple servers.

.. option:: --show-defaults, -d

   Display default settings for :command:`mysqld` from the local configuration
   file. It uses :command:`my_print_defaults` to obtain the options.
   
.. option:: --show-servers

   Display information about servers running on the local host. The utility
   examines the host process list to determine which servers are running.

.. option:: --start, -s

   Start the server in read-only mode if it is offline. With this option, you
   must also give the :option:`--basedir` and :option:`--datadir` options.

.. option:: --verbose, -v

   Specify how much information to display. Use this option
   multiple times to increase the amount of information.  For example,
   :option:`-v` = verbose, :option:`-vv` = more verbose, :option:`-vvv` =
   debug.

.. option:: --version

   Display version information and exit.

.. _mysqlserverinfo-notes:

For the :option:`--format` option, the permitted values are not case
sensitive. In addition, values may be specified as any unambiguous prefix of
a valid value.  For example, :option:`--format=g` specifies the grid format.
An error occurs if a prefix matches more than one valid value.

EXAMPLES
--------

To display the server information for the local server and the settings for
:command:`mysqld` in the configuration file with the output in a vertical
list, use this command::

    $ mysqlserverinfo --server=root:pass@localhost -d --format=vertical
    # Source on localhost: ... connected.
    *************************       1. row *************************
             server: localhost:3306
            version: 5.1.50-log
            datadir: /usr/local/mysql/data/
            basedir: /usr/local/mysql-5.1.50-osx10.6-x86_64/
         plugin_dir: /usr/local/mysql-5.1.50-osx10.6-x86_64/lib/plugin
        config_file: /etc/my.cnf
         binary_log: my_log.000068
     binary_log_pos: 212383
          relay_log: None
      relay_log_pos: None
    1 rows.
      
    Defaults for server localhost:3306
      --port=3306
      --basedir=/usr/local/mysql
      --datadir=/usr/local/mysql/data
      --server_id=5
      --log-bin=my_log
      --general_log
      --slow_query_log
      --innodb_data_file_path=ibdata1:778M;ibdata2:50M:autoextend
    #...done.

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
