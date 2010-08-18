import sys
import os
import distutils.core
import cx_Freeze

META_INFO = {
    'name':             'mysql-utilities',
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

INSTALL = {
    'packages': ["mysql"],
    'scripts': [
        'scripts/mysqlproc.py'
        ],
    }

class TestCommand(distutils.core.Command):
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
    'cmdclass': { 'test': TestCommand },
    }

ARGS = {
    'executables': [cx_Freeze.Executable(exe) for exe in INSTALL['scripts']],
    }
    
ARGS.update(META_INFO)
ARGS.update(INSTALL)
ARGS.update(COMMANDS)
cx_Freeze.setup(**ARGS)
