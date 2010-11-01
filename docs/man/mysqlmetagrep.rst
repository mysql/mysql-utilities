#############
mysqlmetagrep
#############

SYNOPSIS
========

  mysqlmetagrep [ OPTIONS ] PATTERN [ SERVER ] ...

DESCRIPTION
===========

This utility searches for objects on a server matching a given pattern
and show a table of the objects that match. The first non-option
argument it taken to be the pattern unless the :option:`--pattern`
option is used, in which case all non-option arguments are treated as
connection specifications.

Internally, the utility creates an SQL statement for searching the
necessary tables in the **INFORMATION_SCHEMA** database on the
provided servers and executes it in turn before collecting the result
and printing it as a table. If you do not want to send the statement
to the servers and instead have the utility emit the statement, you
can use the :option:`--sql` option. This can be useful if you want to
feed the output of the statement to other utilities such as
:manpage:`mysqlevent(1)`.

Normally, the **LIKE** operator is used to match the name (and
optionally, the body) but this can be changed to use the **REGEXP**
operator instead by using the :option:`--regexp` option.

Note that since the **REGEXP** operator does a substring searching, it
is necessary to anchor the expression to the beginning of the string
if you want to match the beginning of the string. 

Options
-------

.. option:: --type=TYPE,...

   Only search for/in objects of type TYPE, where TYPE can be:
   **procedure**, **function**, **event**, **trigger**, **table**, or
   **database**.
  
   Default is to search for/in all kinds of types.

.. option:: -b, --body

   Search the body of procedures, functions, triggers, and
   events. Default is to only match the name.

.. option:: -G, --basic-regexp, --regexp

   Perform the match using the **REGEXP** operator. Default is to use
   **LIKE** for matching.

.. option:: -p, --print-sql, --sql

   Print the SQL code that will be executed to find all matching
   objects. This can be useful if you want to safe the statement for
   later execution, or pipe it into other tools.

.. option:: -e PATTERN, --pattern=PATTERN

   Pattern to use when matching. This is required when the pattern
   looks like a connection specification.

   If a pattern option is given, the first argument is not treated as
   a pattern but as a connection specifier.

.. option:: --database=PATTERN

   Only look in databases matching this pattern.

.. option:: --version

   Print the version and exit.

.. option:: -h, --help

   Print help.


EXAMPLES
========

Find all objects where the name match the pattern 't\_'::

    $ mysqlmetagrep 't_' mats@localhost
    +------------------------+--------------+--------------+-----------+
    | Connection             | Object Type  | Object Name  | Database  |
    +------------------------+--------------+--------------+-----------+
    | mats:*@localhost:3306  | TABLE        | t1           | test      |
    | mats:*@localhost:3306  | TABLE        | t2           | test      |
    | mats:*@localhost:3306  | TABLE        | t3           | test      |
    +------------------------+--------------+--------------+-----------+

To find all object that contain 't2' in the name or the body (for
routines, triggers, and events)::

    $ mysqlmetagrep -b '%t2%' mats@localhost:3306
    +------------------------+--------------+--------------+-----------+
    | Connection             | Object Type  | Object Name  | Database  |
    +------------------------+--------------+--------------+-----------+
    | root:*@localhost:3306  | TRIGGER      | tr_foo       | test      |
    | root:*@localhost:3306  | TABLE        | t2           | test      |
    +------------------------+--------------+--------------+-----------+

Same thing, but using the **REGEXP** operator::

    $ mysqlmetagrep -Gb 't2' mats@localhost
    +------------------------+--------------+--------------+-----------+
    | Connection             | Object Type  | Object Name  | Database  |
    +------------------------+--------------+--------------+-----------+
    | root:*@localhost:3306  | TRIGGER      | tr_foo       | test      |
    | root:*@localhost:3306  | TABLE        | t2           | test      |
    +------------------------+--------------+--------------+-----------+
