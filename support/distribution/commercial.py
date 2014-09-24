#
# Copyright (c) 2013, 2014, Oracle and/or its affiliates. All rights reserved.
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
"""Module containing distutils commands for commercial packaging"""


import os
import time

from datetime import date
from distutils import log
from distutils.errors import DistutilsError


GPL_NOTICE_LINENR = 12

COPYRIGHT_FULL_HEADER = 'COPYRIGHT_FULL = "Copyright (c) " + COPYRIGHT +'
COPYRIGHT_FULL_COM = [
    "This is a release of dual licensed MySQL Utilities. "
    "For the avoidance of\n",
    "doubt, this particular copy of the software is released\n",
    "under a commercial license and the GNU General Public"
    " License does not apply.\n",
    "MySQL Utilities is brought to you by Oracle.\n",
    "\"\"\"\n",
    "\n",
    "LICENSE = \"Commercial\"\n"
]

COMMERCIAL_LICENSE_NOTICE = """
This is a release of MySQL Utilities, Oracle's dual-license
MySQL Utilities complete database modeling, administration and
development program for MySQL. For the avoidance of doubt, this
particular copy of the software is released under a commercial
license and the GNU General Public License does not apply.
MySQL Utilities is brought to you by Oracle.

Copyright (c) 2011, {0}, Oracle and/or its affiliates. All rights reserved.

For more information MySQL Utilities, visit
  http://www.mysql.com/products/enterprise/utilities.html
For more downloads visit
  http://www.mysql.com/downloads/

License information can be found in the LICENSE_Utilities.txt file.

This distribution may include materials developed by third
parties. For license and attribution notices for these
materials, please refer to the documentation that accompanies
this distribution (see the "Licenses for Third-Party Components"
appendix) or view the online documentation at
<http://dev.mysql.com/doc/index-utils-fabric.html>
""".format(time.strftime('%Y'))

