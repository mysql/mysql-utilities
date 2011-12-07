.. _`mysqlserverinfo`:

#########################################################################
``mysqlserverinfo`` - Display common diagnostic information from a server
#########################################################################

SYNOPSIS
--------

::

 mysqlserverinfo - [ --server=<user>[<passwd>]@<host>:[<port>][:<socket>] |
                   [, --server=<user>[<passwd>]@<host>:[<port>][:<socket>] ] |
                   --format=[|GRID|TAB|CSV|VERTICAL] ] | --no-headers |
                   --show-defaults | [--start --basedir=<base directory> 
                   --datadir=<data directory>] --verbose

DESCRIPTION
-----------

This utility permits a database administrator to view critical information
about a server for use in diagnosing problems. The information displayed
includes the following:

    * server connection information
    * version number of the server
    * data directory path
    * base directory path
    * plugin directory path
    * configuration file location and name
    * current binary log file
    * current binary log position
    * current relay log file
    * current relay log position

If you want to see information about an offline server, this utility can be
used to see the same information. It works by starting the server in a read
only mode. You must specify the :option:`--basedir`, :option:`--datadir`, and
:option:`--start` options to enable this feature. This is so that an offline
server is not started accidentally. Note: be sure to consider ramifications of
starting a server on the error and similar logs. It is best to save this
information prior to running this utility on an offline server.

You also have the choice to view the output in one of the following
formats using the :option:`--format` option.

**GRID**
  Displays output formatted like that of the mysql monitor in a grid
  or table layout.

**CSV**
  Displays the output in a comma-separated list.

**TAB**
  Displays the output in a tab-separated list.

**VERTICAL**
  Displays the output in a single column similar to the ``\G`` option
  for the mysql monitor commands.

You can turn off the headers when using formats CSV and TAB by
specifying the :option:`--no-headers` option.

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

.. option:: --version

   show program's version number and exit

.. option:: --help

    show the program's help and usage

.. option:: --server=<server>

   connection information for the server in the form:
   <user>:<password>@<host>:<port>:<socket> specify this option multiple times
   for seeing the information from additional servers.

.. option:: --format=<format>, -f<format>

   display the output in either GRID (default), TAB, CSV, or VERTICAL format

.. option:: --no-headers, -h

   do not display the column headers - ignored for GRID format

.. option:: --verbose, -v

   control how much information is displayed. For example, -v =
   verbose, -vv = more verbose, -vvv = debug

.. option:: --show-defaults

   display default settings for mysqld from the local configuration file
   
.. option:: --show-servers

   display running servers on the local host
   
.. option:: --port-range

   the port range to use for finding running servers in the form start:end.
   Applies to Windows only and is ignored if :option:`--show-servers` is not
   specified. Default is 3306:3333

.. option:: --start, -s

   start server in read only mode if offline

.. option:: --basedir=<basedir>

   the base directory for the server
  
.. option:: --datadir=<datadir>

   the data directory for the server

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
