
import distutils.command.build_scripts
import distutils.util
import glob
import os

import mysql.utilities

META_INFO = {
    'name': 'mysql-utilities',
    'description': 'MySQL Utilities ' + mysql.utilities.RELEASE_STRING,
    'maintainer': 'Oracle',
    'maintainer_email': '',
    'version': mysql.utilities.VERSION_STRING,
    'url': 'http://dev.mysql.com',
    'license': 'GNU GPLv2 (with FOSS License Exception)',
    'classifiers': [
        'Development Status :: 3 - Alpha',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
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
        'mysql',
        'mysql.utilities',
        'mysql.utilities.command',
        'mysql.utilities.common',
        ],
    'scripts': glob.glob('scripts/*.py'),
    'requires': [
        'distutils',
        'sphinx (>=1.0)',
        'jinja2 (>=2.1)',
        ],
    'provides': [
        'mysql.utilities',
        ],
    }
