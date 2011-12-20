
.. _`mysqldiskusage`:

#####################################################################
``mysqldiskusage`` - Show disk usage for one or more databases
#####################################################################

SYNOPSIS
--------

::

 mysqldiskusage --server=<user>[<passwd>]@<host>:[<port>][:<socket>]
             [--help | --no-headers | --version | --verbose |
             --binlog | --relaylog | --logs | --empty | --all 
             --format=[SQL|S|GRID|G|TAB|T|CSV|C|VERTICAL|V]
             [| <db>]

DESCRIPTION
-----------

This utility permits a database administrator to see the disk space usage
for one or more databases in either CSV, TAB, GRID, or VERTICAL format.
The utility will also allow the user to examine the disk usage for the
binary logs, slow, error, and general log, and InnoDB tablespace usage. The
default is to show only the database disk space usage.

If no databases are listed, the utility shows the disk space usage for all
databases.

You also have the choice to view the output in one of the following formats
using the :option:`--format` option.

**GRID**
  Displays output formatted like that of the mysql monitor in a grid
  or table layout. This is the default format.

**CSV**
  Displays the output in a comma-separated list.

**TAB**
  Displays the output in a tab-separated list.

**VERTICAL**
  Displays the output in a single column similar to the \G option for
  the mysql monitor commands.

You can turn off the headers when using formats CSV and TAB by
specifying the :option:`--no-headers` option.

You must provide login information such as user, host, password, etc. for a
user that has the appropriate rights to access all objects in the operation.
See :ref:`mysqldiskusage-notes` below for more details.

OPTIONS
-------

.. option:: --version

   Display version information and exit.

.. option:: --help

   Display a help message and exit.

.. option:: --server=<server>

   connection information for the server in the form:
   <user>:<password>@<host>:<port>:<socket>

.. option:: --format=<format>, -f<format>

   display the output in either GRID (default), TAB, CSV,
   or VERTICAL format

.. option::  --no-headers, -h

   do not display the column headers - ignored for grid format

.. option:: --verbose, -v

   control how much information is displayed. For example, -v =
   verbose, -vv = more verbose, -vvv = debug

.. option::  --binlog, -b

    include binary log usage

.. option::  --relaylog, -r

    include relay log usage

.. option::  --logs, -l

    include general, error, and slow log usage
    
.. option::  --InnoDB, -i

    include InnoDB tablespace usage

.. option::  --empty, -m

    include empty databases

.. option::  --all, -a

    show all usage including empty databases
    
.. option:: --quiet

    suppress informational messages

.. _`mysqldiskusage-notes`:

NOTES
-----

The login user must have the appropriate permissions to create new
objects, read the old database, access (read) the mysql database, and
grant privileges.

The user may also require read access to the data directory and InnoDB home
directory. If the user does not have access to these areas, the data displayed
will be limited to information from the system tables and therefore should be
considered an estimate. This is because the utility will not be able to include
.frm and related miscellaneous files in the calculations.

If the user has read access to the data directory, disk space usage shown will
include the sum of all storage engine specific files such as the .MYI and
.MYD files for MyISAM and similarly include the tablespace files for InnoDB.

EXAMPLES
--------

To show only the disk space usage for the employees and test databases in
ggrid format, use this command::

    $ mysqldiskusage --server=root@localhost db1 db2 db3
    # Source on localhost: ... connected.
    # Database totals:
    +------------+--------------+
    | db_name    |       total  |
    +------------+--------------+
    | employees  | 205,979,648  |
    | test       |       4,096  |
    +------------+--------------+
    
    Total database disk usage = 205,983,744 bytes or 196.00 MB
    
    #...done.

To see all disk usage for the server in CSV format, use this command::

    $ mysqldiskusage --server=root@localhost --format=csv -a -vv
    # Source on localhost: ... connected.
    # Database totals:
    db_name,db_dir_size,data_size,misc_files,total
    test1,0,0,0,0
    db3,0,0,0,0
    db2,0,0,0,0
    db1,0,0,0,0
    backup_test,19410,1117,18293,19410
    employees,242519463,205979648,242519463,448499111
    mysql,867211,657669,191720,849389
    t1,9849,1024,8825,9849
    test,56162,4096,52066,56162
    util_test_a,19625,2048,17577,19625
    util_test_b,17347,0,17347,17347
    util_test_c,19623,2048,17575,19623
    
    Total database disk usage = 449,490,516 bytes or 428.00 MB
    
    # Log information.
    # The general_log is turned off on the server.
    # The slow_query_log is turned off on the server.
    
    # binary log information:
    Current binary log file = ./mysql-bin.000076
    log_file,size
    /data/mysql-bin.000076,125
    /data/mysql-bin.000077,125
    /data/mysql-bin.000078,556
    /data/mysql-bin.000079,168398223
    /data/mysql-bin.index,76
    
    Total size of binary logs = 168,399,105 bytes or 160.00 MB
    
    # Server is not an active slave - no relay log information.
    # InnoDB tablespace information:
    InnoDB_file,size,type,specificaton
    /data/ib_logfile0,5242880,log file,
    /data/ib_logfile1,5242880,log file,
    /data/ibdata1,220200960,shared tablespace,ibdata1:210M
    /data/ibdata2,10485760,shared tablespace,ibdata2:10M:autoextend
    /data/employees/departments.ibd,114688,file tablespace,
    /data/employees/dept_emp.ibd,30408704,file tablespace,
    /data/employees/dept_manager.ibd,131072,file tablespace,
    /data/employees/employees.ibd,23068672,file tablespace,
    /data/employees/salaries.ibd,146800640,file tablespace,
    /data/employees/titles.ibd,41943040,file tablespace,
    
    Total size of InnoDB files = 494,125,056 bytes or 471.00 MB
    
    #...done.

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
