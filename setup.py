import sys
import os
from distutils.core import Command
from cx_Freeze import setup, Executable

META_INFO = {
    'description':      'MySQL Command-line Utilities',
    'maintainer':       'MySQL',         # !!!
    'maintainer_email': "internals@lists.mysql.com", # !!!
    'version':          '0.1.0',
    'url':              'http://launchpad.net/???', # !!! Launchpad URL
    'classifiers': [
        'Programming Language :: Python',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: OS Independent',
        'Operating System :: POSIX',
        ],
    }

if sys.platform.startswith("win32"):
    META_INFO['name'] = 'MySQL Utilities'
else:
    META_INFO['name'] = 'mysql-utilities'

INSTALL = {
    'packages': ["mysql"],
    'scripts': [
        'scripts/mysqlproc.py'
        ],
    }

class CheckCommand(Command):
    """
    Command to execute all unit tests in the tree.
    """
    user_options = [ ]

    def initialize_options(self):
        self._dir = os.getcwd()
        # Install mock database
        # @todo add option to use real database later
        import tests.MySQLdb
        sys.modules['MySQLdb'] = tests.MySQLdb

    def finalize_options(self):
        pass

    def run(self):
        "Finds all the tests modules in tests/, and runs them."

        import unittest
        import tests.command
        suite = unittest.TestSuite()
        suite.addTest(tests.command.suite())
        runner = unittest.TextTestRunner(verbosity=1)
        runner.run(suite)

COMMANDS = {
    'cmdclass': { 'check': CheckCommand },
    }

ARGS = {
    'executables': [Executable(exe) for exe in INSTALL['scripts']],
    }
    
ARGS.update(META_INFO)
ARGS.update(INSTALL)
ARGS.update(COMMANDS)
setup(**ARGS)
