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
"""This Class extends DistUtils commands for create mac osx distribution
packages
"""

import os
import platform
import sys

from distutils import log
from distutils.command.bdist import bdist
from distutils.file_util import copy_file
from distutils.dir_util import copy_tree, remove_tree


class BuildDistOSX(bdist):
    """This class contains the command to built an osx distribution package
    """
    platf_n = '-osx'
    platf_v = '.'.join(platform.mac_ver()[0].split('.', 2)[0:2])
    description = 'create a mac osx distribution package'
    user_options = [
        ('keep-temp', 'k',
         "keep the pseudo-installation tree around after "
         "creating the distribution archive"),
        ('create-dmg', 'c',
         "create a dmg image from the resulting package file "
         "(default 'False')"),
        ('sign', 's',
         "signs the package file (default 'False')"),
        ('identity=', 'i',
         "identity or name of the certificate to use to sign the package file"
         "(default 'MySQL-Utilities')"),
        ('dist-dir=', 'd',
         "directory to put final built distributions in"),
        ('platform=', 'p',
         "name of the platform in resulting file "
         "(default '{0}')".format(platf_n)),
        ('platform-version=', 'v',
         "version of the platform in resulting file "
         "(default '{0}')".format(platf_v))
    ]

    boolean_options = ['keep-temp', 'create-dmg', 'sign']

    def initialize_options(self):
        """Initialize the options"""
        self.name = self.distribution.get_name()
        self.version = self.distribution.get_version()
        self.keep_temp = None
        self.create_dmg = False
        self.dist_dir = None
        self.started_dir = os.getcwd()
        self.platform = self.platf_n
        self.platform_version = self.platf_v
        self.debug = False
        self.osx_pkg_name = "{0}-{1}.pkg".format(self.name, self.version)
        self.dstroot = "dstroot"
        self.sign = False
        self.identity = "MySQL-Utilities"

    def finalize_options(self):
        """Finalize the options"""
        self.set_undefined_options('bdist',
                                   ('dist_dir', 'dist_dir'))

    def _prepare_pgk_base(self, template_name, root='', gpl=True):
        """Create and populate the src base directory

        osx_pkg_name[in] the name of the resulting package
        root[in]         the root path for the package contents
        gpl[in]          if false license and readme will correspond to the
                         commercial package instead of GPL files. default=True
        """

        # copy and create necessary files
        osx_dist_name = template_name.format(self.name, self.version)
        osx_pkg_name = "{0}.pkg".format(osx_dist_name)
        osx_pkg_contents = os.path.join(root, osx_pkg_name, 'Contents')
        osx_pkg_resrc = os.path.join(osx_pkg_contents, 'Resources')
        self.mkpath(osx_pkg_resrc)

        copy_file_src_dst = [
            (os.path.join("support", "osx", "PkgInfo"),
             os.path.join(osx_pkg_contents, "PkgInfo")),
            (os.path.join("support", "osx", "background.jpg"),
             os.path.join(osx_pkg_resrc, "background.jpg")),
            (os.path.join("support", "osx", "Welcome.rtf"),
             os.path.join(osx_pkg_resrc, "Welcome.rtf"))
        ]

        if gpl:
            copy_file_src_dst += [
                (os.path.join(os.getcwd(), "README.txt"),
                 os.path.join(osx_pkg_resrc, "ReadMe.txt")),
                (os.path.join(os.getcwd(), "LICENSE.txt"),
                 os.path.join(osx_pkg_resrc, "License.txt"))
            ]
        else:
            com_path = os.path.join('support', 'commercial_docs')
            copy_file_src_dst += [
                (os.path.join(os.getcwd(), com_path, "README_com.txt"),
                 os.path.join(osx_pkg_resrc, "ReadMe.txt")),
                (os.path.join(os.getcwd(), com_path, "LICENSE_com.txt"),
                 os.path.join(osx_pkg_resrc, "License.txt"))
            ]

        property_files = [
            (os.path.join("support", "osx", "Info.plist"),
             os.path.join(osx_pkg_contents, "Info.plist")),
            (os.path.join("support", "osx", "Description.plist"),
             os.path.join(osx_pkg_resrc, "Description.plist"))
        ]

        for pro_file, dest_file in property_files:
            with open(pro_file) as temp_f:
                lines = (ln.replace('\n', '') for ln in temp_f)
                major_version = self.version.split('.')[0]
                minor_version = self.version.split('.')[1]
                content = '\n'.join(lines).format(VERSION=self.version,
                                                  MAJORVERSION=major_version,
                                                  MINORVERSION=minor_version)
                with open(dest_file, 'w') as dest_f:
                    dest_f.write('{0}\n'.format(content))

        for src, dst in copy_file_src_dst:
            copy_file(src, dst)

    def _create_pkg(self, template_name, dmg=False, sign=False, root='',
                    identity=''):
        """Create the mac osx pkg and a dmg image if it is required

        dmg[in]      if true a dmg file will created for the package folder
        root[in]     the root path for the package contents
        """

        osx_dist_name = template_name.format(self.name, self.version)
        osx_pkg_name = "{0}.pkg".format(osx_dist_name)
        osx_pkg_contents = os.path.join(osx_pkg_name, 'Contents')

        if self.debug:
            log.info("current directory: {0}".format(os.getcwd()))
        os.chdir(root)
        log.info("Root directory: {0}".format(os.getcwd()))

        # create a bom(8) file to tell the installer which files need to be
        # installed
        log.info("creating Archive.bom file, that describe files to install")
        archive_bom_path = os.path.join(osx_pkg_contents, 'Archive.bom')
        self.spawn(['mkbom', self.dstroot, archive_bom_path])

        # Create an archive of the files to install
        log.info("creating Archive.pax with files to be installed")
        os.chdir(self.dstroot)

        pax_file = '../{NAME}/Contents/Archive.pax'.format(NAME=osx_pkg_name)
        self.spawn(['pax', '-w', '-x', 'cpio', '.', '-f', pax_file])
        os.chdir('../')
        if self.debug:
            log.info("current directory: {0}".format(os.getcwd()))

        # Sign the package
        # In Order to be possible the certificates needs to be installed
        if sign:
            log.info("Signing the package")
            osx_pkg_name_signed = '{0}_s.pkg'.format(osx_dist_name)
            self.spawn(['productsign', '--sign', identity,
                        osx_pkg_name,
                        osx_pkg_name_signed])
            self.spawn(['spctl', '-a', '-v', '--type', 'install',
                        osx_pkg_name_signed])
            osx_pkg_name = osx_pkg_name_signed

        # Create a .dmg image
        if dmg:
            log.info("Creating dmg file")
            self.spawn(['hdiutil', 'create', '-volname', osx_dist_name,
                        '-srcfolder', osx_pkg_name, '-ov', '-format',
                        'UDZO', '{0}.dmg'.format(osx_dist_name)])

        log.info("Current directory: {0}".format(os.getcwd()))

        for base, dirs, files in os.walk(os.getcwd()):
            for filename in files:
                if filename.endswith('.dmg'):
                    new_name = filename.replace(
                        '{0}'.format(self.version),
                        '{0}{1}{2}'.format(self.version, self.platform,
                                                 self.platform_version)
                    )
                    file_path = os.path.join(base, filename)
                    file_dest = os.path.join(self.started_dir,
                                             self.dist_dir, new_name)
                    copy_file(file_path, file_dest)
                    break
            for dir_name in dirs:
                print(dir_name)
                if dir_name.endswith('.pkg'):
                    new_name = dir_name.replace(
                        '{0}'.format(self.version),
                        '{0}{1}{2}'.format(self.version, self.platform,
                                                 self.platform_version)
                    )
                    dir_dest = os.path.join(self.started_dir,
                                            self.dist_dir, new_name)
                    copy_tree(dir_name, dir_dest)
                    break
            break

    def run(self):
        """Run the distutils command"""
        self.mkpath(self.dist_dir)

        self.debug = self.verbose

        build_path = 'build'
        root = os.path.join(build_path, 'osx')
        osx_path = os.path.join(root, self.dstroot)
        self.mkpath(osx_path)

        if self.debug:
            log.info("os.getcwd() {0}".format(os.getcwd()))
        install_cmd = self.reinitialize_command('install',
                                                reinit_subcommands=1)

        install_cmd.prefix = osx_path
        log.info("install_cmd.prefix {0}".format(install_cmd.prefix))
        if not self.debug:
            install_cmd.verbose = 0
        install_cmd.compile = False
        purelib_path = os.path.join('Library', 'Python',
                                    sys.version[0:3], 'site-packages')
        log.info("py_version {0}".format(purelib_path))
        install_cmd.install_purelib = purelib_path
        install_cmd.root = osx_path
        #install_cmd.install_dir = build_path
        log.info("running install cmd")
        self.run_command('install')
        log.info("install cmd finish")

        copy_tree(os.path.join(osx_path, osx_path, 'bin'),
                  os.path.join(osx_path, 'bin'))

        remove_tree(os.path.join(osx_path, 'build'))

        man_prefix = '/usr/local/share/man'
        install_man_cmd = self.reinitialize_command('install_man',
                                                    reinit_subcommands=1)

        install_man_cmd.root = osx_path
        install_man_cmd.prefix = man_prefix
        log.info("install_cmd.root {0}".format(install_man_cmd.root))
        log.info("install_cmd.prefix {0}".format(install_man_cmd.prefix))
        if not self.debug:
            install_man_cmd.verbose = 0
        log.info("running install_man cmd")
        self.run_command('install_man')
        log.info("install_man cmd finish")

        if self.debug:
            log.info("current directory: {0}".format(os.getcwd()))

        template_name = "{0}-{1}"
        self._prepare_pgk_base(template_name, root=root)

        if self.debug:
            log.info("current directory: {0}".format(os.getcwd()))

        self._create_pkg(template_name, dmg=self.create_dmg, root=root,
                         sign=self.sign, identity=self.identity)

        os.chdir(self.started_dir)
        if self.debug:
            log.info("current directory: {0}".format(os.getcwd()))
        if not self.keep_temp:
            remove_tree(build_path, dry_run=self.dry_run)


