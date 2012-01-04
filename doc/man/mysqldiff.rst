.. `mysqldiff`:

###########################################################
``mysqldiff`` - Identify Differences Among Database Objects
###########################################################

SYNOPSIS
--------

::

  mysqldiff --server1=<user>[:<passwd>]@<host>[:<port>][:<socket>]
              [ --server2=<user>[:<passwd>]@<host>[:<port>][:<socket>] |
              --help | --version | --verbose | --force | --width=<width> |
              --changes-for=[server1|server2] --quiet |
              [--difftype=[unified|context|differ|sql]]
              [<db1:db2> [<db1:db2>*] | --show-reverse |
               <db1.obj1:db2.obj2> [<db1.obj1:db2.obj2>*]]

DESCRIPTION
-----------

This utility reads the definitions of objects and compares them using a
diff-like method to determine whether they are the same. If the objects are
not the same, the differences are displayed. The user may specify any
combination of either a database and object pair in the form
database1.object1:database2.object2 or a database pair in the form
database1:database2 as arguments. If a database pair is specified, all of
the objects in database1 are compared to those in database2. Any objects not
appearing in either database produce an error.

The diff may be run against a single server for comparing two
databases of different names on the same server by specifying only the
:option:`--server1` option. Alternatively, you can also connect to
another server by specifying the :option:`--server2` option. In this
case, the first object to compare is taken from server1 and the second
from server2.

By default, the utilty generates object differences in the form of
a difference report. However, you can generate a transformation
report containing SQL statements for transforming the objects for
conformity instead.  Use the 'sql' value for the :option:`--difftype`
option to produce a listing that contains the appropriate ALTER
commands to conform the object definitions for the object pairs
specified. If a transformation cannot be formed, the utility reports
the diff of the object along with a warning statement. See important
limitations in the NOTES section.

To specify how to display diff-style output, use one of the following
values with the :option:`--difftype` option:

**unified** (default)
  Display unified format output.

**context**
  Display context format output.

**differ**
  Display differ-style format output.

**sql**
  Display SQL transformation statement output.

The :option:`--changes-for` option controls the direction of the
difference (by specifying the object to be transformed) in either the
difference report (default) or the transformation report (designated with the
:option:`--difftype=sql` option). Consider the following command::

  mysqldiff --server1=root@host1 --server2=root@host2 --difftype=sql \
    db1.table1:dbx.table3

In this example, db1 exists on host1 and dbx exists on host2 as
defined by position where the database and object to the left of
the colon are located on the server designated by :option:`--server1`
and the database and object on the right is located on the server
designated by :option:`--server2`.

  * :option:`--changes-for=server1`: The object definition on server1 is the object to be
    transformed and is used to produce the difference or transformation
    compared to the definition on server2. The output therefore is the
    transformation needed to make the object on server1 like the object on
    server2.
  * :option:`--changes-for=server2`: The object definition on server2 is the object to be
    transformed and is used to produce the difference or transformation
    compared to the definition on server1. The output therefore is the
    transformation needed to make the object on server2 like the object on
    server1.

The default direction is server1. 

For difference type SQL, you can also see the reverse transformation by
specifying the :option:`--show-reverse` option.
      
The utility stops on the first occurrence of missing objects or when an
object does not match. To override this behavior, specify the
:option:`--force` option, which causes the utility to attempt to compare
all objects listed as arguments.

You must provide connection parameters (user, host, password, and
so forth), for an account that has the appropriate privileges to
access all objects in the operation.

OPTIONS
-------

**mysqldiff** accepts the following command-line options:

.. option:: --help

   Display a help message and exit.

.. option:: --changes-for=DIRECTION

   Specify the server to show transformations to match the other server. For
   example, to see the transformation for transforming server1 to match
   server2, use --changes-for=server1. Valid values are 'server1' or
   'server2'. The default is 'server1'.

.. option:: --difftype=<difftype>, -d<difftype>

   Specify the difference display format. Permitted format values are unified,
   context, differ, and sql. The default is unified.
   
.. option:: --force

   Do not halt at the first difference found. Process all objects.
   
.. option:: --quiet

   Do not print anything. Return only an exit code of success or failure.

.. option:: --server1=<source>

   Connection information for the first server in the format:
   <user>[:<passwd>]@<host>[:<port>][:<socket>]

.. option:: --server2=<source>

   Connection information for the second server in the format:
   <user>[:<passwd>]@<host>[:<port>][:<socket>]
   
.. option:: --show-reverse

   Produce a transformation report containing the SQL statements to conform the
   object definitions specified in reverse. For example, if
   :option:`--changes-for` is set
   to server1, also generate the transformation for server2. Note: The reverse
   changes are annotated and marked as comments.

.. option:: --verbose, -v

   Specify how much information to display. Use this option
   multiple times to increase the amount of information.  For example, -v =
   verbose, -vv = more verbose, -vvv = debug.

.. option:: --version

   Display version information and exit.

.. option:: --width

   Change the display width of the test report.


NOTES
-----

The login user must have the appropriate read permissions for all objects to
be compared.

The SQL transformation feature has the following known limitations:

* When tables with partition differences are encountered, the utility
  generates the **ALTER TABLE** statements for all other changes but
  prints a warning and the partition differences are omitted.
  
* If the transformation detects table options in the source table (specified
  with the :option:`--changes-for` option) that are not changed or do not exist
  in the target table, a warning is issued.
  
* Rename for events is not supported. This is because **mysqldiff** compares
  objects by name. In this case, depending on the direction of the diff, the
  event is identified as needing to be added or a **DROP EVENT** statement
  is generated.

* Changes in the definer clause for events are not supported.

* MySQL Cluster-specific SQL extensions are not supported.

EXAMPLES
--------

To scan all tables in the employees database to see the possible redundant
and duplicate indexes as well as the **DROP** statements for the indexes,
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
    
The following examples show how to generate a transformation report. Assume
the following object definitions:

Host1:
CREATE TABLE db1.table1 (num int, misc char(30));

Host2:
CREATE TABLE dbx.table3 (num int, notes char(30), misc char(55));

To generate a set of SQL statements to transform the definition of db1.table1 to
dbx.table3, use this command::

    $ mysqldiff --server1=root@host1 --server2=root@host2 \
          --changes-for=server1 --difftype=sql \
          db1.table1:dbx.table3
    # server1 on host1: ... connected.
    # server2 on host2: ... connected.
    # Comparing db1.table1 to dbx.table3                               [FAIL]
    # Transformation statments:

    ALTER TABLE db1.table1 
      ADD COLUMN notes char(30) AFTER a, 
      CHANGE COLUMN misc misc char(55);

    Compare failed. One or more differences found.

To generate a set of SQL statements to transform the definition of dbx.table3 to
db1.table1, use this command::

    $ mysqldiff --server1=root@host1 --server2=root@host2 \
          --changes-for=server2 --difftype=sql \
          db1.table1:dbx.table3
    # server1 on host1: ... connected.
    # server2 on host2: ... connected.
    # Comparing db1.table1 to dbx.table3                               [FAIL]
    # Transformation statments:

    ALTER TABLE dbx.table3 
      DROP COLUMN notes, 
      CHANGE COLUMN misc misc char(30);

    Compare failed. One or more differences found.

To generate a set of SQL statements to transform the definitions of dbx.table3
and db1.table1 in both directions, use this command::

    $ mysqldiff --server1=root@host1 --server2=root@host2 \
          --show-reverse --difftype=sql \
          db1.table1:dbx.table3
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
