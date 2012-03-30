.. _`mut`:

#################################
``mut`` - MySQL Utilities Testing
#################################

SYNOPSIS
--------

::

 mut [options] [suite_name.]test_name ...

DESCRIPTION
-----------

This utility executes predefined tests to test the MySQL
Utilities. The tests are located under the ``/mysql-test`` directory and divided into suites (stored as folders). By default,
all tests located in the ``/t`` folder are considered the 'main' suite.

You can select any number of tests to run, select one or more suites to
restrict the tests, exclude suites and tests, and specify the location of
the utilities and tests.

The utility requires the existence of at least one server to
clone for testing purposes. You must specify at least one server, but you may
specify multiple servers for tests designed to use additional servers.

The utility has a special test suite named 'performance' where
performance-related tests are placed. This suite is not included
by default and must be specified with the :option:`--suite` option
to execute the performance tests.

OPTIONS
-------

:command:`mut` accepts the following command-line options:

.. option:: --help

   Display a help message and exit.

.. option:: --do-tests=<prefix>

   Execute all tests that begin with *prefix*.

.. option:: --force

   Do not abort when a test fails.

.. option:: --record

   Record the output of the specified test if successful. With this option,
   you must specify exactly one test to run.

.. option:: --server=<server>

   Connection information for the server to use in the tests, in
   <*user*>[:<*passwd*>]@<*host*>[:<*port*>][:<*socket*>] format.
   Use this option multiple times to specify multiple servers.

.. option:: --skip-long

   Exclude tests that require greater resources or take a long time to
   run.

.. option:: --skip-suite=<name>

   Exclude the named test suite.  Use this option multiple times
   to specify multiple suites.

.. option:: --skip-test=<name>

   Exclude the named test.  Use this option multiple times to specify
   multiple tests.

.. option:: --skip-tests=<prefix>

   Exclude all tests that begin with *prefix*.

.. option:: --sort

   Execute tests sorted by suite.name either ascending (asc) or descending
   (desc). Default is ascending (asc).

.. option:: --start-port=<port>

   The first port to use for spawned servers. If you run the entire test
   suite, you may see up to 12 new instances created. The default is to
   use ports 3310 to 3321.

.. option:: --start-test=<prefix>

   Start executing tests that begin with *prefix*.

.. option:: --suite=<name>

   Execute the named test suite.  Use this option multiple times to specify
   multiple suites.

.. option:: --testdir=<path>

   The path to the test directory.

.. option:: --utildir=<path>

   The location of the utilities.

.. option:: --verbose, -v

   Specify how much information to display. Use this option
   multiple times to increase the amount of information.  For example,
   :option:`-v` = verbose, :option:`-vv` = more verbose, :option:`-vvv` =
   debug. To diagnose test execution problems, use :option:`-vvv` to display
   the actual results of test cases and ignore result processing.

.. option:: --version

   Display version information and exit.

.. option:: --width=<number>

   Specify the display width. The default is 75 characters.

NOTES
-----

The connection specifier must name a valid account for the server.

Any test named *???_template.py* is skipped. This enables the developer
to create a base class to import for a collection of tests based on a common
code base.

EXAMPLES
--------

The following example demonstrates how to invoke :command:`mut` to execute
a subset of the tests using an existing server which is cloned.
The example displays the test name, status, and relative time::

    $ python mut --server=root@localhost --do-tests=clone_user --width=70

    MySQL Utilities Testing - MUT

    Parameters used:
      Display Width       = 70
      Sorted              = True
      Force               = False
      Test directory      = './t'
      Utilities directory = '../scripts'
      Starting port       = 3310
      Test wildcard       = 'clone_user%'

    Servers:
      Connecting to localhost as user root on port 3306: CONNECTED

    ----------------------------------------------------------------------
    TEST NAME                                                STATUS   TIME
    ======================================================================
    main.clone_user                                          [pass]     54
    main.clone_user_errors                                   [pass]     27
    main.clone_user_parameters                               [pass]     17
    ----------------------------------------------------------------------
    Testing completed: Friday 03 December 2010 09:50:06

    All 3 tests passed.

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