class BuildDistOSXcom(BuildDistOSX):
    """This class contains the command to built an osx distribution package
    """
    description = 'create a mac osx distribution package'
    user_options = [
        ('keep-temp', 'k',
         "keep the pseudo-installation tree around after "
         "creating the distribution archive"),
        ('create-dmg', 'c',
         "create a dmg image from the resulting package file "
         "(default 'False')"),
        ('sign', 's',
         "signs the package file (default 'False')"),
        ('identity=', 'i',
         "identity or name of the certificate to use to sign the package file"
         "(default 'MySQL-Utilities')"),
        ('dist-dir=', 'd',
         "directory to put final built distributions in"),
        ('platform=', 'p',
         "name of the platform in resulting file "
         "(default '{0}')".format(BuildDistOSX.platf_n)),
        ('platform-version=', 'v',
         "version of the platform in resulting file "
         "(default '{0}')".format(BuildDistOSX.platf_v))
    ]

    boolean_options = ['keep-temp', 'create-dmg', 'sign']

    def initialize_options(self):
        """Initialize the options"""
        self.name = self.distribution.get_name()
        self.version = self.distribution.get_version()
        self.keep_temp = None
        self.create_dmg = False
        self.dist_dir = None
        self.started_dir = os.getcwd()
        self.platform = self.platf_n
        self.platform_version = self.platf_v
        self.debug = False
        self.osx_pkg_name = "{0}-{1}.pkg".format(self.name, self.version)
        self.dstroot = "dstroot"
        self.sign = False
        self.identity = "MySQL-Utilities"

    def finalize_options(self):
        """Finalize the options"""
        self.set_undefined_options('bdist',
                                   ('dist_dir', 'dist_dir'))

    def run(self):
        """Run the distutils command"""
        log.info("self.name = {0}".format(self.name))
        self.mkpath(self.dist_dir)

        self.debug = self.verbose

        build_path = 'build'
        root = os.path.join(build_path, 'osx')
        osx_path = os.path.join(root, self.dstroot)
        self.mkpath(osx_path)

        if self.debug:
            log.info("current directory: {0}".format(os.getcwd()))

        log.info("Current directory: {0}".format(os.getcwd()))
        bdist = self.get_finalized_command('bdist_com')
        bdist.dist_dir = root
        bdist.prefix = osx_path
        log.info("install_cmd.prefix {0}".format(bdist.prefix))
        if not self.debug:
            bdist.verbose = 0
        bdist.compile = False
        purelib_path = os.path.join(osx_path, 'Library', 'Python',
                                    sys.version[0:3], 'site-packages')
        log.info("py_version {0}".format(purelib_path))
        bdist.bdist_dir = purelib_path
        bdist.man_root = osx_path
        bdist.man_prefix = os.path.join('usr', 'local', 'share', 'man')
        bdist.bin_install_dir = os.path.join(osx_path, 'bin')
        self.run_command('bdist_com')
        if self.debug:
            log.info("current directory: {0}".format(os.getcwd()))
        log.info("bdist_com cmd finish")

        install_cmd = self.get_finalized_command('install_data')
        log.info("install_cmd.dist_dir {0}".format(root))
        install_cmd.install_dir = root
        log.info("install_cmd.root {0}".format(osx_path))
        install_cmd.root = osx_path
        log.info("install_cmd.prefix {0}".format(bdist.prefix))

        self.run_command('install_data')
        if self.debug:
            log.info("current directory: {0}".format(os.getcwd()))
        log.info("install_cmd cmd finish")

        # Copy necessary files to build osx package.
        if self.debug:
            log.info('dir(bdist) {0}'.format(dir(bdist)))
            log.info('bdist.dist_name {0}'.format(bdist.dist_name))

        template_name = "{0}-commercial-{1}"
        self._prepare_pgk_base(template_name, root=root, gpl=False)

        if self.debug:
            log.info("current directory: {0}".format(os.getcwd()))

        self._create_pkg(template_name, dmg=self.create_dmg, root=root,
                         sign=self.sign, identity=self.identity)

        os.chdir(self.started_dir)
        if self.debug:
            log.info("current directory: {0}".format(os.getcwd()))
        if not self.keep_temp:
            remove_tree(build_path, dry_run=self.dry_run)