COMMERCIAL_SETUP_PY = """#!/usr/bin/env python
# -*- coding: utf-8 -*-
# MySQL Utilities - Command-line tools for MySQL Administration.
# Copyright (c) 2012, %d, Oracle and/or its affiliates. All rights reserved.

import glob
import os

from distutils.command.build import build
from distutils.command.build_scripts import build_scripts as _build_scripts
from distutils.command.install import install as _install
from distutils.command.install_data import install_data as _install_data
from distutils.command.install_scripts import \
    install_scripts as _install_scripts
from distutils.core import Command
from distutils.core import setup
from distutils.dir_util import copy_tree
from distutils import log, util

COMMANDS = {{
    'cmdclass': {{
        }}
    }}

PROFILE_SCRIPT = '''
prepend_path () (
    IFS=':'
    for D in $PATH; do
        if test x$D != x$1; then
            OUTPATH="${{OUTPATH:+$OUTPATH:}}$D"
        fi
    done
    echo "$1:$OUTPATH"
)

PATH=`prepend_path `
'''

class Build(build):
    def run(self):
        copy_tree('mysql', os.path.join(self.build_lib, 'mysql'))
        #copy_tree('usr', os.path.join(self.build_lib, 'usr'))

def change_root (new_root, pathname):
    if os.name == 'posix':
        if not os.path.isabs(pathname):
            return os.path.join(new_root, pathname)
        else:
            return os.path.join(new_root, pathname[1:])

    elif os.name == 'nt':
        (drive, path) = os.path.splitdrive(pathname)
        if path[0] == '\\\\':
            path = path[1:]
        return os.path.join(new_root, path)

    elif os.name == 'os2':
        (drive, path) = os.path.splitdrive(pathname)
        if path[0] == os.sep:
            path = path[1:]
        return os.path.join(new_root, path)

    else:
        raise DistutilsPlatformError('unknown platform')

class install_man(Command):
    description = 'Install Unix manual pages'

    user_options = [
        ('prefix=', None, 'installation prefix (default /usr/share/man)'),
        ('root=', None,
         'install everything relative to this alternate root directory'),
        ('record=', None,
         'filename in which to record list of installed files'),
        ('srcdir=', None,
         'source directory prefix of the manuals')
    ]

    def initialize_options(self):
        self.root = None
        self.prefix = None
        self.record = None
        self.srcdir = None

    def finalize_options(self):
        self.set_undefined_options('install',
                                   ('root', 'root'),
                                   ('record', 'record')
                                   )
        if not self.prefix:
            self.prefix = '/usr/share/man'

        if self.root:
            self.prefix = change_root(self.root, self.prefix)

    def run(self):
        srcdir = os.path.join(self.srcdir, 'docs', 'man')
        manpages = os.listdir(srcdir)
        self._outfiles = []
        for man in manpages:
            src_man = os.path.join(srcdir, man)
            section = os.path.splitext(man)[1][1:]
            dest_dir = os.path.join(self.prefix, 'man' + section)
            self.mkpath(dest_dir) # Could be different section
            dest_man = os.path.join(dest_dir, man)
            self.copy_file(src_man, dest_man)
            self._outfiles.append(dest_man)

        # Disabled, done in the RPM spec
        #self._write_record()

    def _write_record(self):
        if self.record:
            outputs = self.get_outputs()
            if self.root:               # strip any package prefix
                root_len = len(self.root)
                for counter in xrange(len(outputs)):
                    outputs[counter] = outputs[counter][root_len:]

            log.info('writing list of installed files to')
            log.info(self.record)
            f = open(self.record, 'a')
            for line in outputs:
                f.write(line + '\\n')

    def get_outputs(self):
        return self._outfiles

class install_scripts(_install):
    description = "Install the Shell Profile (Linux/Unix)"

    user_options = _install.user_options + [
        ('root=', None,
         "install everything relative to this alternate root directory"),
        ]

    boolean_options = _install.boolean_options + ['skip-profile']
    profile_filename = 'mysql-utilities.sh'
    profile_d_dir = '/etc/profile.d/'

    def initialize_options(self):
        _install.initialize_options(self)
        self.skip_profile = False
        self.root = None
        self.install_dir = None

    def finalize_options(self):
        _install.finalize_options(self)
        self.set_undefined_options('install',
                                   ('install_dir', 'install_dir'),
                                   ('root', 'root'))

    def _create_shell_profile(self):
        \"\"\"Creates and installes the shell profile

        This method will create and try to install the shell
        profile file under /etc/profile.d/. It will skip this
        step when the --skip-profile install option has been
        given, or when the user installing MySQL Utilities
        has no permission.
        \"\"\"
        if self.skip_profile:
            log.info("Not adding shell profile " +
                     os.path.join(self.profile_d_dir, self.profile_filename)
                     +  "(skipped)")
            return

        if self.root:
            profile_dir = change_root(self.root, self.profile_d_dir)
        else:
            profile_dir = self.profile_d_dir

        try:
            dir_util.mkpath(profile_dir)
        except DistutilsFileError as err:
            log.info("Not installing mysql-utilities.sh: " + err)
            self.skip_profile = True
            return

        destfile = os.path.join(profile_dir, self.profile_filename)
        if not os.access(os.path.dirname(destfile), os.X_OK | os.W_OK):
            log.info("Not installing mysql-utilities.sh in "
                     "" + destfile + "(no permission)")
            self.skip_profile = True
            return

        if os.path.exists(os.path.dirname(destfile)):
            if os.path.isdir(destfile) and not os.path.islink(destfile):
                dir_util.remove_tree(destfile)
            elif os.path.exists(destfile):
                log.info('Removing '+ destfile)
                os.unlink(destfile)

        script = PROFILE_SCRIPT +self.install_dir
        log.info("Writing " + destfile)
        open(destfile, 'w+').write(script)

    def run(self):
        self._create_shell_profile()

    def get_outputs(self):
        outputs = _install.get_outputs(self)
        return outputs


class build_scripts(_build_scripts):
    \"\"\"Class for providing a customized version of build_scripts.

    When ``run`` is called, this command class will:
    1. Create a copy of all ``.py`` files in the **scripts** option
       that does not have the ``.py`` extension.
    2. Replace the list in the **scripts** attribute with a list
       consisting of the script files with the ``.py`` extension
       removed.
    3. Call run method in `distutils.command.build_scripts`.
    4. Restore the scripts list to the old value, for other commands
       to use.\"\"\"

    def run(self):
        if not self.scripts:
            return

        saved_scripts = self.scripts
        self.scripts = []
        for script in saved_scripts:
            script = util.convert_path(script)
            script_copy, script_ext = os.path.splitext(script)

            if script_ext != '.py':
                log.debug("Not removing extension from "
                          "" + script + "since it's not '.py'")
            else:
                log.debug('Copying {{0}} -> {{0}}'.format(script, script_copy))
                self.copy_file(script, script_copy)
                self.scripts.append(script_copy)
        # distutils is compatible with 2.1 so we cannot use super() to
        # call it.
        if not self.scripts:
            self.scripts = saved_scripts
        _build_scripts.run(self)
        self.outfiles = self.scripts
        self.scripts = saved_scripts
        

    def get_outputs(self):
        return self.outfiles


COMMANDS['cmdclass'].update({{
        'build': Build,
        'install_man': install_man,
        }})

if os.name != "nt":
    COMMANDS['cmdclass'].update({{
        'build_scripts': build_scripts,
        'install_man': install_man
        }})

data_files_found = []
for root, dirs, files in os.walk('etc'):
    datafiles = []
    for src in files:
        datafiles.append(os.path.join('etc', 'mysql', src))
    if datafiles:
        data_files_found.append(('etc/mysql', datafiles))

LONG_DESCRIPTION = \"\"\"
{long_description}
\"\"\"

setup(
    name='{name}',
    version='{version}',
    description='{description}',
    long_description=LONG_DESCRIPTION,
    author='{author}',
    author_email='{author_email}',
    license='{license}',
    keywords='{keywords}',
    url='{url}',
    download_url='{download_url}',
    package_dir={{ '': '' }},
    packages=['mysql', 'mysql.utilities', 'mysql.utilities.command',
        'mysql.utilities.common'],
    data_files=data_files_found,
    scripts=glob.glob('usr/bin/*'),
    classifiers={classifiers},
    cmdclass=COMMANDS['cmdclass']
)

""" % (date.today().year)


