# Keep the imports sorted (alphabetically) in each group. Makes
# merging easier.

import os
import setuptools
import sys

from distutils import log
from distutils.command.build_scripts import build_scripts
from distutils.command.install_data import install_data
from distutils.util import convert_path

import distutils.core

import mysql.utilities

META_INFO = {
    'description':      'MySQL Utilities',
    'maintainer':       'MySQL Utilities Team',
    'maintainer_email': "internals@lists.mysql.com", # !!!
    'version':          mysql.utilities.VERSION_STRING,
    'url':              'http://launchpad.net/???', # !!! Launchpad URL
    'classifiers': [
        'Development Status :: 3 - Alpha',
        'Programming Language :: Python :: 2.6',
        'Environment :: Console',
        'Environment :: Win32 (MS Windows)',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Intended Audience :: Database Administrators',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: OS Independent',
        'Operating System :: POSIX',
        'Topic :: Utilities',
        ],
    }

INSTALL = {
    'packages': [
        "mysql.utilities",
        "mysql.utilities.command",
        "mysql.utilities.common",
        ],
    'scripts': [
        'scripts/mysqldbcopy.py',
        'scripts/mysqlexport.py',
        'scripts/mysqlimport.py',
        'scripts/mysqlindexcheck.py',
        'scripts/mysqlmetagrep.py',
        'scripts/mysqlprocgrep.py',
        'scripts/mysqlreplicate.py',
        'scripts/mysqlserverclone.py',
        'scripts/mysqluserclone.py',
        ],
    'data_files': [
        ('man/man1', [
                'build/sphinx/man/mysqldbcopy.1',
                'build/sphinx/man/mysqlexport.1',
                'build/sphinx/man/mysqlimport.1',
                'build/sphinx/man/mysqlindexcheck.1',
                'build/sphinx/man/mysqlmetagrep.1',
                'build/sphinx/man/mysqlprocgrep.1',
                'build/sphinx/man/mysqlreplicate.1',
                'build/sphinx/man/mysqlserverclone.1',
                'build/sphinx/man/mysqluserclone.1',
                'build/sphinx/man/mut.1',
                ] ),
        ],
    }

ARGS = {
    'test_suite': 'tests.test_all',
}

if sys.platform.startswith("win32"):
    from cx_Freeze import setup, Executable
    META_INFO['name'] = 'MySQL Utilities'
    ARGS.update({
            'executable': [
                Executable(exe, base="Console") for exe in INSTALL['scripts']
                ],
            'options': { 'bdist_msi': { 'add_to_path': True, },
                }
            })
else:
    from distutils.core import setup
    META_INFO['name'] = 'mysql-utilities'

class MyInstallData(install_data):
    """Class for providing a customized version of install_data.

    Before installing the data, the manuals will be built since these
    are considered data from the view of distutils.
    """

    def run(self):
        self.run_command('build_man')
        # distutils is compatible with 2.1 so we cannot use super() to
        # call it.
        install_data.run(self)

class MyBuildScripts(build_scripts):
    """Class for providing a customized version of build_scripts.

    When ``run`` is called, this command class will:
    1. Create a copy of all ``.py`` files in the **scripts** option
       that does not have the ``.py`` extension.
    2. Replace the list in the **scripts** attribute with a list
       consisting of the script files with the ``.py`` extension
       removed.
    3. Call run method in `distutils.command.build_scripts`.
    4. Restore the scripts list to the old value, for other commands
       to use."""

    def run(self):
        if not self.scripts:
            return
        saved_scripts = self.scripts
        self.scripts = []
        for script in saved_scripts:
            script = convert_path(script)
            script_copy, script_ext = os.path.splitext(script)

            if script_ext != '.py':
                log.debug("Not removing extension from %s since it's not '.py'", script)
            else:
                log.debug("Copying %s -> %s", script, script_copy)
                self.copy_file(script, script_copy)
                self.scripts.append(script_copy)
        # distutils is compatible with 2.1 so we cannot use super() to
        # call it.
        build_scripts.run(self)
        self.scripts = saved_scripts


COMMANDS = {
    'cmdclass': {
        'build_scripts': MyBuildScripts,
        'install_data': MyInstallData,
        },
    }

ARGS.update(META_INFO)
ARGS.update(INSTALL)
ARGS.update(COMMANDS)
setup(**ARGS)
