#
# Copyright (c) 2012, 2013 Oracle and/or its affiliates. All rights reserved.
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
"""DistUtils commands for creating RPM packages
"""

import os
import subprocess
import fnmatch

from distutils.core import Command
from distutils.dir_util import remove_tree, copy_tree
from distutils.file_util import copy_file
from distutils import log
from distutils.errors import DistutilsError

from info import META_INFO


class BuiltDistRPM(Command):
    """Create a built RPM distribution"""
    description = 'create a built RPM distribution'
    user_options = [
        ('bdist-base=', 'd',
         "base directory for creating built distributions"),
        ('rpm-base=', 'd',
         "base directory for creating RPMs (default <bdist-dir>/rpm)"),
        ('keep-temp', 'k',
         "keep the pseudo-installation tree around after "
         "creating the distribution archive"),
        ('dist-dir=', 'd',
         "directory to put final built distributions in"),
    ]

    rpm_spec = 'support/RPM/mysql_utilities_src.spec'

    def initialize_options(self):
        """Initialize the options"""
        self.bdist_base = None
        self.rpm_base = None
        self.keep_temp = 0
        self.dist_dir = None
    
    def finalize_options(self):
        """Finalize the options"""
        self.set_undefined_options('bdist', 
                                   ('bdist_base', 'bdist_base'),
                                   ('dist_dir', 'dist_dir'))

        if not self.rpm_base:
            self.rpm_base = os.path.join(self.bdist_base, 'rpm')

    def _populate_rpmbase(self):
        """Create and populate the RPM base directory"""
        self.mkpath(self.rpm_base)
        dirs = ['BUILD', 'RPMS', 'SOURCES', 'SPECS', 'SRPMS']
        self._rpm_dirs = {}
        for dirname in dirs:
            self._rpm_dirs[dirname] = os.path.join(self.rpm_base, dirname)
            self.mkpath(self._rpm_dirs[dirname])

    def eval(self, expr):
        """Returns macro expansion

        This method uses the --eval option of the rpm command line
        tool to return the macro expansion of expr.

        For example, to learn the value of %_prefix:
          self.eval('%_prefix')

        Returns a string.
        """
        cmd = ['rpm', '--eval', "'{0}'".format(expr)]
        prc = subprocess.Popen(' '.join(cmd),
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE,
                               shell=True)
        (stdoutdata, stderrdata) = prc.communicate()
        return stdoutdata.strip()

    def _create_rpm(self, stage='bb'):
        """Create the RPM files using the rpm command"""
        log.info("creating RPM using rpmbuild")

        cmd = ['rpmbuild',
            '-{0}'.format(stage),
            '--define', "_topdir " + os.path.abspath(self.rpm_base),
            '--define', "release_info " + META_INFO['description'],
            '--define', "version " + META_INFO['version'],
            self.rpm_spec
            ]
        if not self.verbose:
            cmd.append('--quiet')

        self.spawn(cmd)

        for loc in ('RPMS', 'SRPMS'):
            rpms = os.path.join(self.rpm_base, loc)
            for base, dirs, files in os.walk(rpms):
                for filename in files:
                    if filename.endswith('.rpm'):
                        filepath = os.path.join(base, filename)
                        copy_file(filepath, self.dist_dir)

    def run(self):
        """Run the distutils command"""
        # check whether we can execute rpmbuild
        self.mkpath(self.dist_dir)
        if not self.dry_run:
            try:
                devnull = open(os.devnull, 'w')
                subprocess.Popen(['rpmbuild', '--version'],
                    stdin=devnull, stdout=devnull, stderr=devnull)
            except OSError:
                raise DistutilsError("Cound not execute rpmbuild. Make sure "
                                     "it is installed and in your PATH")

        self._populate_rpmbase()
        
        sdist = self.get_finalized_command('sdist')
        sdist.dist_dir = self._rpm_dirs['SOURCES']
        sdist.formats = ['gztar']
        self.run_command('sdist')
        
        self._create_rpm()

        if not self.keep_temp:
            remove_tree(self.bdist_base, dry_run=self.dry_run)

class SourceRPM(BuiltDistRPM):
    """Create a source RPM distribution"""
    description = "create a source RPM distribution (src.rpm)"
    rpm_spec = 'support/RPM/mysql_utilities_src.spec'

    def run(self):
        self.mkpath(self.dist_dir)
        self._populate_rpmbase()

        sdist = self.get_finalized_command('sdist')
        sdist.dist_dir = self._rpm_dirs['SOURCES']
        sdist.formats = ['gztar']
        self.run_command('sdist')

        self._create_rpm(stage='bs')

        if not self.keep_temp:
            remove_tree(self.bdist_base, dry_run=self.dry_run)

class BuiltExeRPM(BuiltDistRPM):
    """Create a built RPM distribution with executables"""
    description = 'create a built RPM distribution with executables'
    rpm_spec = 'support/RPM/mysql_utilities.spec'

    def run(self):
        self.mkpath(self.dist_dir)
        self._populate_rpmbase()

        bdist = self.get_finalized_command('bdist')
        bdist.dist_dir = self._rpm_dirs['SOURCES']
        bdist.run()

        self._create_rpm()

