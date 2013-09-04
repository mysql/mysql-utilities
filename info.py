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


def find_packages(*args, **kwrds):
    """Find all packages and sub-packages and return a list of them.

    The function accept any number of directory names that will be
    searched to find packages. Packages are identified as
    sub-directories containing an __init__.py file.  All duplicates
    will be removed from the list and it will be sorted
    alphabetically.

    Packages can be excluded by pattern using the 'exclude' keyword,
    which accepts a list of patterns.  All packages with names that
    match the beginning of an exclude pattern will be excluded.
    
    Root base path can be attached to each package by using 'inc_base'
    keyword.
    """
    from fnmatch import fnmatch
    excludes = kwrds.get('exclude', [])
    inc_base = kwrds.get('inc_base', False)
    pkgs = {}
    for base_path in args:
        for root, _dirs, files in os.walk(base_path):
            if '__init__.py' in files:
                assert root.startswith(base_path)
                pkg = root[len(base_path)+1:].replace(os.sep, '.')
                if inc_base and pkg:
                        pkg = os.path.join(base_path, pkg).replace(os.sep, '.')
                elif inc_base:
                        pkg = base_path.replace(os.sep, '.')
                pkgs[pkg] = root

    result = pkgs.keys()
    for excl in excludes:
        # We exclude packages that *begin* with an exclude pattern.
        result = [pkg for pkg in result if not fnmatch(pkg, excl + "*")]
    result.sort()
    return result


def add_optional_resources(*args, **kwrds):
    """Adds additional resources, as source packages, scripts and data files.

    The function will try to find all resources in the directory names given,
    that will be searched to find packages, data files and scripts.
    
    Packages are identified as sub-directories containing an __init__.py file.
    All duplicates will be removed from the list and it will be sorted
    alphabetically. This function uses the find_packages function; see his
    help to know more how packages are found.

    Scripts must be set on 'scripts', and a list of the desired scripts to add
    must be given by 'scripts' keyword.
    
    Data files can be set in a dictionary with the keyword 
    'data_files', where destination is used as key and a list of source files,
    are the item for that key.
    """
    
    excludes = kwrds.get('exclude', [])
    inc_base = kwrds.get('inc_base', True)
    data_files = kwrds.get('data_files', {})

    packages_found = []

    pkg_base = args[0]
    print('checking {0} for packages to distribute'.format(pkg_base))
    pkgs = find_packages(pkg_base, exclude=excludes, inc_base=inc_base)
    print("packages found: {0}".format(pkgs))
    packages_found.extend(pkgs)

    #if os.path.exists('scripts/mysqlfabric'):
    #    os.rename('scripts/mysqlfabric', 'scripts/mysqlfabric.py')

    scripts_found = []
    for root, _dirs, scripts in os.walk('scripts'):
        for script in scripts:
            script_path = os.path.join('scripts', script)
            if (not script_path.endswith('.py') and 
                not os.path.exists(script_path)):
                os.rename(script_path, '{0}.py'.format(script_path))
                script_path = '{0}.py'.format(script_path)
            if script_path.endswith('.py'):
                scripts_found.append(script_path)

    data_files_found = []
    for root, _dirs, data_files in os.walk('data'):
        datafiles = []
        zipfiles = []
        otherfiles = []
        for src in data_files:
            name, ext = os.path.splitext(src)
            if ext == '.zip' and os.name != 'nt':
                zipfiles.append(os.path.join('data', src))
            else:
                datafiles.append(os.path.join('data', src))
        if datafiles:
            data_files_found.append(('data', datafiles))
        if zipfiles:
            data_files_found.append(('/etc/mysql', zipfiles))
        if otherfiles:
            data_files_found.append(('other', otherfiles))

    if packages_found:
        INSTALL['packages'].extend(packages_found)
        print("package set {0}".format(set(INSTALL['packages'])))
        INSTALL['packages'] = list(set(INSTALL['packages']))
    if scripts_found:
        INSTALL['scripts'].extend(scripts_found)
        INSTALL['scripts'] = list(set(INSTALL['scripts']))
    if data_files_found:
        INSTALL['data_files'] = data_files_found


META_INFO = {
    'name': 'mysql-utilities',
    'description': 'MySQL Utilities ' + mysql.utilities.RELEASE_STRING,
    'maintainer': 'Oracle',
    'maintainer_email': '',
    'version': mysql.utilities.VERSION_STRING,
    'url': 'http://dev.mysql.com',
    'license': 'GNU GPLv2 (with FOSS License Exception)',
    'keywords': "mysql db",
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
# This adds any optional resource
add_optional_resources('mysql', exclude=["tests"])

if __name__=="__main__":
    for key, item in INSTALL.iteritems():
        print("--> {0}".format(key))
        print("      {0}".format(item))
        print

