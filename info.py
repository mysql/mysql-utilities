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
    'maintainer_email': "gui-tools@lists.mysql.com",
    'version': mysql.utilities.VERSION_STRING,
    'url': 'http://launchpad.net/mysql-utilities',
    'license': 'GNU GPLv2 (with FOSS License Exception)',
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
