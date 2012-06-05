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

To get help for ``setup.py``, you can do::

    python setup.py --help

To get a complete list of commands available for ``setup.py``, you can
do::

    python setup.py --help-commands


Requirements
~~~~~~~~~~~~

MySQL Utilities have some dependencies on other packages:
- Python 2.6 or later but Python 3.x is not supported (yet).
- Sphinx version 1.0 or later is needed to build the manuals from
  Sphinx markup. If you do not bother about building the manuals,
  earlier versions of Sphinx work fine, but check what builders are
  available in your installed version of Sphinx.
- Sphinx requires docutils to build the documentation and 0.6 or later
  to build manual pages.
- Sphinx also requires Jinja2 2.1 or later to generate HTML pages.


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

If you have problems with build_* commands not working or not showing
in the help, please check your prerequisites.  Commands are in many
cases not installed if the prerequisites are not met; this is
deliberate.


Documentation
-------------

If you have Sphinx installed, you can build documentation is a variety
of different formats such as HTML, EPUB, and Unix manual pages.

To create documentation in HTML format::

    python setup.py build_sphinx -b html

To create documentation in man format either one of the following
commands can be used::

    python setup.py build_sphinx -b man
    python setup.py build_man

NOTE: Building Unix manual pages require Sphinx version 1.0 or later and
docutils 0.6 or later.

Manual pages are currently not pre-generated, so you have to build
them to get them installed.

To create documentation in EPUB format::

    python setup.py build_sphinx -b epub

For more information on Sphinx:

   http://sphinx.pocoo.org/


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

If you need to test a version of mysql.connector together with
mysql.utilities without installing it first, special care have to be
taken.  Since both packages live in the 'mysql' package, they are
expected to be found in the same directory.  For that reason, you
first have to install both mysql.connector and mysql.utilities in a
temporary directory and add this to PYTHONPATH.

  # cd repository for mysql.connector
  python setup.py build -b /temp/something
  # cd to repository for mysql.utilities
  python setup.py build -b /temp/something
  cd mysql-test
  PYTHONPATH=/temp/something/lib.* python mut.py --server=<as above>

Operating System Notes
----------------------

The MySQL Utilities are designed to run on any platform that supports
Python 2.6 or higher. You should ensure you have Python and all the
pre-requisites listed above installed and configured correctly before
installing the utilities.

There are no known issues on any platform.


Reporting bugs
--------------

Bugs are reported in the Oracle/MySQL bugs system at:

    http://bugs.mysql.com/


Contributors
------------

Mats Kindahl <mats.kindahl@oracle.com>
Charles Bell <chuck.bell@oracle.com>
