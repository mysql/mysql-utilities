.. _`mysqldbexport`:

#####################################################################
``mysqldbexport`` - Export Object Definitions or Data from a Database
#####################################################################

SYNOPSIS
--------

::

 mysqldbexport --server=<user>[:<passwd>]@<host>[:<port>][:<socket>]
             (<db_name>[, <db_name>])+ [--quiet | --help | --no-headers |
             --skip=(TABLES,TRIGGERS,VIEWS,PROCEDURES,FUNCTIONS,
             EVENTS,GRANTS,DATA,CREATE_DB)* | --skip-blobs | --help |
             --verbose | --version | --bulk-insert | --file-per-table |
             --export=[DEFINITIONS|DATA|BOTH] |
             --format=[SQL|S|GRID|G|TAB|T|CSV|C|VERTICAL|V] ] |
             --exclude=<name>[|,--exclude=<name>]

DESCRIPTION
-----------

This utility exports the metadata
(object definitions) or data or both from one or more
databases. By default, the utility exports only definitions.

You can also skip objects by type using the :option:`--skip` option
To skip objects by type, use the :option:`--skip` option
with a list of the objects to skip. This enables you to extract a
particular set of objects, say, for exporting only events (by
excluding all other types). Similarly, to skip creation of **UPDATE**
statements for BLOB data, specify the :option:`--skip-blobs` option.

To specify how to display output, use one of the following values
with the :option:`--format` option:

**SQL** (default)
  Display output using SQL statements. For definitions, this consists of
  the appropriate **CREATE** and **GRANT** statements. For data, this
  is an **INSERT** statement (or bulk insert if the
  :option:`--bulk-insert` option is specified).

**GRID**
  Display output formatted like that of the mysql monitor in a grid
  or table layout.

**CSV**
  Display output in comma-separated values format.

**TAB**
  Display output in tab-separated format.

**VERTICAL**
  Display output in a single column similar to the ``\G`` command
  for the mysql monitor.

To specify how much data to display, use one of the following values
with the :option:`--display` option:

**BRIEF**
  Display only the minimal columns for recreating the objects.

**FULL**
  Display the complete column list for recreating the objects.

**NAMES**
  Display only the object names.

Note: For SQL-format output, the :option:`--display` option is ignored.

To turn off the headers when using CSV or TAB display format, specify
the :option:`--no-headers` option.

To turn off all feedback information, specify the :option:`--quiet` option.

You can also have the utility write the data for the tables to separate files
by using the :option:`--file-per-table` option. This creates files with a
file name composed of the database and table name followed by the format of the
file. For example, the following command produces files named
db1.<table_name>.csv::

  mysqldbexport --server=root@server1:3306 --format=csv db1 --export=data

To exclude specific objects by name, use the :option:`--exclude` option
whereby you specify a name in <db>.<object> format or supply a
regex search pattern. For example, :option:`--exclude=db1.trig1` excludes
the single named trigger and :option:`--exclude=trig_` excludes all objects
from all databases whose name begins with trig and has a following character
or digit.

**mysqldbexport** differs from **mysqldump** in that it can produce output in a
variety of formats to make your data extraction/transport much easier. It
permits you to export your data in the format most suitable to an external
tool, another MySQL server, or a yet another use without the need to
reformat the data.

By default, the export operation uses a consistent snapshot to read
from the selected databases. To change the locking mode, use the
:option:`--locking` option. To disable locking altogether or use
only table locks, use an option value of 'no-locks' or 'lock-all',
respectively. The default value is 'snapshot'.

You must provide connection parameters (user, host, password, and
so forth), for an account that has the appropriate privileges to
access all objects in the operation.
For details, see :ref:`mysqldbexport-notes`.

OPTIONS
-------

**mysqldbexport** accepts the following command-line options:

.. option:: --help

   Display a help message and exit.

.. option:: --bulk-insert, -b

   Use bulk insert statements for data (default:False).

.. option:: --display=<display>, -d<display>

   Control the number of columns shown. Permitted display values are BRIEF
   = minimal columns for object creation (default), FULL = all columns, and
   NAMES = only object names (not valid for --format=SQL).

.. option:: --exclude=<exclude>, -x<exclude> 

   Exclude one or more objects from the operation using either a specific name
   such as db1.t1 or a REGEXP search pattern.  Use this option multiple times
   to specify multiple exclusions.

   This option does not apply to grants.

.. option:: --export=<export>, -e<export>

   Control the export of either DATA|D = only the table data for the
   tables in the database list, DEFINITIONS|F = export only the
   definitions for the objects in the database list, or BOTH|B =
   export the metadata followed by the data (default: export metadata).

.. option:: --file-per-table

   Write table data to separate files. This is Valid only if the export
   output includes data (that is, if :option:`--export=data`
   or :option:`--export=both` are given). This option produces files named
   <db_name>.<tbl_name>.<format>. For example, a CSV export of two tables in
   db1, t1 and t2, results in files named db1.t1.csv and db1.t2.csv. If
   definitions are included, they are written to stdout as usual.

.. option:: --format=<format>, -f<format>

   Specify the output format. Permitted format values are
   SQL|S, GRID|G, TAB|T, CSV|C, and VERTICAL|V. The default is SQL.

.. option:: --locking=<locking>

   Choose the lock type for the operation. Permitted lock values are no-locks
   = do not use any table locks, lock-all = use table locks but no transaction
   and no consistent read, and snaphot = consistent read using a single
   transaction. The default is snapshot.

