#!/usr/bin/env python
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
"""Setup script for MySQL Utilities"""
from __future__ import absolute_import

import ConfigParser
import fnmatch
import os
import re
from glob import glob
import sys

import distutils.core
from distutils.core import setup
from distutils.command.build_scripts import build_scripts as _build_scripts
from distutils.command.install import install as _install
from distutils.command.install_data import install_data as _install_data
from distutils.command.install_scripts import \
    install_scripts as _install_scripts
from distutils.util import change_root
from distutils.file_util import DistutilsFileError, write_file
from distutils import log, dir_util

from info import META_INFO, INSTALL

# Check required Python version
if sys.version_info[0:2] not in [(2, 6), (2, 7)]:
    log.error("MySQL Utilities requires Python v2.6 or v2.7")
    sys.exit(1)

COMMANDS = {
    'cmdclass': {
        },
    }

# Custom bdist_rpm DistUtils command
try:
    from support.dist_rpm import BuiltDistRPM, BuiltCommercialRPM, SourceRPM
except ImportError:
    pass # Use default when not available
else:
    COMMANDS['cmdclass'].update({
        'bdist_rpm': BuiltDistRPM,
        'sdist_rpm': SourceRPM,
        'bdist_com_rpm': BuiltCommercialRPM
    })

try:
    from support.distribution.commands import build, bdist, sdist
except ImportError:
    pass # Use default when not available
else:
    COMMANDS['cmdclass'].update({
        'sdist': sdist.GenericSourceGPL,
        'build': build.Build,
        'sdist_com': sdist.SourceCommercial,
        'bdist_com': bdist.BuiltCommercial
    })

try:
    from support.dist_deb import BuildDistDebian, BuildCommercialDistDebian
                                  
except ImportError:
    pass
else:
    COMMANDS['cmdclass'].update({
        'bdist_deb': BuildDistDebian,
        'bdist_com_deb': BuildCommercialDistDebian
    })
ARGS = {
}

PROFILE_SCRIPT = '''
prepend_path () (
    IFS=':'
    for D in $PATH; do
        if test x$D != x$1; then
            OUTPATH="${OUTPATH:+$OUTPATH:}$D"
        fi
    done
    echo "$1:$OUTPATH"
)

PATH=`prepend_path %s`
'''


class install(_install):
    """Install MySQL Utilities"""
    user_options = _install.user_options + [
        ("skip-profile", None, "Skip installing a profile script"),
        ]

    boolean_options = _install.boolean_options + ['skip-profile']

    def initialize_options(self):
        """Initialize options"""
        _install.initialize_options(self)
        self.skip_profile = False

    def finalize_options(self):
        """Finalize options"""
        _install.finalize_options(self)

    def run(self):
        _install.run(self)


class install_man(distutils.core.Command):
    description = "Install Unix manual pages"

    user_options = [
        ('prefix=', None, 'installation prefix (default /usr/share/man)'),
        ('root=', None,
         "install everything relative to this alternate root directory"),
        ('record=', None,
         "filename in which to record list of installed files"),
    ]

    def initialize_options(self):
        """Initialize options"""
        self.root = None
        self.prefix = None
        self.record = None

    def finalize_options(self):
        """Finalize options"""
        self.set_undefined_options('install',
                                   ('root', 'root'),
                                   ('record', 'record')
                                   )
        if not self.prefix:
            self.prefix = '/usr/share/man'

        if self.root:
            self.prefix = change_root(self.root, self.prefix)

    def run(self):
        """Run the command"""
        srcdir = os.path.join('docs', 'man')
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
        """Write list of installed files"""
        if self.record:
            outputs = self.get_outputs()
            if self.root:               # strip any package prefix
                root_len = len(self.root)
                for counter in xrange(len(outputs)):
                    outputs[counter] = outputs[counter][root_len:]

            log.info("writing list of installed files to '{0}'".format(
                self.record))
            f = open(self.record, "a")
            for line in outputs:
                f.write(line + "\n")

    def get_outputs(self):
        return self._outfiles


