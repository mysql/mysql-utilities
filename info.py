#
# Copyright (c) 2010, 2013, Oracle and/or its affiliates. All rights reserved.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301 USA
#

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
