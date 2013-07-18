#
# Copyright (c) 2013 Oracle and/or its affiliates. All rights reserved.
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
"""This Class extends DistUtils commands for create Debian distribution
packages
"""

import fnmatch
import os
import platform
import subprocess
import time

from distutils.core import Command
from distutils.dir_util import remove_tree, copy_tree
from distutils.file_util import copy_file
from distutils import log
from distutils.errors import DistutilsError


class BuildDistDebian(Command):
    """This class contains the command to built a Debian distribution package
    """
    description = 'create a Debian distribution'
    user_options = [
        ('keep-temp', 'k',
         "keep the pseudo-installation tree around after "
         "creating the distribution archive"),
        ('dist-dir=', 'd',
         "directory to put final built distributions in"),
        ('platform=', 'p',
         "name of the platform in resulting file "
         "(default '{0}')".format(platform.linux_distribution()[0].lower())),
        ('platform-version=', 'v',
         "version of the platform in resulting file "
         "(default '{0}')".format('.'.join(
             platform.linux_distribution()[1].split('.', 2)[0:2])))
    ]

    def initialize_options(self):
        """Initialize the options"""
        self.name = self.distribution.get_name()
        self.version = self.distribution.get_version()
        self.maintainer = self.distribution.get_maintainer()
        self.maintainer_email = self.distribution.get_maintainer_email()
        if self.maintainer_email == 'UNKNOWN':
            # default email to avoid build failure on parsing changelog
            self.maintainer_email = 'mysql-build@oss.oracle.com'
        deb_base = "{0}-{1}".format(self.name, self.version)
        self.deb_base = os.path.join(os.getcwd(), deb_base)
        self.keep_temp = None
        self.dist_dir = None
        self.deb_build_cmd = 'debuild'
        self.started_dir = os.getcwd()
        self.platform = platform.linux_distribution()[0].lower()
        self.platform_version = '.'.join(
            platform.linux_distribution()[1].split('.', 2)[0:2])

    def finalize_options(self):
        """Finalize the options"""
        self.set_undefined_options('bdist', 
                                   ('dist_dir', 'dist_dir'))
        pass

    def _populate_deb_base(self):
        """Create and populate the deb base directory"""
        
        def _get_date_time():
            """return time with format, Day, day# MM YYYY HH:MM:SS utc"""
            return time.strftime("%a, %d %b %Y %H:%M:%S %z", time.gmtime())
        
        #copy necessary files and debian metainfo files
        self.mkpath(self.deb_base)
        deb_dir = os.path.join(self.deb_base, "debian")
        copy_tree_src_dst = [(os.path.join("support", "debian"), deb_dir),
           ("docs", os.path.join(self.deb_base, "docs")),
           ("mysql", os.path.join(self.deb_base, "mysql")),
           ("scripts", os.path.join(self.deb_base, "scripts"))
           ]
        for src, dst in copy_tree_src_dst:
            copy_tree(src, dst)

        copy_file(os.path.join(os.getcwd(), "README.txt"),
                  os.path.join(self.deb_base, "README"))
        copy_file(os.path.join(os.getcwd(), "LICENSE.txt"),
                  os.path.join(self.deb_base, "LICENSE.txt"))
        copy_file(os.path.join(os.getcwd(), "setup.py"),
                  os.path.join(self.deb_base, "setup.py"))
        copy_file(os.path.join(os.getcwd(), "info.py"),
                  os.path.join(self.deb_base, "info.py"))
        
        # debian/compat set to 8 for Debian 6 compatibility
        log.info("creating debian/compat file")
        f_compat = open(os.path.join(deb_dir, 'compat'), mode='w')
        f_compat.write('8\n')
        f_compat.flush()
        f_compat.close()

        # debian/changelog
        log.info("creating debian/changelog file")
        f_changelog = open( os.path.join(deb_dir,'changelog'), mode='w')
        f_changelog.write("{project_name} ({ver}) UNRELEASED; urgency=low\n\n"
                          "  * Debian package automatically created.\n\n"
                          " -- {maintainer} <{maintainer_email}>  {date_R}\n"
                          "".format(project_name=self.name, ver=self.version,
                                    maintainer=self.maintainer,
                                    maintainer_email=self.maintainer_email,
                                    date_R=_get_date_time()))
        f_changelog.flush()
        f_changelog.close()

        # package.manpages
        log.info("creating debian/package.manpages file")
        f_manpages = open(os.path.join(deb_dir, 'manpages'), mode='w')
        for base, dirs, files in os.walk(os.path.join(self.deb_base,
                                                      "docs", "man")):
                for filename in files:
                    if not self.verbose:
                        log.info("  Adding MAN page: {0}".format(filename))
                    filepath = os.path.join("docs", "man", filename)
                    f_manpages.write('{0}\n'.format(filepath))
        f_manpages.flush()
        f_manpages.close()

    def _create_deb(self, source_only=False, sign_pkg=False):
        """Create the deb files using the deb_build_cmd command"""
        log.info("creating deb package using {0}".format(self.deb_build_cmd))

        cmd = [self.deb_build_cmd]

        # The -us and -uc are use to avoid try to sign the deb package and dsc
        if not sign_pkg:
            cmd.append("-us")
            cmd.append("-uc")

        # create only the debian src tar (a tar with the debian directory)
        if source_only:
            cmd.append("-S")

        os.chdir(self.deb_base)
        self.spawn(cmd)

        for base, dirs, files in os.walk(self.started_dir):
            for filename in files:
                if filename.endswith('.deb'):
                    newname = filename.replace(
                        '{0}_all'.format(self.version),
                        '{0}{1}{2}_all'.format(self.version, self.platform,
                                               self.platform_version)
                        )
                    filepath = os.path.join(base, filename)
                    filedest = os.path.join(self.started_dir,
                                            self.dist_dir, newname)
                    copy_file(filepath, filedest)

    def run(self):
        """Run the distutils command"""
        # check whether we can execute debuild
        self.mkpath(self.dist_dir)
        if not self.dry_run:
            try:
                devnull = open(os.devnull, 'w')
                subprocess.Popen([self.deb_build_cmd, '--version'],
                    stdin=devnull, stdout=devnull, stderr=devnull)
            except OSError:
                raise DistutilsError("Cound not execute debuild. Make sure "
                                     "it is installed and in your PATH"
                                     "or try apt-get install devscripts.")

        # Copy necessary files to build debian package.
        self._populate_deb_base()

        self._create_deb()

        if not self.keep_temp:
            remove_tree(self.deb_base, dry_run=self.dry_run)