.. option::  --no-headers, -h

   Do not display the column headers. This option is ignored for GRID-format
   output.

.. option:: --quiet, -q

   Turn off all messages for quiet execution.

.. option:: --regexp, --basic-regexp, -G

   Use 'REGEXP' operator to match pattern for exclusion. Default is to use
   'LIKE'.

.. option:: --server=<server>

   Connection information for the server in the format:
   <user>:<password>@<host>:<port>:<socket>

.. option:: --skip=<skip-objects>

   Specify objects to skip in the operation as a comma-separated list
   (no spaces). Permitted values are CREATE_DB, DATA, EVENTS, FUNCTIONS,
   GRANTS, PROCEDURES, TABLES, TRIGGERS, and VIEWS.

.. option:: --skip-blobs

   Do not export BLOB data.

.. option:: --verbose, -v

   Specify how much information to display. Use this option
   multiple times to increase the amount of information.  For example, -v =
   verbose, -vv = more verbose, -vvv = debug.

.. option:: --version

   Display version information and exit.


.. _mysqldbexport-notes:

NOTES
-----

The login user must have the appropriate permissions to
read the old database and access (read) the mysql database.

To export all objects from a source database, the user must have **SELECT** and
**SHOW VIEW** privileges on the database as well as **SELECT** on the
mysql database.

Actual privileges needed may differ from installation to installation
depending on the security privileges present and whether the database
contains certain objects such as views or events and whether binary
logging is turned on (hence the need for **SUPER**).

Some combinations of the options may result in errors during the operation.
For example, eliminating tables but not views may result in an error when the
view is imported on another server.

The :option:`--exclude` option does not apply to grants.

EXAMPLES
--------

To export the definitions of the database 'dev' from a MySQL server on
localhast via port 3306, producing output consisting of **CREATE** statements,
use this command::

    $ mysqldbexport --server=root:pass@localhost \
      --skip=GRANTS --export=DEFINITIONS util_test
    # Source on localhost: ... connected.
    # Exporting metadata from util_test
    DROP DATABASE IF EXISTS util_test;
    CREATE DATABASE util_test;
    USE util_test;
    # TABLE: util_test.t1
    CREATE TABLE `t1` (
      `a` char(30) DEFAULT NULL
    ) ENGINE=MEMORY DEFAULT CHARSET=latin1;
    # TABLE: util_test.t2
    CREATE TABLE `t2` (
      `a` char(30) DEFAULT NULL
    ) ENGINE=MyISAM DEFAULT CHARSET=latin1;
    # TABLE: util_test.t3
    CREATE TABLE `t3` (
      `a` int(11) NOT NULL AUTO_INCREMENT,
      `b` char(30) DEFAULT NULL,
      PRIMARY KEY (`a`)
    ) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=latin1;
    # TABLE: util_test.t4
    CREATE TABLE `t4` (
      `c` int(11) NOT NULL,
      `d` int(11) NOT NULL,
      KEY `ref_t3` (`c`),
      CONSTRAINT `ref_t3` FOREIGN KEY (`c`) REFERENCES `t3` (`a`)
    ) ENGINE=InnoDB DEFAULT CHARSET=latin1;
    # VIEW: util_test.v1
    [...]
    #...done.

Similarly, to export the data of the database 'util_test', producing bulk
insert statements, use this command::

    $ mysqldbexport --server=root:pass@localhost \
      --export=DATA --bulk-insert util_test
    # Source on localhost: ... connected.
    USE util_test;
    # Exporting data from util_test
    # Data for table util_test.t1:
    INSERT INTO util_test.t1 VALUES  ('01 Test Basic database example'),
      ('02 Test Basic database example'),
      ('03 Test Basic database example'),
      ('04 Test Basic database example'),
      ('05 Test Basic database example'),
      ('06 Test Basic database example'),
      ('07 Test Basic database example');
    # Data for table util_test.t2:
    INSERT INTO util_test.t2 VALUES  ('11 Test Basic database example'),
      ('12 Test Basic database example'),
      ('13 Test Basic database example');
    # Data for table util_test.t3:
    INSERT INTO util_test.t3 VALUES  (1, '14 test fkeys'),
      (2, '15 test fkeys'),
      (3, '16 test fkeys');
    # Data for table util_test.t4:
    INSERT INTO util_test.t4 VALUES  (3, 2);
    #...done.
    
If the database to be exported does not contain only InnoDB tables and you
want to ensure data integrity of the exported data  by locking the tables
during the read step, add a :option:`--locking=lock-all` option to the command::

    $ mysqldbexport --server=root:pass@localhost \
      --export=DATA --bulk-insert util_test --locking=lock-all
    # Source on localhost: ... connected.
    USE util_test;
    # Exporting data from util_test
    # Data for table util_test.t1:
    INSERT INTO util_test.t1 VALUES  ('01 Test Basic database example'),
      ('02 Test Basic database example'),
      ('03 Test Basic database example'),
      ('04 Test Basic database example'),
      ('05 Test Basic database example'),
      ('06 Test Basic database example'),
      ('07 Test Basic database example');
    # Data for table util_test.t2:
    INSERT INTO util_test.t2 VALUES  ('11 Test Basic database example'),
      ('12 Test Basic database example'),
      ('13 Test Basic database example');
    # Data for table util_test.t3:
    INSERT INTO util_test.t3 VALUES  (1, '14 test fkeys'),
      (2, '15 test fkeys'),
      (3, '16 test fkeys');
    # Data for table util_test.t4:
    INSERT INTO util_test.t4 VALUES  (3, 2);
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
