.. _ `mysqlmetagrep`:

#############################################
``mysqlmetagrep`` - Search object definitions
#############################################

SYNOPSIS
--------

  mysqlmetagrep [ <options> ] --pattern=<pattern> --server=user:pass@host:port:socket ...

DESCRIPTION
-----------

This utility searches for objects on all the servers provided via repeated
occurrences of the --server option matching a given pattern
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

.. option:: --type <type>,...

   Only search for/in objects of type <type>, where <type> can be:
   **procedure**, **function**, **event**, **trigger**, **table**, or
   **database**.
  
   Default is to search for/in all kinds of types.

.. option:: --body, -b

   Search the body of procedures, functions, triggers, and
   events. Default is to only match the name.

.. option:: --regexp, --basic-regexp, -G

   Perform the match using the **REGEXP** operator. Default is to use
   **LIKE** for matching.

.. option:: --sql, --print-sql, -p

   Print the SQL code that will be executed to find all matching
   objects. This can be useful if you want to safe the statement for
   later execution, or pipe it into other tools.

.. option:: --pattern <pattern>, -e <pattern>

   Pattern to use when matching. This is required when the pattern
   looks like a connection specification.

   If a pattern option is given, the first argument is not treated as
   a pattern but as a connection specifier.

.. option:: --database <pattern>

   Only look in databases matching this pattern.

.. option:: --version

   Print the version and exit.

.. option:: --help, -h

   Print help.


EXAMPLES
--------

Find all objects where the name match the pattern ``'t\_'``::

    $ mysqlmetagrep 't_' --server=mats@localhost
    +------------------------+--------------+--------------+-----------+
    | Connection             | Object Type  | Object Name  | Database  |
    +------------------------+--------------+--------------+-----------+
    | mats:*@localhost:3306  | TABLE        | t1           | test      |
    | mats:*@localhost:3306  | TABLE        | t2           | test      |
    | mats:*@localhost:3306  | TABLE        | t3           | test      |
    +------------------------+--------------+--------------+-----------+

To find all object that contain ``'t2'`` in the name or the body (for
routines, triggers, and events)::

    $ mysqlmetagrep -b '%t2%' --server=mats@localhost:3306
    +------------------------+--------------+--------------+-----------+
    | Connection             | Object Type  | Object Name  | Database  |
    +------------------------+--------------+--------------+-----------+
    | root:*@localhost:3306  | TRIGGER      | tr_foo       | test      |
    | root:*@localhost:3306  | TABLE        | t2           | test      |
    +------------------------+--------------+--------------+-----------+

Same thing, but using the **REGEXP** operator::

    $ mysqlmetagrep -Gb 't2' --server=mats@localhost
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
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
USA
