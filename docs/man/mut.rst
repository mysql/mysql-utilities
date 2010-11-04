.. _`mut`:

#################################
``mut`` - MySQL Utilities Testing
#################################


SYNOPSIS
--------

::

 mut [[--help | --version ] | --verbose | --sorted | --record |
            --utildir=<path> | --width=<num> | --start-port=<num> |
            --testdir=<path> | --do-test=<prefix> | --force |
            [ --server=<user:passwd@host:port:socket> |
            [, --server=<user:passwd@host:port:socket> ] |
            [ --suite=<suite> | [, --suite=<suite> ]] |
            [ --skip-suite=<suite> | [, --skip-suite=<suite> ]] |
              --skip-tests=<test_prefix> | --skip-long |
            [ --skip-test=<test> | [, --skip-test=<test> ]] |
            [ <test> | <suite>.<test> | [, <test> | <suite>.<test> ]]

DESCRIPTION
-----------

This utility is designed to execute predefined tests to test the MySQL
utilities.

You can select any number of tests to run, select one or more suites to
restrict the tests, exclude suites and tests, and specify the location of
the utilities and tests.

The utility requires the existance of at least one server with which to use to
clone for testing purposes. You must specify at least one server, but you may
specify multiple servers for tests designed to use existing servers.

For example, to execute all available tests using a mysql instance on the
local machine with the root user, you can execute the following command::

  mut.py --server:root:xxxx@localhost:3306

OPTIONS
-------

.. option:: --version

   Show program's version number and exit

.. option:: --help

   Show this help message and exit

.. option:: --server <server>

   Server given by *server* will be used in the tests. The format of
   *server* is given in :ref:`connspec`. List option multiple times
   for multiple servers to use

.. option:: --do-test <prefix>

    Execute all tests that begin with *prefix*.

.. option:: --suite <suite>

   test suite to execute - list option multiple times for multiple
   suites

.. option:: --skip-test <test>

   exclude *test* - list option multiple times for multiple tests

.. option:: --skip-tests <tests>

   exclude *tests* that begin with this string

.. option:: --start-test <prefix>

   start executing tests that begin with *prefix*

.. option:: --skip-long

   exclude tests that require greater resources or take a long time to
   run

.. option:: --testdir <path>

   Path to test directory

.. option:: --start-port <port>

   starting port for spawned servers

.. option:: --record

   record output of specified test if successful - works with only one
   test selected

.. option:: --sorted

   execute tests sorted by suite.name (default = True)

.. option:: --utildir <path>

   Path to utility directory

.. option:: --width <number>

   Display width

.. option:: --force, -f

   Do not abort when a test fails

.. option:: --verbose, -v

   display additional information during operation

.. option:: --debug, -d

   display actual results of test cases to screen and ignore result
   processing - used to diagnose test execution problems

NOTES
-----

The information specified for the server must be a valid login
account.

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
