.. `mysqlindexcheck`:

#######################################################################
``mysqlindexcheck`` - Identify potentially redundant indexes in a table
#######################################################################

SYNOPSIS
--------

::

  mysqlcheckindex --server=<user>[<passwd>]@<host>:[<port>][:<socket>]
                 [[ --help | --version ] |
                 [ --show-drops | --skip | --verbose | --show-indexes |
                   --quiet | --index-format=[GRID|SQL|TAB|CSV] |
                   --stats [--best=<num_rows> | --worst=<num rows> ]]
                 <db> | [ ,<db> | ,<db.table> | , <db.table>]]

DESCRIPTION
-----------

This utility is used to read the indexes for one or more tables and
identify duplicate and potentially redundant indexes. The following
rules are applied during the operation.

**BTREE**
  idx_b is redundant to idx_a iff the first n columns in idx_b
  also appear in idx_a. Order and uniqueness count.

**HASH**
  idx_a and idx_b are duplicates iff they contain the same
  columns in the same order and uniqueness counts.

**SPATIAL**
  idx_a and idx_b are duplicates iff they contain the same
  column (only 1 column is permitted)

**FULLTEXT**
  idx_b is redundant to idx_a iff all columns in idx_b are
  included in idx_a (order is not important)

You can specify scanning all of the tables for any database (except
the internal databases **mysql**, **INFORMATION_SCHEMA**,
**PERFORMANCE_SCHEMA**) by specifying only the database name or you
can specify a list of tables (in the form *db.tablename*) which will
limit the scan to only those tables in the databases listed and those
tables listed.

If you want to see the example DROP statements to drop the redundant
indexes, you can specify the -d option (see below). You can also
examine the existing indexes using the :option:`-v` option which
prints the equivalent **CREATE INDEX** (or **ALTER TABLE** for primary
keys).

You can also display the best and worst non-primary key indexes for
each table with the :option:`--best` and :option:`--worst`
options. The data will show the top 5 indexes from tables with 10 or
more rows.

You can change the display format of the index lists for
:option:`--show-indexes`, :option:`--best`, and :option:`--worst` in
one of the following formats:

**TABLE** (default)
  print a mysql-like table output

**TAB**
  print using tabs for separation

**CSV**
  print using commas for separation

**SQL**
  print SQL statements rather than a list.

Note: the :option:`--best` and :option:`--worst` lists cannot be
printed as SQL statements.

You must provide login information (e.g., user, host, password, etc.
for a user that has the appropriate rights to access all objects
in the operation.

OPTIONS
-------

.. option:: --version

   show version number and exit

.. option:: --help

   show the help page

.. option:: --server <source>

   connection information for source server in the form:
   <user>:<password>@<host>:<port>:<socket>

.. option:: --show-drops, -d

   display DROP statements for dropping indexes

.. option:: --show-indexes, -i

   display indexes for each table

.. option:: --skip, -s

   skip tables that do not exist

.. option:: -v, --verbose

   control how much information is displayed. e.g., -v =
   verbose, -vv = more verbose, -vvv = debug

.. option:: --format <index-format>

   Display the list of indexes per table in either **SQL**, **TABLE**
   (default), **TAB**, **CSV**, or **VERTICAL** format

.. option:: --stats

    show index performance statistics

.. option:: --best <num>

    limit index statistics to the best N indexes

.. option:: --worst <num>

   limit index statistics to the worst N indexes


NOTES
-----

The login user must have the appropriate permissions to read all databases
and tables listed.

EXAMPLES
--------

To scan all of the tables in the employees database to see the possible
redundant and duplicate indexes as well as the DROP statements for the indexes,
use this command::

    $ python .mysqlindexcheck.py --server=root@localhost employees
    # Source on localhost: ... connected.
    # The following indexes are duplicates or redundant \\
      for table employees.dept_emp:
    #
    CREATE INDEX emp_no ON employees.dept_emp (emp_no) USING BTREE
    #     may be redundant or duplicate of:
    ALTER TABLE employees.dept_emp ADD PRIMARY KEY (emp_no, dept_no)
    # The following indexes are duplicates or redundant \\
      for table employees.dept_manager:
    #
    CREATE INDEX emp_no ON employees.dept_manager (emp_no) USING BTREE
    #     may be redundant or duplicate of:
    ALTER TABLE employees.dept_manager ADD PRIMARY KEY (emp_no, dept_no)
    # The following indexes are duplicates or redundant \\
      for table employees.salaries:
    #
    CREATE INDEX emp_no ON employees.salaries (emp_no) USING BTREE
    #     may be redundant or duplicate of:
    ALTER TABLE employees.salaries ADD PRIMARY KEY (emp_no, from_date)
    # The following indexes are duplicates or redundant \\
      for table employees.titles:
    #
    CREATE INDEX emp_no ON employees.titles (emp_no) USING BTREE
    #     may be redundant or duplicate of:
    ALTER TABLE employees.titles ADD PRIMARY KEY (emp_no, title, from_date)

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
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
USA
