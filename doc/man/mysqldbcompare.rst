.. `mysqldbcompare`:

#################################################################
``mysqldbcompare`` - Check Two Databases and Identify Differences
#################################################################

SYNOPSIS
--------

::

  mysqldbcompare --server1=<user>[:<passwd>]@<host>[:<port>][:<socket>]
              [ --server2=<user>[:<passwd>]@<host>[:<port>][:<socket>] |
              --help | --version | --verbose | --run-all-tests | --quiet |
              --format=<format> | --width=<width> |
              --changes-for=[server1|server2] | 
              [--difftype=[unified|context|differ|sql]]
              [<db1:db2> | <db> [<db1:db2>* | db*] [--skip-object-compare |
              --skip-row-count | --skip-diff | --skip-data-check]

DESCRIPTION
-----------

This utility compares the objects and data from two databases to
find differences. It identifies objects having different definitions
in the two databases and presents them in a diff-style format of
choice. Differences in the data are shown using a similar diff-style
format. Changed or missing rows are shown in a standard format of
GRID, CSV, TAB, or VERTICAL.

Those objects considered in the database include tables, views, triggers,
procedures, functions, and events. A count of each object type can be shown
with the :option:`-vv` option.

The check is performed using a series of steps called tests. The utility is
designed to stop on the first failed test but the user may specify the
:option:`--run-all-tests` option which causes the utility to run
all tests regardless of their end state.

Note: Using :option:`--run-all-tests` may produce expected cascade failures.
For example, if the row counts differ among two tables being compared, the data
consistency will also fail.

The tests include the following:

1) Check database definitions
2) Check existance of objects in both databases
3) Compare the definitions of objects
4) Check row count for tables
5) Check data consistency for tables

(1) A database existance precondition check ensures that both databases exist.
If they do not, no further processing is possible and the
:option:`--run-all-tests` option is ignored.

(2) The test for objects in both databases identifies those objects missing
from one or another database. The following tests (3)-(5) apply only to those
objects that appear in both databases.

(3) The definitions (the CREATE statements) are compared and differences are
presented. In the case of name differences only, this test fails (since the
statements are not the same) but the user may elect that this is normal and
therefore may want to run the utility again with the :option:`--skip-diff`
option to skip this test.

(4) The row count check ensures that both tables have the same
number of rows. Note that this does not ensure the table data is
consistent. It is merely a cursory check to indicate possible missing
rows in one or the other table being compared. The data consistency
check (5) identifies the missing rows.

(5) The data consistency check identifies both changed rows as well as
missing rows from one or another of the tables in the databases. Changed rows
are displayed as a diff-style report with the format chosen (default is GRID)
and missing rows are also displayed using the format chosen.

Each test completes with one of the following states:

**pass**
  The test succeeded.

**FAIL**
  The test failed. Errors are displayed following the test state line.

**SKIP**
  The test was skipped due to a missing prerequisite or a skip option.

**WARN**
  The test encountered an unusual but not fatal error.

**-**
  The test is not applicable to this object.

Several of the tests may be skipped with a --skip-% option. For example, the
user can skip the object compare step if there are known missing objects among
the databases by using the :option:`--skip-object-compare` option, skip the
definition comparison if there are known differences in the definitions by
using the :option:`--skip-diff` option, skip the row count step using the
:option:`--skip-row-count` option, and skip the data check step using the
:option:`--skip-data-check` options. A user may want to use these options to
run only one of the tests. This may be helpful when working to bring two
databases into synchronization to avoid running all of the tests repeatedly
during the process.

To specify the databases to compare, use the notation db1:db2.
Additionally, the check may be run against either a single server for comparing
two databases of different names on the same server by specifying only the
:option:`--server1` option. The user can also connect to another server by
specifying the :option:`--server2` option. In this case, the database or
database object pair align such that database1 (or database1.object1) are taken
from server1 and database2 (or database2.object2) are taken from server2.

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

To specify how to display changed or missing row output, use one of
the following values with the :option:`--format` option:

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

The :option:`--changes-for` option controls the direction of the
difference (by specifying the object to be transformed) in either the
difference report (default) or the transformation report (designated with the
:option:`--difftype=sql` option). Consider the following command::

  mysqldbcompare --server1=root@host1 --server2=root@host2 --difftype=sql \
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

You must provide connection parameters (user, host, password, and
so forth) for an account that has the appropriate privileges to
access all objects in the operation.

If the utility is to be run on a server that has binary logging
enabled, and you do not want the comparison steps logged, use the
:option:`--disable-binary-logging` option.

OPTIONS
-------

**mysqldbcompare** accepts the following command-line options:

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
   
.. option:: --disable-binary-logging

   Turn binary logging off during operation if enabled (SQL_LOG_BIN=1).
   Prevents comparison operations from being written to the binary log. Note:
   Requires the SUPER privilege.

.. option:: --format=<format>, -f<format>

   Specify the missing-row display format. Permitted format values are
   GRID, CSV, TAB, and VERTICAL. The default is GRID.
   
.. option:: --quiet

   Do not print anything. Return only an exit code of success or failure.

.. option:: --run-all-tests, -a

   Do not halt at the first difference found. Process all objects.
   
.. option:: --server1=<source>

   Connection information for the first server in the format:
   <user>[:<passwd>]@<host>[:<port>][:<socket>]

.. option:: --server2=<source>

   Connection information for the second server in the format:
   <user>[:<passwd>]@<host>[:<port>][:<socket>]

.. option:: --show-reverse

   Produce a transformation report containing the SQL statements to conform the
   object definitions specified in reverse. For example, if --changes-for is set
   to server1, also generate the transformation for server2. Note: The reverse
   changes are annotated and marked as comments.

.. option:: --skip-data-check

   Skip the data consistency check.

