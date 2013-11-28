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

import os
import platform
import subprocess
import time

from distutils import log
from distutils.core import Command
from distutils.file_util import copy_file, move_file
from distutils.dir_util import create_tree, remove_tree, copy_tree
from distutils.errors import DistutilsError

from support.distribution.utils import unarchive_targz, get_dist_name

FORMAT = 'http://www.debian.org/doc/packaging-manuals/copyright-format/1.0/'
SOURCE = 'http://www.mysql.com/about/legal/licensing/foss-exception.html',
GPL_CR = {
    'FORMAT': FORMAT,
    'PRODUCT_NAME': 'mysql-utilities',
    'SOURCE': SOURCE,
    'CURRENT_YEAR': time.strftime('%Y'),
    'LICENSE_TYPE': 'GPL2',
    'README': '',
}

SOURCE = 'http://www.mysql.com/about/legal/licensing/oem/'
COM_CR = {
    'FORMAT': FORMAT,
    'PRODUCT_NAME': 'mysql-utilities-commercial',
    'SOURCE': SOURCE,
    'CURRENT_YEAR': time.strftime('%Y'),
    'LICENSE_TYPE': 'Commercial',
    'README': '',
}


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
             platform.linux_distribution()[1].split('.', 2)[0:2]))),
        ('tag=', 't',
         "Adds a tag name after the release version"),
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
        self.debian_support_dir = 'debian' # omit the /gpl for now.
        self.debug = True
        self.tag = ''

    def finalize_options(self):
        """Finalize the options"""
        self.set_undefined_options('bdist', 
                                   ('dist_dir', 'dist_dir'))
        if self.tag:
            self.tag = "-{0}".format(self.tag)

    def _populate_deb_base(self):
        """Create and populate the deb base directory"""

        def _get_date_time():
            """return time with format, Day, day# MM YYYY HH:MM:SS utc"""
            return time.strftime("%a, %d %b %Y %H:%M:%S %z", time.gmtime())

        #copy necessary files and debian metainfo files
        self.mkpath(self.deb_base)
        deb_dir = os.path.join(self.deb_base, "debian")
        copy_tree_src_dst = [
           (os.path.join("support", "debian","gpl"), deb_dir),
           ("docs", os.path.join(self.deb_base, "docs")),
           ("mysql", os.path.join(self.deb_base, "mysql")),
           ("scripts", os.path.join(self.deb_base, "scripts"))
        ]
        # Hack for Fabric, copy data dir if exist
        if os.path.exists('data'):
            copy_tree_src_dst.append(("data",
                                      os.path.join(self.deb_base, "data")))

        for src, dst in copy_tree_src_dst:
            copy_tree(src, dst)

        copy_file(os.path.join(os.getcwd(), "README.txt"),
                  os.path.join(self.deb_base, "README.txt"))
        copy_file(os.path.join(os.getcwd(), "LICENSE.txt"),
                  os.path.join(self.deb_base, "LICENSE.txt"))
        copy_file(os.path.join(os.getcwd(), "setup.py"),
                  os.path.join(self.deb_base, "setup.py"))
        copy_file(os.path.join(os.getcwd(), "info.py"),
                  os.path.join(self.deb_base, "info.py"))

        # debian/files
        log.info("creating debian/docs file")
        f_compat = open(os.path.join(deb_dir, 'docs'), mode='w')
        f_compat.write('README.txt\n')
        f_compat.write('LICENSE.txt\n')
        f_compat.flush()
        f_compat.close()

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

        # debian/copyright
        log.info("creating debian/copyright file")
        with open('README.txt') as f_readme:
            GPL_CR['README'] = ''.join(f_readme)
        cr_tmp_path = os.path.join("support", "debian", "copyright_template")
        with open(cr_tmp_path) as f_cr_template:
            lines = (line.replace('\n', '') for line in f_cr_template)
            content = '\n'.join(lines).format(**GPL_CR)
            with open(os.path.join(deb_dir, 'copyright'), 'w') as f_copyright:
                f_copyright.write('{0}\n'.format(content))

    def _create_deb(self, source_only=False, sign_pkg=False, binary=True):
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
        
        if binary:
            cmd.append("-b")
            cmd.append("-nc")
            cmd.append("-rfakeroot")
        
        os.chdir(self.deb_base)
        self.spawn(cmd)

        for base, dirs, files in os.walk(self.started_dir):
            for filename in files:
                if filename.endswith('.deb'):
                    newname = filename.replace(
                        '{0}_all'.format(self.version),
                        '{0}-1{1}{2}{3}_all'.format(self.version, self.tag, 
                                                  self.platform,
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


class BuildCommercialDistDebian(BuildDistDebian):
    description = 'create a commercial built distribution Debian package'

    def finalize_options(self):
        self.debian_support_dir = 'debian/commercial'
        BuildDistDebian.finalize_options(self)

    def _get_orig_name(self):
        """Returns name for tarball according to Debian's policies
        """
        return ("{name}-commercial_{version}.orig"
                "".format(name=self.distribution.get_name(),
                          version=self.distribution.get_version()))

    def _populate_deb_base(self,):
        """populate the Debian base directory for the commercial package"""

        def _get_date_time():
            """return time with format, Day, day# MM YYYY HH:MM:SS utc"""
            return time.strftime("%a, %d %b %Y %H:%M:%S %z", time.gmtime())

        log.info("Copying commercial Debian metainfo files")
        #copy necessary files and debian metainfo files
        #self.mkpath(self.deb_base)
        self.dist_name = get_dist_name(
            self.distribution,
            source_only_dist=False,#self.include_sources,
            commercial=True)
        deb_dir = os.path.join(self.dist_name, "debian")
        deb_lic_dir = self.debian_support_dir
        log.info("os.getcwd() {0}".format(os.getcwd()))
        copy_tree_src_dst = [(os.path.join("support", deb_lic_dir), deb_dir)]
        for src, dst in copy_tree_src_dst:
            copy_tree(src, dst, self.verbose, self.dry_run)

        # debian/files
        log.info("creating debian/docs file")
        f_compat = open(os.path.join(deb_dir, 'docs'), mode='w')
        f_compat.write('README_com.txt\n')
        f_compat.write('LICENSE_com.txt\n')
        f_compat.flush()
        f_compat.close()

        # debian/compat set to 8 for Debian 6 compatibility
        log.info("creating debian/compat file")
        f_compat = open(os.path.join(deb_dir, 'compat'), mode='w')
        f_compat.write('8\n')
        f_compat.flush()
        f_compat.close()

        # debian/changelog
        log.info("creating debian/changelog file")
        f_changelog = open( os.path.join(deb_dir,'changelog'), mode='w')
        f_changelog.write("{project_name}-commercial ({ver}) UNRELEASED; urgency=low\n\n"
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

        # debian/copyright
        log.info("creating debian/copyright file")
        log.info("current directory: {0}".format(os.getcwd()))
        readme_p = os.path.join('support', 'commercial_docs', 'README_com.txt')
        with open(readme_p) as f_readme:
            COM_CR['README'] = ''.join(f_readme)
        cr_tmp_path = os.path.join("support", "debian", "copyright_template")
        with open(cr_tmp_path) as f_cr_template:
            lines = (line.replace('\n', '') for line in f_cr_template)
            content = '\n'.join(lines).format(**COM_CR)
            with open(os.path.join(deb_dir, 'copyright'), 'w') as f_copyright:
                f_copyright.write('{0}\n'.format(content))

    def _prepare(self, tarball=None, base=None):
        dist_dirname = self.distribution.get_fullname()
        log.info("dist_dirname {0}".format(dist_dirname))
        log.info("os.getcwd() {0}".format(os.getcwd()))
        
        # Rename tarball to conform Debian's Policy
        if tarball:
            self.orig_tarball = os.path.join(
                os.path.dirname(tarball),
                self._get_orig_name()) + '.tar.gz'
            move_file(tarball, self.orig_tarball)

            untared_dir = unarchive_targz(self.orig_tarball)
            self.deb_base = os.path.join(
                tarball.replace('.tar.gz', ''), 'debian')
        elif base:
            self.deb_base = os.path.join(base, 'debian')
            log.info('self.deb_base = {0}'.format(self.deb_base))
            self.commercial_name = base

        self.mkpath(self.deb_base)
        self.mkpath(os.path.join(self.deb_base, 'source'))

        self._populate_deb_base()

    def run(self):
        """""Run the distutils command"""
        log.info("run() -commercial")
        # check whether we can execute debuild
        self.mkpath(self.dist_dir)
        cur_dir = os.getcwd()
        if not self.dry_run:
            try:
                devnull = open(os.devnull, 'w')
                subprocess.Popen([self.deb_build_cmd, '--version'],
                    stdin=devnull, stdout=devnull, stderr=devnull)
            except OSError:
                raise DistutilsError("Cound not execute debuild. Make sure "
                                     "it is installed and in your PATH"
                                     "or try apt-get install devscripts.")

        log.info("os.getcwd() {0}".format(os.getcwd()))
        sdist = self.get_finalized_command('bdist_com')
        sdist.dist_dir = os.getcwd()
        log.info("self.deb_base {0}".format(self.deb_base))
        sdist.formats = ['gztar']
        self.run_command('bdist_com')
        log.info("os.getcwd() {0}".format(os.getcwd()))

        # Copy necessary files to build debian package.
        log.info('dir(sdist) {0}'.format(dir(sdist)))
        log.info('sdist.dist_name {0}'.format(sdist.dist_name))
        if 'archive_files' in dir(sdist):
            self._prepare(sdist.archive_files[0])
        self._prepare(base=sdist.dist_name)


        self._create_deb(binary=True)

        if not self.keep_temp:
            os.chdir(cur_dir)
            temp_dir = get_dist_name(self.distribution,
                                     source_only_dist=False,
                                     commercial=True)
            remove_tree(temp_dir, dry_run=self.dry_run)

