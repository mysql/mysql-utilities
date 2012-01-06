.. _`mysqlserverinfo`:

#########################################################################
``mysqlserverinfo`` - Display Common Diagnostic Information from a Server
#########################################################################

SYNOPSIS
--------

::

 mysqlserverinfo [ --server=<user>[:<passwd>]@<host>[:<port>][:<socket>] |
                   [, --server=<user>[:<passwd>]@<host>[:<port>][:<socket>] ] |
                   --format=[|GRID|CSV|TAB|VERTICAL] ] | --no-headers |
                   --show-defaults | [--start --basedir=<base directory> 
                   --datadir=<data directory>] --verbose

DESCRIPTION
-----------

This utility permits a database administrator to view critical information
about a server for use in diagnosing problems. The information displayed
includes the following:

    * Server connection information
    * Version number of the server
    * Data directory path
    * Base directory path
    * Plugin directory path
    * Configuration file location and name
    * Current binary log file
    * Current binary log position
    * Current relay log file
    * Current relay log position

If you want to see information about an offline server, this utility
can be used to see the same information. It works by starting the
server in a read-only mode. You must specify the :option:`--basedir`,
:option:`--datadir`, and :option:`--start` options to enable this
feature. This is so that an offline server is not started accidentally.
Note: Be sure to consider the ramifications of starting a server on the
error and similar logs. It is best to save this information prior
to running this utility on an offline server.

To specify how to display output, use one of the following values
with the :option:`--format` option:

**GRID** (default)
  Display output in grid or table format like that of the **mysql** monitor.

**CSV**
  Display output in comma-separated values format.

**TAB**
  Display output in tab-separated format.

**VERTICAL**
  Display output in single-column format like that of the ``\G`` command
  for the **mysql** monitor.

To turn off the headers for CSV or TAB display format, specify
the :option:`--no-headers` option.

You can also see the common default settings read from the machine's local
configuration file. This option reads the configuration file on the machine
that the utility is run from, not the servers to which the :option:`--server`
option specifies.

You can also run the utility against several servers by specifying the
:option:`--server` option multiple times. In this case, the utility will
attempt to connect to each server and read the information.

You can also see the MySQL servers running on the local machine by using the
:option:`--show-servers` option. This will show all of the servers with their
process id and data directory (on Windows, only the process id and port is
shown).

OPTIONS
-------

**mysqlserverinfo** accepts the following command-line options:

.. option:: --help

   Display a help message and exit.

.. option:: --basedir=<basedir>

   The base directory for the server.
  
.. option:: --datadir=<datadir>

   The data directory for the server.

.. option:: --format=<format>, -f<format>

   Specify the output display format. Permitted format values are
   GRID, CSV, TAB, and VERTICAL. The default is GRID.

.. option:: --no-headers, -h

   Do not display column headers. This option applies only for CSV and TAB
   output.
   
.. option:: --port-range

   The port range to use for finding running servers in the form start:end.
   Applies only to Windows and is ignored if :option:`--show-servers` is not
   specified. Default is 3306:3333.

.. option:: --server=<server>

   Connection information for the server in the format:
   <user>[:<passwd>]@<host>[:<port>][:<socket>]
   Use this option multiple times
   to see information for multiple servers.

.. option:: --show-defaults

   Display default settings for mysqld from the local configuration file.
   
.. option:: --show-servers

   Display running servers on the local host.

.. option:: --start, -s

   Start server in read-only mode if offline.

.. option:: --verbose, -v

   Specify how much information to display. Use this option
   multiple times to increase the amount of information.  For example, -v =
   verbose, -vv = more verbose, -vvv = debug.

.. option:: --version

   Display version information and exit.

.. _mysqlserverinfo-notes:

NOTES
-----

The :option:`--show-defaults` option, it applies to the machine the utility is
run from.


EXAMPLES
--------

To display the server information for the local server and the settings for
mysqld in the configuration file with the output in a vertical list, use this
command::

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
