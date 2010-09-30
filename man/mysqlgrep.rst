=========
mysqlgrep
=========

------------------------------
Search for objects on a server
------------------------------

:Author: The Oracle MySQL Utilities team
:Date: 2010-09-29
:Copyright: GPL
:Manual section: 1


SYNOPSIS
========

  mysqlgrep [ OPTIONS ] PATTERN [ SERVER ] ...

DESCRIPTION
===========

This utility searches for objects on a server matching a given pattern
and print them as a `simple table in reStructuredText format`__.

.. __: http://docutils.sourceforge.net/docs/ref/rst/restructuredtext.html#simple-tables

Interlly, the utility creates an SQL statement for searching the necessary
tables in the ``INFORMATION_SCHEMA`` database on the provided
servers and executes it in turn before collecting the result and
printing it as a table.

Normally, the ``LIKE`` operator is used to match the name (and
optionally, the body) but this can be changed to use the ``REGEXP``
operator instead by using the `--basic-regexp`_ option.

Note that since the ``REGEXP`` operator does a substring searching, it
is necessary to anchor the expression to the beginning of the string
if you want to match the beginning of the string.

It is also possible to emit the generated SQL code on the standard
output by using the `--print-sql`_ option described below.

Options
-------

--type=TYPE,...
  Only search for/in objects of type TYPE, where TYPE can be:
  ``procedure``, ``function``, ``event``, ``trigger``, ``table``,
  or ``database``.
  
  Default is to search for/in all kinds of types.  

-b, --body
  Search the body of procedures, functions, triggers, and
  events. Default is to only match the name.

-G, --basic-regex, --regexp
  Perform the match using the ``REGEXP`` operator. Default is to use
  ``LIKE`` for matching.

-p, --print-sql, --sql
  Print the SQL code that will be executed to find all matching
  objects. This can be useful if you want to safe the statement for
  later execution, or pipe it into other tools.

--help
  Print help.


EXAMPLES
========

Find all objects where the name match the pattern 't_'::

    $ mysqlgrep 't_' mats@localhost
    ==============  =====  ====  ========  
    Server          Type   Name  Database  
    ==============  =====  ====  ========  
    mats@localhost  TABLE  t1    test      
    mats@localhost  TABLE  t2    test      
    ==============  =====  ====  ========  

To find all object that contain 't2' in the name or the body (for
routines, triggers, and events)::

    $ mysqlgrep -b '%t2%' mats@localhost:3306
    ===================  =======  ======  ========  
    Server               Type     Name    Database  
    ===================  =======  ======  ========  
    mats@localhost:3306  TRIGGER  tr_foo  test      
    mats@localhost:3306  TABLE    t2      test      
    ===================  =======  ======  ========  

Same thing, but using the ``REGEXP`` operator::

    $ mysqlgrep -Gb 't2' mats@localhost
    ===================  =======  ======  ========  
    Server               Type     Name    Database  
    ===================  =======  ======  ========  
    mats@localhost:3306  TRIGGER  tr_foo  test      
    mats@localhost:3306  TABLE    t2      test      
    ===================  =======  ======  ========  
