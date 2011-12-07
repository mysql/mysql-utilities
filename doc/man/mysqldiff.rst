.. `mysqldiff`:

#######################################################################
``mysqldiff`` - Identify differences among database objects
#######################################################################

SYNOPSIS
--------

::

  mysqldiff --server1=<user>[<passwd>]@<host>:[<port>][:<socket>]
            [ --server2=<user>[<passwd>]@<host>:[<port>][:<socket>] |
              --help | --version | --verbose | --force | --width=<width> |
              --changes-for = [server1|server2] --quiet |
              [--difftype=[--unified|--context|--differ|sql]]
              [<db1:db2> [<db1:db2>*] | --show-reverse |
               <db1.obj1:db2.obj2> [<db1.obj1:db2.obj2>*]]

DESCRIPTION
-----------

This utility is used to read the definitions of objects and compare them using
a diff-like method to determine if two objects are the same. If the objects are
not the same, the differences will be displayed (difference report). The user
may specify any combination of either a database and object pair in the form
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

The utilty will generate the difference of the objects in the form of a
difference report by default. However, you can generate a transformation report
containing SQL statements for transforming the objects for conformity instead.
Use the 'sql' value for the :option:`--difftype` option to produce a listing
that contains the appropriate ALTER commands to conform the object definitions
for the object pairs specified. If a transformation cannot be formed, the
utility reports the diff of the object along with a warning statement. See
important limitations below in the NOTES section.

You can change the display format of the diff output using one of the
following formats:

**unified** (default)
  print unified format output

**context**
  print context format output

**differ**
  print differ-style format output

The :option:`--changes-for` option can be used to control the direction of the
difference (by specifying the object to be transformed) in either the
difference report (default) or the transformation report (designated with the
:option:`--difftype=sql` option). For example, consider the following command.::

  mysqldiff --server1=root@host1 --server2@host2 db1.table1:dbx.table3 \
    --difftype=sql

In this example, db1 exists on host1 and dbx exists on host2 as defined by
position where the database and object to the left of the colon are located on
--server1 and the database and object on the right is located on --server2.

  * --changes-for=server1 - The object definition on server1 is the object to be
    transformed and is used to produce the difference or transformation
    compared to the definition on server2. The output therefore will be the
    transformation needed to make the object on server1 like the object on
    server2.
  * --changes-for=server2 - The object definition on server2 is the object to be
    transformed and is used to produce the difference or transformation
    compared to the definition on server1. The output therefore will be the
    transformation needed to make the object on server2 like the object on
    server1.

The default direction is server1. 

For difference type SQL, you can also see the reverse transformation by
specifying the :option:`--show-reverse` option.
      
The utility stops on the first occurance of either missing objects or when an
object does not match. The user can override this behavior by specifying the
:option:`--force` option will will attempt to compare all objects listed as
arguments.

You must provide login information such as user, host, password, etc. for a
user that has the appropriate rights to access all objects in the operation.

OPTIONS
-------

.. option:: --help

   show the help page

.. option:: --changes-for=DIRECTION

   specify the server to show transformations to match the other server. For
   example, to see the transformation for transforming server1 to match
   server2, use --changes-for=server1. Valid values are 'server1' or
   'server2'. The default is 'server1' 

.. option:: --difftype=<difftype>, -d<difftype>

   display differences in context format either unified,
   context, differ, or sql (default: unified)
   
.. option:: --force

   do not halt at the first difference found. Process all objects
   
.. option:: --quiet

   do not print anything. Return only success or fail as exit code

.. option:: --server1=<source>

   connection information for the first server in the form:
   <user>:<password>@<host>:<port>:<socket>

.. option:: --server2=<source>

   connection information for the second server in the form:
   <user>:<password>@<host>:<port>:<socket>
   
.. option:: --show-reverse

   produce a transformation report containing the SQL statements to conform the
   object definitions specified in reverse. For example if --changes-for is set
   to server1, also generate the transformation for server2. Note: the reverse
   changes are annotated and marked as comments

.. option:: --verbose, -v

   control how much information is displayed. For example, -v =
   verbose, -vv = more verbose, -vvv = debug

.. option:: --version

   show version number and exit

.. option:: --width

   change the display width of the test report


NOTES
-----

The login user must have the appropriate permissions to read all databases
and tables listed.

This utility currently compares the full CREATE statement for the objects.
Future versions will have additional features to produce more detailed
comparisons that can generate appropriate ALTER statements and have the
capability to ignore naming differences.

The SQL transformation feature has the following known limitations.

* Does not support tables with partition settings that change. When a table
  with partition changes is encountered, the utility will generate the ALTER
  TABLE statements for all other changes but will print a warning when
  partition changes are detected.
  
* If the transformation detects table options in the source table (specified
  with the :option:`--changes-for` option) that are not changed or do not exist
  in the target table, a warning is issued.
  
* Rename for events is not supported. This is because mysqldiff compares
  objects by name. In this case, the event will be identified as needing to
  be added or a DROP EVENT statement will be generated depending on the
  direction of the diff.

* Changes in the definer clause for events is not supported.

* MySQL Cluster-specific SQL extensions are not supported.

EXAMPLES
--------

To scan all of the tables in the employees database to see the possible
redundant and duplicate indexes as well as the DROP statements for the indexes,
use this command::

    $ mysqldiff --server1=root@localhost employees:emp1 
    # server1 on localhost: ... connected.
    WARNING: Objects in server1:employees but not in server2:emp1:
      EVENT: e1
    Compare failed. One or more differences found.
    
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
    Compare failed. One or more differences found.
    
The following are examples of generating a transformation report given the
following object definitions.

Host1:
CREATE TABLE db1.table1 (num int, misc char(30));

Host2:
CREATE TABLE dbx.table3 (num int, notes char(30), misc char(55));

To generate a set of SQL statements to transform the definition of db1.table1 to
dbx.table3, use this command:

    $ mysqldiff --server1=root@host1 --server2@host2 db1.table1:dbx.table3 \
          --changes-for=server1 --difftype=sql
    # server1 on host1: ... connected.
    # server2 on host2: ... connected.
    # Comparing db1.table1 to dbx.table3                               [FAIL]
    # Transformation statments:

    ALTER TABLE db1.table1 
      ADD COLUMN notes char(30) AFTER a, 
      CHANGE COLUMN misc misc char(55);

    Compare failed. One or more differences found.

To generate a set of SQL statements to transform the definition of dbx.table3 to
db1.table1, use this command:

    $ mysqldiff --server1=root@host1 --server2@host2 db1.table1:dbx.table3 \
          --changes-for=server2 --difftype=sql
    # server1 on host1: ... connected.
    # server2 on host2: ... connected.
    # Comparing db1.table1 to dbx.table3                               [FAIL]
    # Transformation statments:

    ALTER TABLE dbx.table3 
      DROP COLUMN notes, 
      CHANGE COLUMN misc misc char(30);

    Compare failed. One or more differences found.

To generate a set of SQL statements to transform the definitions of dbx.table3
and db1.table1 in both directions, use this command:

    $ mysqldiff --server1=root@host1 --server2@host2 db1.table1:dbx.table3 \
          --show-reverse --difftype=sql
    # server1 on host1: ... connected.
    # server2 on host2: ... connected.
    # Comparing db1.table1 to dbx.table3                               [FAIL]
    # Transformation statments:

    # --destination=server1:
    ALTER TABLE db1.table1 
      ADD COLUMN notes char(30) AFTER a, 
      CHANGE COLUMN misc misc char(55);
    
    # --destination=server2:
    # ALTER TABLE dbx.table3 
    #   DROP COLUMN notes, 
    #   CHANGE COLUMN misc misc char(30);

    Compare failed. One or more differences found.


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
