===============================
 mut - MySQL Utilities Testing 
===============================

-------------------------------------------------------
run system and acceptance tests on the MySQL Utilities
-------------------------------------------------------

:Author: The Oracle MySQL Utilities team
:Date: 2010-08-27
:Copyright: GPL
:Version: 1.0.0
:Manual group: database 

SYNOPSIS
========

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
===========

This document describes the ``mut`` utility. This utility is designed to
execute predefined tests to test the MySQL utilities.

You can select any number of tests to run, select one or more suites to
restrict the tests, exclude suites and tests, and specify the location of
the utilities and tests.

The utility requires the existance of at least one server with which to use to
clone for testing purposes. You must specify at least one server, but you may
specify multiple servers for tests designed to use existing servers.

For example, to execute all available tests using a mysql instance on the
local machine with the root user, you can execute the following command.

::

 mut.py --server:root:xxxx@localhost:3306

OPTIONS
=======

--version              show program's version number and exit

--help                 show this help message and exit

--server=<user:passwd@host:port:socket>
                       connection information for a server to be used in the
                       tests in the form: user:passwd@host:port:socket -
                       list option multiple times for multiple servers to use

--do-test=<prefix>     execute all tests that begin with this string

--suite=<suite>        test suite to execute - list option multiple times for
                       multiple suites

--skip-test=SKIP_TEST  exclude a test - list option multiple times for
                        multiple tests
--skip-tests=SKIP_TESTS
                       exclude tests that begin with this string

--start-test=START_TEST
                       start executing tests that begin with this string

--skip-long            exclude tests that require greater resources or take a
                       long time to run

--testdir=<path>       path to test directory

--start-port=<num>     starting port for spawned servers

--record               record output of specified test if successful - works
                       with only one test selected

--sorted               execute tests sorted by suite.name (default = True)

--utildir=<path>       path to utility directory

--width=<num>          display width

-f, --force            do not abort when a test fails

-v, --verbose          display additional information during operation

-d, --debug            display actual results of test cases to screen and
                       ignore result processing - used to diagnose test
                       execution problems

FILES
=====

 - **mut.py**          the utility script
 - **mysql**           the MySQL utilities library
 - **mysql_util**      the MySQL testing library

NOTES
=====

The information specified for the server must be a valid login account.
