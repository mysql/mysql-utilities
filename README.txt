===============
MySQL Utilities
===============

MySQL Utilities contain a collection of scripts useful for managing
and administering MySQL servers.

Installation
============

To install the scripts together with the libraries::

    python setup.py install

Note: for some platforms, you may need to execute this command with
administrative privileges.

Documentation
=============

To create documentation in html format::

    python setup.py build_sphinx -b html

To create documentation in man format::

    python setup.py build_sphinx -b man
or
    python setup.py build_man

To create documentation in epub format::

    python setup.py build_sphinx -b epub

Unit Tests
==========

To run the existing unit tests::

    python setup.py test

Systems Tests
=============

To execute the system and acceptance tests created for the utilities, change
to the /test directory and execute::

    python mut.py --server=<user>:<passwd>@<host>:<port>:<socket>

You will need to supply a specific user, password (optional), host, port
(optional), and socket (optional) to connect to a running instance of MySQL
for use in running the tests. By default, the command above will execute all
tests. You can specify one or more tests as arguments to the command. See the
manual for more information about the MySQL Utilities Testing utility (mut).

Operating System Notes
======================

The MySQL Utilities are designed to run on any platform that supports Python
2.6 or higher. You should ensure you have Python installed and configured
correctly before installing.

There are no known issues on any platform.

Contributors
============

Mats Kindahl <mats.kindahl@oracle.com>
Charles Bell <chuck.bell@oracle.com>
