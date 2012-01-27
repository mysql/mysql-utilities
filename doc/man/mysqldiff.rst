.. `mysqldiff`:

###########################################################
``mysqldiff`` - Identify Differences Among Database Objects
###########################################################

SYNOPSIS
--------

::

 mysqldiff [options] {db1[:db1] | db1.obj1[:db2.obj2]} ...

DESCRIPTION
-----------

This utility reads the definitions of objects and compares them using a
diff-like method to determine whether they are the same. The utility displays
the differences for objects that are
not the same.

Use the notation db1:db2 to name two databases to compare, or, alternatively
just db1 to compare two databases with the same name.  The latter case is a
convenience notation for comparing same-named databases on different
servers.

The comparison may be run against two databases of different names on a
single server by specifying only the :option:`--server1` option. The user
can also connect to another server by specifying the :option:`--server2`
option. In this case, db1 is taken from server1 and db2 from server2.

When a database pair is specified, all objects in one database are
compared to the corresponding objects in the other. Any objects
not appearing in either database produce an error.

To compare a specific pair of objects, add an object name to each database
name in *db.obj* format. For example, use ``db1.obj1:db2.obj2`` to compare two
named objects, or db1.obj1 to compare an object with the same name in
databases with the same name. It is not legal to mix a database name with an
object name. For example, ``db1.obj1:db2`` and ``db1:db2.obj2`` are illegal.

The comparison may be run against a single server for comparing two
databases of different names on the same server by specifying only the
:option:`--server1` option. Alternatively, you can also connect to
another server by specifying the :option:`--server2` option. In this
case, the first object to compare is taken from server1 and the second
from server2.

By default, the utilty generates object differences as
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

The leftmost database (``db1``) exists on the server 
designated by the :option:`--server1` option (``host1``).
The rightmost database (``dbx``) exists on the server 
designated by the :option:`--server2` option (``host2``).

* :option:`--changes-for=server1`: Produce output that shows how to make the
  definitions of objects on ``server1`` like the definitions of the
  corresponding objects on ``server2``.
* :option:`--changes-for=server2`: Produce output that shows how to make the
  definitions of objects on ``server2`` like the definitions of the
  corresponding objects on ``server1``.

The default direction is ``server1``. 

For **sql** difference format, you can also see the reverse transformation
by specifying the :option:`--show-reverse` option.

The utility stops on the first occurrence of missing objects or when an
object does not match. To override this behavior, specify the
:option:`--force` option to cause the utility to attempt to compare all
objects listed as arguments.

OPTIONS
-------

:command:`mysqldiff` accepts the following command-line options:

.. option:: --help

   Display a help message and exit.

.. option:: --changes-for=<direction>

   Specify the server to show transformations to match the other server. For
   example, to see the transformation for transforming object definitions on
   server1 to match the corresponding definitions on server2, use
   :option:`--changes-for=server1`. Permitted values are **server1** and
   **server2**. The default is **server1**.

.. option:: --difftype=<difftype>, -d<difftype>

   Specify the difference display format. Permitted format values are
   **unified**, **context**, **differ**, and **sql**. The default is
   **unified**.
   
.. option:: --force

   Do not halt at the first difference found. Process all objects to find
   all differences.
   
.. option:: --quiet, -q

   Do not print anything. Return only an exit code of success or failure.

.. option:: --server1=<source>

   Connection information for the first server in
   <*user*>[:<*passwd*>]@<*host*>[:<*port*>][:<*socket*>] format.

.. option:: --server2=<source>

   Connection information for the second server in
   <*user*>[:<*passwd*>]@<*host*>[:<*port*>][:<*socket*>] format.
   
.. option:: --show-reverse

   Produce a transformation report containing the SQL statements to conform the
   object definitions specified in reverse. For example, if
   :option:`--changes-for` is set
   to server1, also generate the transformation for server2. Note: The reverse
   changes are annotated and marked as comments.

.. option:: --verbose, -v

   Specify how much information to display. Use this option
   multiple times to increase the amount of information.  For example,
   :option:`-v` = verbose, :option:`-vv` = more verbose, :option:`-vvv` =
   debug.

.. option:: --version

   Display version information and exit.

.. option:: --width=<number>

   Change the display width of the test report.
   The default is 75 characters.


NOTES
-----

You must provide connection parameters (user, host, password, and
so forth) for an account that has the appropriate privileges to
access all objects to be compared.

The SQL transformation feature has these known limitations:

* When tables with partition differences are encountered, the utility
  generates the **ALTER TABLE** statement for all other changes but
  prints a warning and omits the partition differences.
  
* If the transformation detects table options in the source table (specified
  with the :option:`--changes-for` option) that are not changed or do not exist
  in the target table, the utility generates the **ALTER TABLE** statement for
  all other changes but prints a warning and omits the table option
  differences.
  
* Rename for events is not supported. This is because :command:`mysqldiff` compares
  objects by name. In this case, depending on the direction of the diff, the
  event is identified as needing to be added or a **DROP EVENT** statement
  is generated.

* Changes in the definer clause for events are not supported.

* SQL extensions specific to MySQL Cluster are not supported.

For the :option:`--difftype` option, the permitted values are not case
sensitive. In addition, values may be specified as any unambiguous prefix of
a valid value. For example, :option:`--difftype=d` specifies the differ
type. An error occurs if a prefix matches more than one valid value.

EXAMPLES
--------

To compare the ``employees`` and ``emp`` databases on the local server,
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

Host1::

   CREATE TABLE db1.table1 (num int, misc char(30));

Host2::

   CREATE TABLE dbx.table3 (num int, notes char(30), misc char(55));

To generate a set of SQL statements that transform the definition of
``db1.table1`` to ``dbx.table3``, use this command::

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

To generate a set of SQL statements that transform the definition of
``dbx.table3`` to ``db1.table1``, use this command::

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

To generate a set of SQL statements that transform the definitions of
``dbx.table3`` and ``db1.table1`` in both directions, use this command::

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