def remove_gpl(pyfile, dry_run=0):
    """Remove the GPL license form a Python source file

    Raise DistutilsError when a problem is found.
    """
    start = "# This program is free"
    end = "MA 02110-1301 USA"

    log.info("removing GPL license from %s" % pyfile)

    result = []
    removed = 0
    fp = open(pyfile, "r")
    line = fp.readline()

    done = False
    while line:
        if line.strip().startswith(start) and not done:
            result.append("# Following empty comments"
                          " are intentional.\n")
            removed += 1
            line = fp.readline()
            while line:
                result.append("#\n")
                removed += 1
                line = fp.readline()
                if line.strip().endswith(end):
                    done = True
                    line = fp.readline()
                    result.append("# End empty comments.\n")
                    removed += 1
                    break
        result.append(line)
        line = fp.readline()
    fp.close()
    result.append("\n")

    if removed != GPL_NOTICE_LINENR:
        msg = ("Problem removing GPL license. Removed %d lines from "
               "file %s" % (removed, pyfile))
        raise DistutilsError(msg)

    if not dry_run:
        fp = open(pyfile, "w")
        fp.writelines(result)
        fp.close()


def remove_full_gpl_cr(base_path, dry_run=0):
    init_path = os.path.join(base_path, "mysql","utilities","__init__.py")
    init_f = open(init_path, "r")
    line = init_f.readline()
    have_gpl = False
    done = False
    log.info("removing full GPL copyright from %s" % init_path)
    result = []
    while line:
        if not done and COPYRIGHT_FULL_HEADER in line:
            result.append(line) # add original header
            have_gpl = True
            #init_f.readline() # drop an original line
            for r_line in COPYRIGHT_FULL_COM:
                result.append(r_line)
                line = init_f.readline() # drop an original line
                print("rep {0} - > {1}".format(line, r_line))
            line = init_f.readline() # get the ending quotes
        else:
            result.append(line)
            line = init_f.readline()
    init_f.close()
    #result.append("\n")

    if not have_gpl:
        msg = ("Problem removing GPL Copyright.  from file %s" %  init_path)
        raise DistutilsError(msg)

    if not dry_run:
        fp = open(init_path, "w")
        fp.writelines(result)
        fp.close()

