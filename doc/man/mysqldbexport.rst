.. _`mysqldbexport`:

#####################################################################
``mysqldbexport`` - Export object definitions or data from a database
#####################################################################

SYNOPSIS
--------

::

 mysqldbexport --server=<user>[<passwd>]@<host>:[<port>][:<socket>]
             (<db_name>[, <db_name>])+ [--quiet | --help | --no-headers |
             --skip=(TABLES,TRIGGERS,VIEWS,PROCEDURES,FUNCTIONS,
             EVENTS,GRANTS,DATA,CREATE_DB)* | --skip-blobs | --help |
             --veerbose | --version | --bulk-insert | --file-per-table |
             --export=[DEFINITIONS|DATA|BOTH] |
             --format=[SQL|S|GRID|G|TAB|T|CSV|C|VERTICAL|V] ] |
             --exclude=<name>[|,--exclude=<name>]

DESCRIPTION
-----------

This utility permits a database administrator to export the metadata
(object definitions, hence definitions) or data or both from one or more
databases. By default, the utility will export only definitions.

You can also skip objects by type using the :option:`--skip` option
and list the objects you want to skip. This can allow you to extract a
particular set of objects, say, for exporting only events (by
excluding all other types). Similarly, you can skip creating blob
UPDATE commands by specifying the :option:`--skip-blobs` option.

You also have the choice to view the output in one of the following
formats using the :option:`--format` option.

**SQL**
  Displays the output using SQL statements. For definitions, this is
  the appropriate **CREATE** and **GRANT** statements. For data, this
  is an **INSERT** statement (or bulk insert if the
  :option:`--bulk-insert` options is specified).

**GRID**
  Displays output formatted like that of the mysql monitor in a grid
  or table layout.

**CSV**
  Displays the output in a comma-separated list.

**TAB**
  Displays the output in a tab-separated list.

**VERTICAL**
  Displays the output in a single column similar to the ``\G`` option
  for the mysql monitor commands.

  You also have the option to specify how much data to display in one
  of the following displays using the :option:`--display` option.

**BRIEF**
  Show only the minimal columns for recreating the objects.

**FULL**
  Show the complete column list for recreating the objects.

**NAMES**
  Show only the names of the objects.

Note: When combining :option:`--format` and :option:`--display`, the
:option:`--display` option is ignored for SQL generation.

You can turn off the headers when using formats CSV and TAB by
specifying the :option:`--no-headers` option.

You can turn off all feedback information by specifying the
:option:`--quiet` option.

You can also have the utility write the data for the tables to separate files
by using the :option:`--file-per-table` option. This would create files with a
file name composed of the database and table name followed by the format of the
file. For example, the following command produces files named db1.<table
name>.csv.::

  mysqldbexport --server=root@server1:3306 --format=csv db1 --export=data

You can exclude specific objects by name using the :option:`--exclude` option
whereby you specify a name in the form of <db>.<object> or you can supply a
regex search pattern. For example, :option:`--exclude=db1.trig1` will exclude
the single trigger and :option:`--exclude=trig_` will exclude all objects from
all databases whose name begins with trig and has a following character or
digit.

This utility differs from mysqldump in that it can produce output in a
variety of formats to make your data extraction/transport much easier. It
permits you to export your data in the format most suitable to an external
tool, another MySQL server, or a yet another use without the need to
reformat the data.

You must provide login information such as user, host, password, etc. for a
user that has the appropriate rights to access all objects in the operation.
See :ref:`mysqldbexport-notes` below for more details.

OPTIONS
-------

.. option:: --version

   show program's version number and exit

.. option:: --help

.. option:: --server <server>

   connection information for the server in the form:
   <user>:<password>@<host>:<port>:<socket>

.. option:: --format <format>, -f <format>

   display the output in either SQL|S (default), GRID|G, TAB|T, CSV|C,
   or VERTICAL|V format

.. option:: --display <display>, -d <display>

   control the number of columns shown: BRIEF = minimal columns for
   object creation (default), FULL = all columns, NAMES = only object
   names (not valid for --format=SQL)

.. option:: --export <export>, -e <export>

   control the export of either DATA|D = only the table data for the
   tables in the database list, DEFINITIONS|F = export only the
   definitions for the objects in the database list, or BOTH|B =
   export the metadata followed by the data (default: export metadata)

.. option:: --bulk-insert, -b

   Use bulk insert statements for data (default:False)

.. option:: --file-per-table

   Write table data to separate files. Valid only for :option:`--export=data`
   or :option:`--export=both`. Files will be named
   <db_name>.<tbl_name>.<format>. For example, a CSV export of two tables in
   db1, t1 and t2, results in files named db1.t1.csv and db1.t2.csv. If
   definitions are included, they are written to stdout as normal.

.. option:: --no-headers, -h

   do not display the column headers - ignored for GRID format

.. option:: --quiet, -q

   turn off all messages for quiet execution

.. option:: --verbose, -v

   control how much information is displayed. For example, -v =
   verbose, -vv = more verbose, -vvv = debug

.. option:: --skip <skip-objects>

   specify objects to skip in the operation in the form of a
   comma-separated list (no spaces). Valid values = TABLES, VIEWS,
   TRIGGERS, PROCEDURES, FUNCTIONS, EVENTS, GRANTS, DATA, CREATE_DB

.. option:: -x EXCLUDE --exclude=EXCLUDE

   exclude one or more objects from the operation using either a specific name
   such as db1.t1 or a REGEXP search pattern. Repeat option for multiple
   exclusions.

.. option:: --skip-blobs

   Do not export blob data.


.. _mysqldbexport-notes:

NOTES
-----

The login user must have the appropriate permissions to create new
objects, read the old database, access (read) the mysql database, and
grant privileges.

To export all objects from a source, the user must have **SELECT** and
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
localhast via port 3306 producing **CREATE** statements, use this command::

    $ mysqldbexport --server=root:pass@localhost \\
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

Similarly, to export the data of the database 'util_test' producing bulk
insert statements, use this command::

    $ mysqldbexport --server=root:pass@localhost \\
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
