# Boilerplate code to install setuptools if it is not installed
import ez_setup
ez_setup.use_setuptools()

import distutils.command.build_scripts
import distutils.util
import glob
import setuptools
import os

import mysql.utilities

META_INFO = {
    'name': 'mysql-utilities',
    'description': 'MySQL Utilities',
    'maintainer': 'MySQL Utilities Team',
    'maintainer_email': "internals@lists.mysql.com", # !!!
    'version': mysql.utilities.VERSION_STRING,
    'url': 'http://launchpad.net/???', # !!! Launchpad URL
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
    'packages': setuptools.find_packages(exclude=["tests"]),
    'scripts': glob.glob('scripts/*.py'),
    'setup_requires': [
        'Sphinx >=1.0',
        ],
    }

class MyBuildScripts(distutils.command.build_scripts.build_scripts):
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
        from distutils import log
        if not self.scripts:
            return
        saved_scripts = self.scripts
        self.scripts = []
        for script in saved_scripts:
            script = distutils.util.convert_path(script)
            script_copy, script_ext = os.path.splitext(script)

            if script_ext != '.py':
                log.debug("Not removing extension from %s since it's not '.py'", script)
            else:
                log.debug("Copying %s -> %s", script, script_copy)
                self.copy_file(script, script_copy)
                self.scripts.append(script_copy)
        # distutils is compatible with 2.1 so we cannot use super() to
        # call it.
        distutils.command.build_scripts.build_scripts.run(self)
        self.scripts = saved_scripts


COMMANDS = {
    'cmdclass': {
        'build_scripts': MyBuildScripts,
        },
    }

