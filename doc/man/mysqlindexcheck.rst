.. `mysqlindexcheck`:

##################################################################
``mysqlindexcheck`` - Identify Potentially Redundant Table Indexes
##################################################################

SYNOPSIS
--------

::

 mysqlindexcheck [options] db[:table] ...

DESCRIPTION
-----------

This utility reads the indexes for one or more tables and identifies
duplicate and potentially redundant indexes.

To check all tables in a database, specify only the database name. To check
a specific table, name the table in *db.table* format. It is possible
to mix database and table names.

You can scan tables in any database except the internal databases
**mysql**, **INFORMATION_SCHEMA**, and **performance_schema**.

Depending on the index type, the utility applies the following rules to
compare indexes (designated as ``idx_a`` and ``idx_b``):

**BTREE**
  ``idx_b`` is redundant to ``idx_a`` if and only if the first *n* columns in
  ``idx_b`` also appear in ``idx_a``. Order and uniqueness count.

**HASH**
  ``idx_a`` and ``idx_b`` are duplicates if and only if they contain the same
  columns in the same order. Uniqueness counts.

**SPATIAL**
  ``idx_a`` and ``idx_b`` are duplicates if and only if they contain the same
  column (only one column is permitted).

**FULLTEXT**
  ``idx_b`` is redundant to ``idx_a`` if and only if all columns in ``idx_b``
  are included in ``idx_a``. Order counts.

To see **DROP** statements to drop redundant indexes,
specify the :option:`--show-drops` option. To examine the existing
indexes, use the :option:`--verbose` option, which prints the
equivalent **CREATE INDEX** (or **ALTER TABLE** for primary keys.

To display the best or worst nonprimary key indexes for each table,
use the :option:`--best` or :option:`--worst` option. This causes the
output to show the best or worst indexes from tables with 10 or more rows.
By default, each option shows five indexes. To override that, provide
an integer value for the option.

To change the format of the index lists displayed for the
:option:`--show-indexes`, :option:`--best`, and :option:`--worst` options,
use one of the following values with the :option:`--format` option:

**grid** (default)
  Display output in grid or table format like that of the
  :command:`mysql` monitor.

**csv**
  Display output in comma-separated values format.

**tab**
  Display output in tab-separated format.

**sql**
  print SQL statements rather than a list.

**vertical**
  Display output in single-column format like that of the ``\G`` command
  for the :command:`mysql` monitor.

Note: The :option:`--best` and :option:`--worst` lists cannot be
printed as SQL statements.

OPTIONS
-------

:command:`mysqlindexcheck` accepts the following command-line options:

.. option:: --help

   Display a help message and exit.

.. option:: --best[=<N>]

   If :option:`--stats` is given,
   limit index statistics to the best *N* indexes. The default value of *N* is
   5 if omitted.

.. option:: --format=<index_format>, -f<index_format>

   Specify the index list display format for output produced by
   :option:`--stats`. Permitted format values are **grid**, **csv**, **tab**,
   **sql**, and **vertical**. The default is **grid**.

.. option:: --server=<source>

   Connection information for the server in
   <*user*>[:<*passwd*>]@<*host*>[:<*port*>][:<*socket*>] format.

.. option:: --show-drops, -d

   Display **DROP** statements for dropping indexes.

.. option:: --show-indexes, -i

   Display indexes for each table.

.. option:: --skip, -s

   Skip tables that do not exist.

.. option:: --stats

    Show index performance statistics.

.. option::  --verbose, -v

   Specify how much information to display. Use this option
   multiple times to increase the amount of information.  For example,
   :option:`-v` = verbose, :option:`-vv` = more verbose, :option:`-vvv` =
   debug.

.. option:: --version

   Display version information and exit.

.. option:: --worst[=<N>]

   If :option:`--stats` is given,
   limit index statistics to the worst *N* indexes. The default value of *N* is
   5 if omitted.

.. _mysqlindexcheck-notes:

NOTES
-----

You must provide connection parameters (user, host, password, and
so forth) for an account that has the appropriate privileges to
read all objects accessed during the operation.

For the :option:`--format` option, the permitted values are not case
sensitive. In addition, values may be specified as any unambiguous prefix of
a valid value.  For example, :option:`--format=g` specifies the grid format.
An error occurs if a prefix matches more than one valid value.

EXAMPLES
--------

To check all tables in the ``employees`` database on the local server to see
the possible redundant and duplicate indexes, use this command::

    $ mysqlindexcheck --server=root@localhost employees
    # Source on localhost: ... connected.
    # The following indexes are duplicates or redundant \
      for table employees.dept_emp:
    #
    CREATE INDEX emp_no ON employees.dept_emp (emp_no) USING BTREE
    #     may be redundant or duplicate of:
    ALTER TABLE employees.dept_emp ADD PRIMARY KEY (emp_no, dept_no)
    # The following indexes are duplicates or redundant \
      for table employees.dept_manager:
    #
    CREATE INDEX emp_no ON employees.dept_manager (emp_no) USING BTREE
    #     may be redundant or duplicate of:
    ALTER TABLE employees.dept_manager ADD PRIMARY KEY (emp_no, dept_no)
    # The following indexes are duplicates or redundant \
      for table employees.salaries:
    #
    CREATE INDEX emp_no ON employees.salaries (emp_no) USING BTREE
    #     may be redundant or duplicate of:
    ALTER TABLE employees.salaries ADD PRIMARY KEY (emp_no, from_date)
    # The following indexes are duplicates or redundant \
      for table employees.titles:
    #
    CREATE INDEX emp_no ON employees.titles (emp_no) USING BTREE
    #     may be redundant or duplicate of:
    ALTER TABLE employees.titles ADD PRIMARY KEY (emp_no, title, from_date)

COPYRIGHT
---------

Copyright (c) 2010, 2012, Oracle and/or its affiliates. All rights reserved.

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
