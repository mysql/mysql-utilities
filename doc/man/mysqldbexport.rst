.. _`mysqldbexport`:

#####################################################################
``mysqldbexport`` - Export Object Definitions or Data from a Database
#####################################################################

SYNOPSIS
--------

::

 mysqldbexport [options] db_name ...

DESCRIPTION
-----------

This utility exports metadata (object definitions) or data or both from one
or more databases. By default, the export includes only definitions.

:command:`mysqldbexport` differs from :command:`mysqldump` in that it can
produce output in a variety of formats to make your data
extraction/transport much easier. It permits you to export your data in the
format most suitable to an external tool, another MySQL server, or other use
without the need to reformat the data.

To exclude specific objects by name, use the :option:`--exclude` option with
a name in *db*.*obj* format, or you can supply a search pattern. For example,
:option:`--exclude=db1.trig1` excludes the single trigger and
:option:`--exclude=trig_` excludes all objects from all databases having a
name that begins with ``trig`` and has a following character.

To skip objects by type, use the :option:`--skip` option
with a list of the objects to skip. This enables you to extract a
particular set of objects, say, for exporting only events (by
excluding all other types). Similarly, to skip creation of **UPDATE**
statements for ``BLOB`` data, specify the :option:`--skip-blobs` option.

To specify how to display output, use one of the following values
with the :option:`--format` option:

**sql** (default)
  Display output using SQL statements. For definitions, this consists of
  the appropriate **CREATE** and **GRANT** statements. For data, this
  is an **INSERT** statement (or bulk insert if the
  :option:`--bulk-insert` option is specified).

**grid**
  Display output in grid or table format like that of the
  :command:`mysql` monitor.

**csv**
  Display output in comma-separated values format.

**tab**
  Display output in tab-separated format.

**vertical**
  Display output in single-column format like that of the ``\G`` command
  for the :command:`mysql` monitor.

To specify how much data to display, use one of the following values
with the :option:`--display` option:

**brief**
  Display only the minimal columns for recreating the objects.

**full**
  Display the complete column list for recreating the objects.

**names**
  Display only the object names.

Note: For SQL-format output, the :option:`--display` option is ignored.

To turn off the headers for **csv** or **tab** display format, specify
the :option:`--no-headers` option.

To turn off all feedback information, specify the :option:`--quiet` option.

To write the data for individual tables to separate files, use the
:option:`--file-per-table` option. The name of each file is composed of the
database and table names followed by the file format.  For example, the
following command produces files named db1.*table_name*.csv::

  mysqldbexport --server=root@server1:3306 --format=csv db1 --export=data

By default, the operation uses a consistent snapshot to read the source
databases. To change the locking mode, use the :option:`--locking` option
with a locking type value.  Use a value of **no-locks** to turn off locking
altogether or **lock-all** to use only table locks. The default value is
**snapshot**. Additionally, the utility uses WRITE locks to lock the
destination tables during the copy.

You can include replication statements for exporting data among a master and
slave or between slaves. The :option:`--rpl` option permits you to select
from the following replication statements to include in the export.

**master**
  Include the **CHANGE MASTER** statement to start a new slave with the current
  server acting as the master. This places the appropriate STOP and
  START slave statements in the export whereby the **STOP SLAVE** statement is
  placed at the start of the export and the **CHANGE MASTER** followed by the
  **START SLAVE** statements are placed after the export stream.
    
**slave**
  Include the **CHANGE MASTER** statement to start a new slave using the
  current server's master information. This places the appropriate STOP and
  START slave statements in the export whereby the **STOP SLAVE** statment is
  placed at the start of the export and the **CHANGE MASTER** followed by
  the **START SLAVE** statements are placed after the export stream.
  
**both**
  Include both the 'master' and 'slave' information for **CHANGE MASTER**
  statements for either spawning a new slave with the current server's master
  or using the current server as the master. All statements generated are
  labeled and commented to enable the user to choose which to include when
  imported.

To include the replication user in the **CHANGE MASTER** statement,
use the :option:`--rpl-user` option to specify the user and password. If
this option is omitted, the utility attempts to identify the replication
user. In the event that there are multiple candidates or the user requires a
password, these statements are placed inside comments for the **CHANGE
MASTER** statement.

You can also use the :option:`--comment-rpl` option to place the replication
statements inside comments for later examination.

If you specify the :option:`--rpl-file` option, the utility writes the
replication statements to the file specified instead of including them
in the export stream.

OPTIONS
-------

