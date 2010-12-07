###############
MySQL Utilities
###############

MySQL Utilities contain a collection of scripts useful for managing
and administering MySQL servers.

Installation
------------

To install the scripts together with the libraries::

    python setup.py install

In order for the installation from source to work correctly, you have
to have Python installed on your computer and also Connector/Python.

Note: for some platforms, you may need to execute this command with
administrative privileges.


Windows Notes
~~~~~~~~~~~~~

If you are using Windows, you have to ensure that the script directory
is in the path and that the Python extensions are recognized as script
files.  The procedures are a little different between Windows
PowerShell and a normal CMD shell, so we outline both procedures.

To ensure that the Python extensions are recognized as script files,
you have to add the extensions to the PATHEXT variable. In a CMD
Window, this is done using::

    set PATHEXT="%PATHEXT%;.PY;.PYW;.PYC;.PYO"

and in a PowerShell you do this using::

    $env:PATHEXT="$env:PATHEXT;.PY;.PYW;.PYC;.PYO"

If you have Python installed, it will already have mappings for .PY
(Python script), .PYW (Python Windowless Application), .PYC (Compiled
Python Script), and .PYO (Compiled and Optimized Python Script).


Documentation
-------------

To create documentation in html format::

    python setup.py build_sphinx -b html

To create documentation in man format::

    python setup.py build_sphinx -b man
or
    python setup.py build_man

To create documentation in epub format::

    python setup.py build_sphinx -b epub

Unit Tests
----------

To run the existing unit tests::

    python setup.py test

Systems Tests
-------------

To execute the system and acceptance tests created for the utilities, change
to the /test directory and execute::

    python mut.py --server=<user>:<passwd>@<host>:<port>:<socket>

You will need to supply a specific user, password (optional), host, port
(optional), and socket (optional) to connect to a running instance of MySQL
for use in running the tests. By default, the command above will execute all
tests. You can specify one or more tests as arguments to the command. See the
manual for more information about the MySQL Utilities Testing utility (mut).

Operating System Notes
----------------------

The MySQL Utilities are designed to run on any platform that supports Python
2.6 or higher. You should ensure you have Python installed and configured
correctly before installing.

There are no known issues on any platform.

Contributors
------------

Mats Kindahl <mats.kindahl@oracle.com>
Charles Bell <chuck.bell@oracle.com>