.. option:: --skip-diff

   Skip the object diff check.

.. option:: --skip-object-compare

   Skip the object comparison check.

.. option:: --skip-row-count

   Skip the row count check.

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

The login user must have the appropriate permissions to read all databases
and tables listed.


EXAMPLES
--------

To scan all of the tables in the employees database to see the possible
redundant and duplicate indexes as well as the DROP statements for the indexes,
use this command::

    $ mysqldbcompare --server1=root@localhost emp1:emp2 --run-all-tests
    # server1 on localhost: ... connected.
    # Checking databases emp1 on server1 and emp2 on server2
    
    WARNING: Objects in server2:emp2 but not in server1:emp1:
      TRIGGER: trg
    PROCEDURE: p1
        TABLE: t1
         VIEW: v1
    
                                                        Defn    Row     Data
    Type      Object Name                               Diff    Count   Check
    ---------------------------------------------------------------------------
    FUNCTION  f1                                        pass    -       -       
    TABLE     departments                               pass    pass    FAIL    
    
    Data differences found among rows:
    --- emp1.departments 
    +++ emp2.departments 
    @@ -1,4 +1,4 @@
     *************************       1. row *************************
        dept_no: d002
    - dept_name: dunno
    + dept_name: Finance
     1 rows.
    
    Rows in emp1.departments not in emp2.departments
    *************************       1. row *************************
       dept_no: d008
     dept_name: Research
    1 rows.
    
    Rows in emp2.departments not in emp1.departments
    *************************       1. row *************************
       dept_no: d100
     dept_name: stupid
    1 rows.
    
    TABLE     dept_manager                              pass    pass    pass    
    
    Database consistency check failed.
    
    # ...done

    Given : two databases with the same table layout. Data for each table
            contains:
  
          mysql> select * from db1.t1;
          +---+---------------+
          | a | b             |
          +---+---------------+
          | 1 | Test 789      |
          | 2 | Test 456      |
          | 3 | Test 123      |
          | 4 | New row - db1 |
          +---+---------------+
          4 rows in set (0.00 sec)
          
          mysql> select * from db2.t1;
          +---+---------------+
          | a | b             |
          +---+---------------+
          | 1 | Test 123      |
          | 2 | Test 456      |
          | 3 | Test 789      |
          | 5 | New row - db2 |
          +---+---------------+
          4 rows in set (0.00 sec)
  
    To generate the SQL commands for data transformations to make db1.t1 the
    same as db2.t1, use the --changes-for=server1 options. We must also include
    the -a option to ensure the data consistency test is run. The following
    command illustrates the options used and an excerpt from the results
    generated. 
  
    $ mysqldbcompare --server1=root:root@localhost \
        --server2=root:root@localhost db1:db2 --changes-for=server1 -a \
        --difftype=sql
        
    [...]
  
    #                                                   Defn    Row     Data   
    # Type      Object Name                             Diff    Count   Check  
    # ------------------------------------------------------------------------- 
    # TABLE     t1                                      pass    pass    FAIL    
    #
    # Data transformations for direction = server1:
    
    # Data differences found among rows:
    UPDATE db1.t1 SET b = 'Test 123' WHERE a = '1';
    UPDATE db1.t1 SET b = 'Test 789' WHERE a = '3';
    DELETE FROM db1.t1 WHERE a = '4';
    INSERT INTO db1.t1 (a, b) VALUES('5', 'New row - db2');
    
    
    # Database consistency check failed.
    #
    # ...done
  
    Similarly, when the same command is run with --changes-for=server2 and
    --difftype=sql, the following report is generated.
  
    $ mysqldbcompare --server1=root:root@localhost \
        --server2=root:root@localhost db1:db2 --changes-for=server2 -a \
        --difftype=sql
        
    [...]
  
    #                                                   Defn    Row     Data   
    # Type      Object Name                             Diff    Count   Check  
    # ------------------------------------------------------------------------- 
    # TABLE     t1                                      pass    pass    FAIL    
    #
    # Data transformations for direction = server2:
    
    # Data differences found among rows:
    UPDATE db2.t1 SET b = 'Test 789' WHERE a = '1';
    UPDATE db2.t1 SET b = 'Test 123' WHERE a = '3';
    DELETE FROM db2.t1 WHERE a = '5';
    INSERT INTO db2.t1 (a, b) VALUES('4', 'New row - db1');
  
    When the --changes-for=both option is set with the --difftype=sql SQL
    generation option set, the following shows an excerpt of the results.
    
    $ mysqldbcompare --server1=root:root@localhost \
        --server2=root:root@localhost db1:db2 --changes-for=both -a \
        --difftype=sql
        
    [...]
  
    #                                                   Defn    Row     Data   
    # Type      Object Name                             Diff    Count   Check  
    # ------------------------------------------------------------------------- 
    # TABLE     t1                                      pass    pass    FAIL    
    #
    # Data transformations for direction = server1:
    
    # Data differences found among rows:
    UPDATE db1.t1 SET b = 'Test 123' WHERE a = '1';
    UPDATE db1.t1 SET b = 'Test 789' WHERE a = '3';
    DELETE FROM db1.t1 WHERE a = '4';
    INSERT INTO db1.t1 (a, b) VALUES('5', 'New row - db2');
  
    # Data transformations for direction = server2:
    
    # Data differences found among rows:
    UPDATE db2.t1 SET b = 'Test 789' WHERE a = '1';
    UPDATE db2.t1 SET b = 'Test 123' WHERE a = '3';
    DELETE FROM db2.t1 WHERE a = '5';
    INSERT INTO db2.t1 (a, b) VALUES('4', 'New row - db1');
    
    
    # Database consistency check failed.
    #
    # ...done


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