:command:`mysqldbexport` accepts the following command-line options:

.. option:: --help

   Display a help message and exit.

.. option:: --bulk-insert, -b

   Use bulk insert statements for data.

.. option:: --comment-rpl

   Place the replication statements in comment statements. Valid only with
   the :option:`--rpl` option.
 
.. option:: --display=<display>, -d<display>

   Control the number of columns shown. Permitted display values are **brief**
   (minimal columns for object creation), **full* (all columns), and **names**
   (only object names; not valid for :option:`--format=sql`). The default is
   **brief**.

.. option:: --exclude=<exclude>, -x<exclude> 

   Exclude one or more objects from the operation using either a specific name
   such as ``db1.t1`` or a search pattern.  Use this option multiple times
   to specify multiple exclusions. By default, patterns use **LIKE** matching.
   With the :option:`--regexp` option, patterns use **REGEXP** matching.

   This option does not apply to grants.

.. option:: --export=<export>, -e<export>

   Specify the export format. Permitted format values are **definitions** =
   export only the definitions (metadata) for the objects in the database list,
   **data** = export only the table data for the tables in the database list,
   and **both** = export the definitions and the data. The default is
   **definitions**.

.. option:: --file-per-table

   Write table data to separate files. This is Valid only if the export
   output includes data (that is, if :option:`--export=data`
   or :option:`--export=both` are given). This option produces files named
   *db_name*.*tbl_name*.*format*. For example, a **csv** export of two tables
   named ``t1`` and ``t2`` in database ``d1``, results in files named
   ``db1.t1.csv`` and ``db1.t2.csv``. If table definitions are included in the
   export, they are written to stdout as usual.

.. option:: --format=<format>, -f<format>

   Specify the output display format. Permitted format values are
   **sql**, **grid**, **tab**, **csv**, and **vertical**. The default is
   **sql**.

.. option:: --locking=<locking>

   Choose the lock type for the operation. Permitted lock values are
   **no-locks** (do not use any table locks), **lock-all** (use table locks
   but no transaction and no consistent read), and **snapshot** (consistent
   read using a single transaction). The default is **snapshot**.

.. option::  --no-headers, -h

   Do not display column headers. This option applies only for **csv** and
   **tab** output.

.. option:: --quiet, -q

   Turn off all messages for quiet execution.

.. option:: --regexp, --basic-regexp, -G

   Perform pattern matches using the **REGEXP** operator. The default is
   to use **LIKE** for matching.

.. option:: --rpl=<dump_option>, --replication=<dump_option>

   Include replication information. Permitted values are **master** (include
   the **CHANGE MASTER** statement using the source server as the master),
   **slave** (include the **CHANGE MASTER** statement using the destination
   server's master information), and **both** (include the **master** and
   **slave** options where applicable).

.. option:: --rpl-file=RPL_FILE, --replication-file=RPL_FILE

   The path and file name where the generated replication information should
   be written. Valid only with the :option:`--rpl` option.

.. option:: --rpl-user=<user[:password]>

   The user and password for the replication user requirement; for example,
   ``rpl:passwd``. The default is ``rpl:rpl``.
 
.. option:: --server=<server>

   Connection information for the server in
   <*user*>[:<*passwd*>]@<*host*>[:<*port*>][:<*socket*>] format.

.. option:: --skip=<skip-objects>

   Specify objects to skip in the operation as a comma-separated list
   (no spaces). Permitted values are **CREATE_DB**, **DATA**, **EVENTS**,
   **FUNCTIONS**, **GRANTS**, **PROCEDURES**, **TABLES**, **TRIGGERS**,
   and **VIEWS**.

.. option:: --skip-blobs

   Do not export ``BLOB`` data.

.. option:: --verbose, -v

   Specify how much information to display. Use this option
   multiple times to increase the amount of information.  For example,
   :option:`-v` = verbose, :option:`-vv` = more verbose, :option:`-vvv` =
   debug.

.. option:: --version

   Display version information and exit.


.. _mysqldbexport-notes:

NOTES
-----

You must provide connection parameters (user, host, password, and
so forth) for an account that has the appropriate privileges to
access all objects in the operation.

To export all objects from a source database, the user must have these
privileges: **SELECT** and **SHOW VIEW** on the database as well as
**SELECT** on the ``mysql`` database.

Actual privileges needed may differ from installation to installation
depending on the security privileges present and whether the database
contains certain objects such as views or events.

Some combinations of the options may result in errors when the export is
imported later. For example, eliminating tables but not views may result in
an error when a view is imported on another server.

