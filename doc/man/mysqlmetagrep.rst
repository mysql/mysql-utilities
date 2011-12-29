.. _ `mysqlmetagrep`:

#############################################
``mysqlmetagrep`` - Search Object Definitions
#############################################

SYNOPSIS
--------

  mysqlmetagrep [ --version | --help ] | --format=<format> |
                --body | --types<object types> | --regexp | --sql |
                --database=<pattern> | --pattern=<pattern>
                --server=<user>[<passwd>]@<host>:[<port>][:<socket>]

DESCRIPTION
-----------

This utility searches for objects on all the servers provided via
repeated occurrences of the :option:`--server` option matching a given
pattern and show a table of the objects that match. The first
non-option argument it taken to be the pattern unless the
:option:`--pattern` option is used, in which case all non-option
arguments are treated as connection specifications.

Internally, the utility creates an SQL statement for searching the
necessary tables in the **INFORMATION_SCHEMA** database on the
provided servers and executes it in turn before collecting the result
and printing it as a table. If you do not want to send the statement
to the servers and instead have the utility emit the statement, you
can use the :option:`--sql` option. This can be useful if you want to
feed the output of the statement to other utilities such as
:manpage:`mysqlevent(1)`.

The MySQL server uses two forms of patterns when matching strings:
:ref:`simple_pattern` and :ref:`posix_regexp`.

Normally, the **LIKE** operator is used to match the name (and
optionally, the body) but this can be changed to use the **REGEXP**
operator instead by using the :option:`--regexp` option.

Note that since the **REGEXP** operator does a substring searching, it
is necessary to anchor the expression to the beginning of the string
if you want to match the beginning of the string.

To specify how to display output, use one of the following values
with the :option:`--format` option:

**GRID** (default)
  Display output formatted like that of the mysql monitor in a grid
  or table layout.

**CSV**
  Display output in comma-separated values format.

**TAB**
  Display output in tab-separated format.

**VERTICAL**
  Display output in a single column similar to the ``\G`` command
  for the mysql monitor.


.. _simple_pattern:

SQL Simple Patterns
^^^^^^^^^^^^^^^^^^^

The simple patterns defined by SQL standard consist of a string of
characters with two characters that have special meaning: **%**
(percent) matches zero or more characters and **_** (underscore)
matches exactly one character.

For example:

``'mats%'``
  Matches any string that starts with 'mats'.
``'%kindahl%'``
  Matches any string consisting containing the word 'kindahl'.
``'%_'``
  Matches any string consisting of one or more characters.


.. _posix_regexp:

POSIX Regular Expressions
^^^^^^^^^^^^^^^^^^^^^^^^^

POSIX regular expressions are more powerful than the simple patterns
defined in the SQL standard. A regular expression is a string of
characters, optionally containing characters with special meaning:

**.**
   Matches any character.
**^**
   Matches the beginning of a string.
**$**
   Matches the end of a string.
**[axy]**
   Matches either **a**, **x**, or **y**.
**[a-f]**
   Matches any character in the range **a** to
   **f** (that is, **a**, **b**, **c**, **d**,
   **e**, or **f**).
**[^axy]**
   Matches any character *except* **a**, **x**,
   or **y**.
**a\***
   Matches a sequence of zero or more **a**.
**a+**
   Matches a sequence of one or more **a**.
**a?**
   Matches zero or one **a**.
**ab|cd**
   Matches either **ab** or **cd**.
**a{5}**
   Matches 5 instances of **a**.
**a{2,5}**
   Matches between 2 and 5 instances of **a**.
**(abc)+**
   Matches one or more repetitions of **abc**.

This is but a brief set of examples of regular expressions. The full
syntax is described in the `MySQL manual`_, but can often be found in
:manpage:`regex(7)`.

.. _`MySQL manual`: http://dev.mysql.com/doc/mysql/en/regexp.html


OPTIONS
-------

.. option:: --help, -h

   Display a help message and exit.

.. option:: --body, -b

   Search the body of procedures, functions, triggers, and
   events. Default is to only match the name.

.. option:: --database=<pattern>

   Only look in databases matching this pattern.

.. option:: --format=<format>, -f<format>

   Display the output in either GRID (default), TAB, CSV, or VERTICAL format.

.. option:: --pattern=<pattern>, -e=<pattern>

   Pattern to use when matching. This is required when the pattern
   looks like a connection specification.

   If a pattern option is given, the first argument is not treated as
   a pattern but as a connection specifier.

.. option:: --regexp, --basic-regexp, -G

   Perform the match using the **REGEXP** operator. Default is to use
   **LIKE** for matching.

.. option:: --search-objects=<type>, ...
            --object-types=<type>, ...

   Only search for/in objects of type <type>, where <type> can be:
   **procedure**, **function**, **event**, **trigger**, **table**, or
   **database**.

   Default is to search in objects of all kinds of types.

.. option:: --server=<source>

   Connection information for the servers to search in the form:
   <user>:<password>@<host>:<port>:<socket>
   The option may be repeated to form a list of servers to search.

.. option::  --sql, --print-sql, -p

   Print the SQL code that will be executed to find all matching
   objects. This can be useful if you want to safe the statement for
   later execution, or pipe it into other tools.

.. option:: --version

   Display version information and exit.


EXAMPLES
--------

Find all objects where the name match the pattern ``'t\_'``::

    $ mysqlmetagrep --pattern="t_" --server=mats@localhost
    +------------------------+--------------+--------------+-----------+
    | Connection             | Object Type  | Object Name  | Database  |
    +------------------------+--------------+--------------+-----------+
    | mats:*@localhost:3306  | TABLE        | t1           | test      |
    | mats:*@localhost:3306  | TABLE        | t2           | test      |
    | mats:*@localhost:3306  | TABLE        | t3           | test      |
    +------------------------+--------------+--------------+-----------+

To find all object that contain ``'t2'`` in the name or the body (for
routines, triggers, and events)::

    $ mysqlmetagrep -b --pattern="%t2%" --server=mats@localhost:3306
    +------------------------+--------------+--------------+-----------+
    | Connection             | Object Type  | Object Name  | Database  |
    +------------------------+--------------+--------------+-----------+
    | root:*@localhost:3306  | TRIGGER      | tr_foo       | test      |
    | root:*@localhost:3306  | TABLE        | t2           | test      |
    +------------------------+--------------+--------------+-----------+

Same thing, but using the **REGEXP** operator. Note that it is not
necessary to add wildcards before the pattern::

    $ mysqlmetagrep -Gb --pattern="t2" --server=mats@localhost
    +------------------------+--------------+--------------+-----------+
    | Connection             | Object Type  | Object Name  | Database  |
    +------------------------+--------------+--------------+-----------+
    | root:*@localhost:3306  | TRIGGER      | tr_foo       | test      |
    | root:*@localhost:3306  | TABLE        | t2           | test      |
    +------------------------+--------------+--------------+-----------+


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
