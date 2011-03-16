.. `mysqldiff`:

#######################################################################
``mysqldiff`` - Identify differences among database objects
#######################################################################

SYNOPSIS
--------

::

  mysqldiff --server1=<user>[<passwd>]@<host>:[<port>][:<socket>]
            [ --server2=<user>[<passwd>]@<host>:[<port>][:<socket>] |
              --help | --version | --verbose | --force --width=<width> |
              --quiet | [|--unified|--context|--differ]
              [<db1:db2> [<db1:db2>*] |
               <db1.obj1:db2.obj2> [<db1.obj1:db2.obj2>*]]

DESCRIPTION
-----------

This utility is used to read the definitions of objects and compare them using
a diff-like method to determine if two objects are the same. The user may
specify any combination of either a database and object pair in the form
database1.object1:database2.object2 or a database pair in the form
database1:database2 as arguments. If a database pair is specified, all of the
objects in database1 will be compared to those in database2. Any objects not
appearing in either database will produce an error.

Additionally, the diff may be run against either a single server for comparing
two databases of different names on the same server by specifying only the
:option:`--server1` option. The user can also connect to another server by
specifying the :option:`--server2` option. In this case, the database or
database object pair align such that database1 (or database1.object1) are taken
from server1 and database2 (or database2.object2) are taken from server2.

You can change the display format of the diff output using one of the
following formats:

**unified** (default)
  print unified format output

**context**
  print context format output

**differ**
  print differ-style format output

The utility stops on the first occurance of either missing objects or when an
object does not match. The user can override this behavior by specifying the
:option:`--force` option will will attempt to compare all objects listed as
arguments.

You must provide login information such as user, host, password, etc. for a
user that has the appropriate rights to access all objects in the operation.

OPTIONS
-------

.. option:: --version

   show version number and exit

.. option:: --help

   show the help page

.. option:: --server1 <source>

   connection information for the first server in the form:
   <user>:<password>@<host>:<port>:<socket>

.. option:: --server2 <source>

   connection information for the second server in the form:
   <user>:<password>@<host>:<port>:<socket>

.. option:: --verbose, -v

   control how much information is displayed. For example, -v =
   verbose, -vv = more verbose, -vvv = debug

.. option:: --unified, -u

   Display the differences in unified format (default)
   
.. option:: --context, -c

   Display the differences in context format
   
.. option:: --differ, -d

   Display the differences in differ-style format
   
.. option:: --force

   Do not halt at the first difference found. Process all objects.
   
.. option:: --quiet

   Do not print anything. Return only success or fail as exit code.

NOTES
-----

The login user must have the appropriate permissions to read all databases
and tables listed.

This utility currently compares the full CREATE statement for the objects.
Future versions will have additional features to produce more detailed
comparisons that can generate appropriate ALTER statements and have the
capability to ignore naming differences.

EXAMPLES
--------

To scan all of the tables in the employees database to see the possible
redundant and duplicate indexes as well as the DROP statements for the indexes,
use this command::

    $ mysqldiff --server1=root@localhost employees:emp1 
    # server1 on localhost: ... connected.
    WARNING: Objects in server1:employees but not in server2:emp1:
      EVENT: e1
    Diff failed. One or more differences found.
    
    $ mysqldiff --server1=root@localhost \
               employees.t1:emp1.t1 employees.t3:emp1.t3
    # server1 on localhost: ... connected.
    # Comparing employees.t1 to emp1.t1                                [PASS]
    # server1 on localhost: ... connected.
    # Comparing employees.t3 to emp1.t3                                [PASS]
    Success. All objects are the same.

    $ mysqldiff --server1=root@localhost \
             employees.salaries:emp1.salaries --differ
    # server1 on localhost: ... connected.
    # Comparing employees.salaries to emp1.salaries                    [FAIL]
    # Object definitions are not the same:
      CREATE TABLE `salaries` (
        `emp_no` int(11) NOT NULL,
        `salary` int(11) NOT NULL,
        `from_date` date NOT NULL,
        `to_date` date NOT NULL,
        PRIMARY KEY (`emp_no`,`from_date`),
        KEY `emp_no` (`emp_no`)
    - ) ENGINE=InnoDB DEFAULT CHARSET=latin1
    ?           ^^^^^
    + ) ENGINE=MyISAM DEFAULT CHARSET=latin1
    ?          ++ ^^^
    Diff failed. One or more differences found.

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
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
USA