For the :option:`--format`, :option:`--export`, and :option:`--display`
options, the permitted values are not case sensitive. In addition, values
may be specified as any unambiguous prefix of a valid value.  For example,
:option:`--format=g` specifies the grid format. An error occurs if a
prefix matches more than one valid value.

EXAMPLES
--------

To export the definitions of the database ``dev`` from a MySQL server on the
local host via port 3306, producing output consisting of **CREATE**
statements, use this command::

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

Similarly, to export the data of the database ``util_test``, producing bulk
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
want to ensure data integrity of the exported data by locking the tables
during the read step, add a :option:`--locking=lock-all` option to the
command::

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

To export a database and include the replication commands to use
the current server as the master (for example, to start a new slave using the
current server as the master), use the following command::

    $ mysqldbexport --server=root@localhost:3311 util_test \
      --export=both --rpl-user=rpl:rpl --rpl=master -v
    # Source on localhost: ... connected.
    #
    # Stopping slave
    STOP SLAVE;
    #
    # Source on localhost: ... connected.
    # Exporting metadata from util_test
    DROP DATABASE IF EXISTS util_test;
    CREATE DATABASE util_test;
    USE util_test;
    # TABLE: util_test.t1
    CREATE TABLE `t1` (
      `a` char(30) DEFAULT NULL
    ) ENGINE=MEMORY DEFAULT CHARSET=latin1;
    #...done.
    # Source on localhost: ... connected.
    USE util_test;
    # Exporting data from util_test
    # Data for table util_test.t1: 
    INSERT INTO util_test.t1 VALUES ('01 Test Basic database example');
    INSERT INTO util_test.t1 VALUES ('02 Test Basic database example');
    INSERT INTO util_test.t1 VALUES ('03 Test Basic database example');
    INSERT INTO util_test.t1 VALUES ('04 Test Basic database example');
    INSERT INTO util_test.t1 VALUES ('05 Test Basic database example');
    INSERT INTO util_test.t1 VALUES ('06 Test Basic database example');
    INSERT INTO util_test.t1 VALUES ('07 Test Basic database example');
    #...done.
    #
    # Connecting to the current server as master
    CHANGE MASTER TO MASTER_HOST = 'localhost', 
      MASTER_USER = 'rpl', 
      MASTER_PASSWORD = 'rpl', 
      MASTER_PORT = 3311, 
      MASTER_LOG_FILE = 'clone-bin.000001' , 
      MASTER_LOG_POS = 106;
    #
    # Starting slave
    START SLAVE;
    #

Similarly, to export a database and include the replication
commands to use the current server's master (for example, to start a new
slave using the same the master), use the following command::

    $ mysqldbexport --server=root@localhost:3311 util_test \
      --export=both --rpl-user=rpl:rpl --rpl=slave -v
    # Source on localhost: ... connected.
    #
    # Stopping slave
    STOP SLAVE;
    #
    # Source on localhost: ... connected.
    # Exporting metadata from util_test
    DROP DATABASE IF EXISTS util_test;
    CREATE DATABASE util_test;
    USE util_test;
    # TABLE: util_test.t1
    CREATE TABLE `t1` (
      `a` char(30) DEFAULT NULL
    ) ENGINE=MEMORY DEFAULT CHARSET=latin1;
    #...done.
    # Source on localhost: ... connected.
    USE util_test;
    # Exporting data from util_test
    # Data for table util_test.t1: 
    INSERT INTO util_test.t1 VALUES ('01 Test Basic database example');
    INSERT INTO util_test.t1 VALUES ('02 Test Basic database example');
    INSERT INTO util_test.t1 VALUES ('03 Test Basic database example');
    INSERT INTO util_test.t1 VALUES ('04 Test Basic database example');
    INSERT INTO util_test.t1 VALUES ('05 Test Basic database example');
    INSERT INTO util_test.t1 VALUES ('06 Test Basic database example');
    INSERT INTO util_test.t1 VALUES ('07 Test Basic database example');
    #...done.
    #
    # Connecting to the current server's master
    CHANGE MASTER TO MASTER_HOST = 'localhost', 
      MASTER_USER = 'rpl', 
      MASTER_PASSWORD = 'rpl', 
      MASTER_PORT = 3310, 
      MASTER_LOG_FILE = 'clone-bin.000001' , 
      MASTER_LOG_POS = 1739;
    #
    # Starting slave
    START SLAVE;
    #

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
