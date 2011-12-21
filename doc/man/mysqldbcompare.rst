.. `mysqldbcompare`:

#######################################################################
``mysqldbcompare`` - check two databases and identify any differences
#######################################################################

SYNOPSIS
--------

::

  mysqldbcompare --server1=<user>[<passwd>]@<host>:[<port>][:<socket>]
            [ --server2=<user>[<passwd>]@<host>:[<port>][:<socket>] |
              --help | --version | --verbose | --run-all-tests | --quiet |
              --format=<format> | --width=<width> |
              --changes-for=[server1|server2] | 
              [--difftype=[unified|context|differ|sql]]
              [<db1:db2> | <db> [<db1:db2>* | db*] [--skip-object-compare |
              --skip-row-count | --skip-diff | --skip-data-check]

DESCRIPTION
-----------

This utility is used to compare the objects and data from two databases to
ensure they are the same. It will identify objects whose definitions differ
presenting them in a diff-style format of choice. Differences in the data are
shown using a similar diff-style format. Changed or missing rows are shown in a
standard format of either GRID, CSV, TAB, or VERTICAL.

Those objects considered in the database include tables, views, triggers,
procedures, functions, and events. A count of each object type can be shown
with the :option:`-vv` option.

The check is performed using a series of steps called tests. The utility is
designed to stop on the first failed test but the user may specify the
:option:`--run-all-tests` option which will run-all-tests the utility to run
all tests regardless of their end state.

Note: using :option:`--run-all-tests` may produce expected cascade failures.
For example, if the row counts differ among two tables being compared, the data
consistency will also fail.

The tests include the following:

1) check database definitions
2) check existance of objects in both databases
3) compare the definitions of objects
4) check row count for tables
5) check data consistency for tables

(1) A database existance precondition check will ensure both databases exist.
If they do not, no further processing is possible and the
:option:`--run-all-tests` option is ignored.

(2) The test for objects in both databases will identify those objects missing
from one or another database. The following tests (3)-(5) apply only those
objects that appear in both databases.

(3) The definitions (the CREATE statements) are compared and differences are
presented. In the case of name differences only, this test will fail (since the
statements are not the same) but the user may elect that this is normal and
therefore may want to run the utility again with the :option:`--skip-diff`
option to skip this test.

(4) The row count test ensure both tables have the same number of rows. Note
that this does not ensure the table data is consistent - it is merely a cursory
check to indicate possible missing rows in one or the other table being
compared. The data consistency check (5) will identify the missing rows.

(5) The test for data consistency will identify both changed rows as well as
missing rows from one or another of the tables in the databases. Changed rows
are displayed as a diff-style report with the format chosen (default is GRID)
and missing rows are also displayed using the format chosen.

A test may complete with one of the following states:

**pass**
  the test succeeded

**FAIL**
  the test failed - errors are displayed following the test state line

**SKIP**
  the test was skipped due to a missing prerequisite or a skip option

**WARN**
  the test encountered an unusual but not fatal error

**-**
  the test is not applicable to this object

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

The user may specify the databases to compare using the notation db1:db2.
Additionally, the check may be run against either a single server for comparing
two databases of different names on the same server by specifying only the
:option:`--server1` option. The user can also connect to another server by
specifying the :option:`--server2` option. In this case, the database or
database object pair align such that database1 (or database1.object1) are taken
from server1 and database2 (or database2.object2) are taken from server2.

You can change the display format of the diff-style output using one of the
following formats:

**unified** (default)
  print unified format output

**context**
  print context format output

**differ**
  print differ-style format output

You can change the display format of changed or missing row output using one of
the following formats:

**GRID**
  displays output formatted like that of the mysql monitor in a grid
  or table layout.

**CSV**
  displays the output in a comma-separated list.

**TAB**
  displays the output in a tab-separated list.

**VERTICAL**
  displays the output in a single column similar to the ``\G`` option
  for the mysql monitor commands.

The :option:`--changes-for` option can be used to control the direction of the
difference (by specifying the object to be transformed) in either the
difference report (default) or the transformation report (designated with the
:option:`--difftype=sql` option). For example, consider the following command.::

  mysqldbcompare --server1=root@host1 --server2@host2 db1.table1:dbx.table3
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

You must provide login information such as user, host, password, etc. for a
user that has the appropriate rights to access all objects in the operation.

If the utility is to be run on a server that has binary logging enabled, and
you do not want the compare steps logged, you can disable the binary logging
(if turned on) of the compare by using the :option:`--disable-binary-logging`
option and will be re-enabled on exit.

OPTIONS
-------

.. option:: --help

   Display a help message and exit.

.. option:: --changes-for=DIRECTION

   Specify the server to show transformations to match the other server. For
   example, to see the transformation for transforming server1 to match
   server2, use --changes-for=server1. Valid values are 'server1' or
   'server2'. The default is 'server1'.

.. option:: --difftype=<difftype>, -d<difftype>

   Display differences in context format either unified,
   context, differ, or sql (default: unified).
   
.. option:: --disable-binary-logging

   Turn binary logging off during operation if enabled (SQL_LOG_BIN=1).
   Prevents compare operations from being written to the binary log. Note: may
   require SUPER privilege.

.. option:: --format=<format>, -f<format>

   Display missing rows in either GRID (default), CSV, TAB, or VERTICAL format.
   
.. option:: --quiet

   Do not print anything. Return only success or fail as exit code.

.. option:: --run-all-tests, -a

   Do not halt at the first difference found. Process all objects.
   
.. option:: --server1=<source>

   Connection information for the first server in the form:
   <user>:<password>@<host>:<port>:<socket>

.. option:: --server2=<source>

   Connection information for the second server in the form:
   <user>:<password>@<host>:<port>:<socket>

.. option:: --show-reverse

   Produce a transformation report containing the SQL statements to conform the
   object definitions specified in reverse. For example if --changes-for is set
   to server1, also generate the transformation for server2. Note: the reverse
   changes are annotated and marked as comments.

.. option:: --skip-data-check

   Skip data consistency check.

.. option:: --skip-diff

   Skip the object diff step.

.. option:: --skip-object-compare

   Skip object comparison step.

.. option:: --skip-row-count

   Skip row count step.

.. option:: --verbose, -v

   Control how much information is displayed. For example, -v =
   verbose, -vv = more verbose, -vvv = debug.

.. option:: --version

   Display version information and exit.

.. option:: --width

   Change the display width of the test report.


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