class install_scripts(_install):
    """Install MySQL Utilities scripts"""
    description = "Install the Shell Profile (Linux/Unix)"

    user_options = _install.user_options + [
        ('root=', None,
         "install everything relative to this alternate root directory"),
        ]

    boolean_options = _install.boolean_options + ['skip-profile']
    profile_filename = 'mysql-utilities.sh'
    profile_d_dir = '/etc/profile.d/'

    def initialize_options(self):
        """initialize options"""
        _install.initialize_options(self)
        self.skip_profile = False
        self.root = None
        self.install_dir = None

    def finalize_options(self):
        """Finalize options"""
        _install.finalize_options(self)
        self.set_undefined_options('install',
                                   ('install_dir', 'install_dir'),
                                   ('root', 'root'))

    def _create_shell_profile(self):
        """Creates and installes the shell profile

        This method will create and try to install the shell
        profile file under /etc/profile.d/. It will skip this
        step when the --skip-profile install option has been
        given, or when the user installing MySQL Utilities
        has no permission.
        """
        if self.skip_profile:
            log.info("Not adding shell profile %s (skipped)" % (
                     os.path.join(self.profile_d_dir, self.profile_filename)))
            return

        if self.root:
            profile_dir = change_root(self.root, self.profile_d_dir)
        else:
            profile_dir = self.profile_d_dir

        try:
            dir_util.mkpath(profile_dir)
        except DistutilsFileError as err:
            log.info("Not installing mysql-utilities.sh: {0}".format(err))
            self.skip_profile = True
            return

        destfile = os.path.join(profile_dir, self.profile_filename)
        if not os.access(os.path.dirname(destfile), os.X_OK | os.W_OK):
            log.info("Not installing mysql-utilities.sh in "
                     "{folder} (no permission)".format(folder=destfile))
            self.skip_profile = True
            return

        if os.path.exists(os.path.dirname(destfile)):
            if os.path.isdir(destfile) and not os.path.islink(destfile):
                dir_util.remove_tree(destfile)
            elif os.path.exists(destfile):
                log.info("Removing {filename}".format(filename=destfile))
                os.unlink(destfile)

        script = PROFILE_SCRIPT % (self.install_dir,)
        log.info("Writing {filename}".format(filename=destfile))
        open(destfile, "w+").write(script)

    def run(self):
        """Run the command"""
        self._create_shell_profile()

    def get_outputs(self):
        """Get installed files"""
        outputs = _install.get_outputs(self)
        return outputs


class build_scripts(_build_scripts):
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
            script = distutils.util.convert_path(script)
            script_copy, script_ext = os.path.splitext(script)

            if script_ext != '.py':
                log.debug("Not removing extension from {script} "
                          "since it's not '.py'".format(script=script))
            else:
                log.debug("Copying {orig} -> {dest}".format(
                    orig=script, dest=script_copy))
                self.copy_file(script, script_copy)
                self.scripts.append(script_copy)
        # distutils is compatible with 2.1 so we cannot use super() to
        # call it.
        _build_scripts.run(self)
        self.outfiles = self.scripts
        self.scripts = saved_scripts
        

    def get_outputs(self):
        """Get installed files"""
        return self.outfiles


COMMANDS['cmdclass'].update({
        'install': install,
        })


# We need to edit the configuration file before installing it
class install_data(_install_data):
    def run(self):
        from itertools import groupby

        # Set up paths to write to config file
        install_dir = self.install_dir
        install_logdir = '/var/log'
        if os.name == 'posix' and install_dir in ('/', '/usr'):
            install_sysconfdir = '/etc'
        else:
            install_sysconfdir = os.path.join(install_dir, 'etc')

        # Go over all entries in data_files and process it if needed
        new_data_files = []
        for df in self.data_files:
            # Figure out what the entry contain and collect a list of files.
            if isinstance(df, str):
                # This was just a file name, so it will be installed
                # in the install_dir location. This is a copy of the
                # behaviour inside distutils intall_data.
                directory = install_dir
                filenames = [df]
            else:
                directory = df[0]
                filenames = df[1]

            # Process all the files for the entry and build a list of
            # tuples (directory, file)
            data_files = []
            for filename in filenames:
                # It was a config file template, add install
                # directories to the config file.
                if fnmatch.fnmatch(filename, 'data/*.cfg.in'):
                    config = ConfigParser.RawConfigParser({
                            'prefix': '', # install_dir,
                            'logdir': install_logdir,
                            'sysconfdir': install_sysconfdir,
                            })
                    config.readfp(open(filename))
                    #filename = os.path.split(os.path.splitext(filename)[0])[1]
                    filename = os.path.splitext(filename)[0]
                    config.write(open(filename, "w"))
                    # change directory 'fabric'to mysql 
                    directory = os.path.join(install_sysconfdir, 'mysql')
                data_files.append((directory, filename))
            new_data_files.extend(data_files)

        # Re-construct the data_files entry from what was provided by
        # merging all tuples with same directory and provide a list of
        # files as second item, e.g.:
        #   [('foo', 1), ('bar', 2), ('foo', 3), ('foo', 4), ('bar', 5)]
        #   --> [('bar', [2, 5]), ('foo', [1, 3, 4])]
        data_files.sort()
        data_files = [
            (d, [ f[1] for f in fs ]) for d, fs in 
                groupby(new_data_files, key=lambda x: x[0])
            ]
        self.data_files = data_files
        _install_data.run(self)


COMMANDS['cmdclass'].update({
        'install_data': install_data,
        })


if os.name != "nt":
    COMMANDS['cmdclass'].update({
        'build_scripts': build_scripts,
        'install_man': install_man,
        })

ARGS.update(META_INFO)
ARGS.update(INSTALL)
ARGS.update(COMMANDS)
setup(**ARGS)

