#
# Copyright (c) 2015, Oracle and/or its affiliates. All rights reserved.
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
"""This Class extends DistUtils commands for create SunOS distribution
packages
"""

import os
import platform
import sys
import subprocess
import time

from distutils import log
from distutils.archive_util import make_tarball
from distutils.command.bdist import bdist
from distutils.errors import DistutilsExecError
from distutils.file_util import copy_file
from distutils.dir_util import copy_tree, remove_tree

PKGINFO = (
    'PKG="{pkg}"\n'
    'NAME="MySQL Utilities {ver} {lic}, Collection of utilities used for '
    'maintaining and administering MySQL servers"\n'
    'VERSION="{ver}"\n'
    'ARCH="all"\n'
    'CLASSES="none"\n'
    'CATEGORY="application"\n'
    'VENDOR="ORACLE Corporation"\n'
    'PSTAMP="{tstamp}"\n'
    'EMAIL="MySQL Release Engineering <mysql-build@oss.oracle.com>"\n'
    'BASEDIR="/"\n'
)


class BuildDistSunOS(bdist):
    """This class contains the command to built an SunOS distribution package
    """
    platf_n = '-solaris'
    platf_v = platform.uname()[2].split('.', 2)[1]
    description = 'create a Solaris distribution package'
    debug = False
    dist_dir = None
    dstroot = "dstroot"
    name = None
    keep_temp = None
    platform_version = None
    sun_pkg_name = None
    sun_path = None
    started_dir = None
    trans = False
    version = None
    pkg = 'mysql-utilities'
    user_options = [
        ('keep-temp', 'k',
         "keep the pseudo-installation tree around after "
         "creating the distribution archive"),
        ('trans', 't',
         "transform the package into data stream (default 'False')"),
        ('dist-dir=', 'd',
         "directory to put final built distributions in"),
        ('platform=', 'p',
         "name of the platform in resulting file "
         "(default '{0}')".format(platf_n)),
        ('platform-version=', 'v', "version of the platform in resulting file"
         " (default '{0}')".format(platf_v))
    ]

    boolean_options = ['keep-temp', 'trans']

    def initialize_options(self):
        """Initialize the options"""
        self.name = self.distribution.get_name()
        self.version = self.distribution.get_version()
        self.keep_temp = None
        self.dist_dir = None
        self.started_dir = os.getcwd()
        self.platform_version = self.platf_v
        self.debug = False
        self.sun_pkg_name = "{0}-{1}.pkg".format(self.name, self.version)
        self.dstroot = "dstroot"
        self.trans = False
        self.sun_path = ''

    def finalize_options(self):
        """Finalize the options"""
        self.set_undefined_options('bdist',
                                   ('dist_dir', 'dist_dir'))

    def _prepare_pgk_base(self, root='', gpl=True):
        """Create and populate the src base directory

        root[in]    The root path for the package contents
        gpl[in]     If false license and readme will correspond to the
                    commercial package instead of GPL files. True by default.
        """

        # copy and create necessary files
        self.sun_path = os.path.join(root, self.dstroot)

        cwd = os.path.join(os.getcwd())

        copy_file_src_dst = []

        # No special folder for GPL or commercial. Files inside the directory
        # will determine what it is.
        data_path = os.path.join(
            self.sun_path, 'usr', '{0}-{1}'.format(self.name, self.version)
        )
        self.mkpath(data_path)

        if gpl:
            lic = '(GPL)'
        else:
            lic = '(Commercial)'
        sun_pkg_info = os.path.join(cwd, self.sun_path, 'pkginfo')
        print("sun_pkg_info path: {0}".format(sun_pkg_info))
        with open(sun_pkg_info, 'w') as f_pkg_info:
            f_pkg_info.write(PKGINFO.format(ver=self.version, lic=lic,
                                            pkg=self.pkg,
                                            tstamp=time.ctime()))
            f_pkg_info.close()

        if gpl:
            copy_file_src_dst += [
                (os.path.join(cwd, "README.txt"),
                 os.path.join(data_path, "README_Utilities.txt")),
                (os.path.join(cwd, "CHANGES.txt"),
                 os.path.join(data_path, "CHANGES_Utilities.txt")),
                (os.path.join(cwd, "LICENSE.txt"),
                 os.path.join(data_path, "LICENSE.txt")),
                (os.path.join(cwd, "README_Fabric.txt"),
                 os.path.join(data_path, "README_Fabric.txt")),
                (os.path.join(cwd, "CHANGES_Fabric.txt"),
                 os.path.join(data_path, "CHANGES_Fabric.txt"))
            ]
        else:
            com_path = os.path.join('support', 'commercial_docs')
            copy_file_src_dst += [
                (os.path.join(cwd, com_path, "README_com.txt"),
                 os.path.join(data_path, "README_com.txt")),
                (os.path.join(cwd, com_path, "LICENSE_com.txt"),
                 os.path.join(data_path, "LICENSE.txt")),
                (os.path.join(cwd, "CHANGES.txt"),
                 os.path.join(data_path, "CHANGES_Utilities.txt")),
                (os.path.join(cwd, "README_Fabric_com.txt"),
                 os.path.join(data_path, "README_Fabric_com.txt")),
                (os.path.join(cwd, "CHANGES_Fabric.txt"),
                 os.path.join(data_path, "CHANGES_Fabric.txt"))
            ]

        for src, dst in copy_file_src_dst:
            if os.path.exists(src):
                copy_file(src, dst)
            else:
                log.info("File not found: {0}".format(src))

    def _create_pkg(self, gpl=True):
        """Create the Solaris package using the OS dependient commands.

        gpl[in]     If false license and readme will correspond to the
                    commercial package instead of GPL files. True by default.
        """
        if self.debug:
            log.info("Current directory: {0}".format(os.getcwd()))

        os.chdir(self.sun_path)
        log.info("Root directory for Prototype: {0}".format(os.getcwd()))

        # creating a Prototype file, this containts a table of contents of the
        # Package, that is suitable to be used for the package creation tool.
        log.info("Creating Prototype file on {0} to describe files to install"
                 "".format(self.dstroot))
        prototype_path = 'Prototype'
        proto_tmp = 'Prototype_temp'

        with open(proto_tmp, "w") as f_out:
            cmd = ['pkgproto', '.']
            pkgp_p = subprocess.Popen(cmd, shell=False, stdout=f_out,
                                      stderr=f_out)
            res = pkgp_p.wait()
            if res != 0:
                log.error("pkgproto command failed with: {0}".format(res))
                raise DistutilsExecError("pkgproto command failed with: {0}"
                                         "".format(res))
            f_out.flush()

        # log Prototype contents
        log.info("/n>> Prototype_temp contents >>/n")
        with open(proto_tmp, 'r') as f_in:
            log.info(f_in.readlines())
        log.info("/n<< Prototype_temp contents end <</n")

        # Fix Prototype file, incert pkginfo and remove Prototype
        log.info("Fixing folder permissions on Prototype contents")
        with open(prototype_path, 'w') as f_out:
            with open(proto_tmp, 'r') as f_in:
                # add pkginfo entry at begining of the Prototype file
                f_out.write("i pkginfo\n")
                f_out.flush()
                for line in f_in:
                    if line.startswith("f none Prototype"):
                        continue
                    elif line.startswith("f none pkginfo"):
                        continue
                    elif line.startswith("d"):
                        tokeep = line.split(' ')[:-3]
                        tokeep.extend(['?', '?', '?', '\n'])
                        f_out.write(' '.join(tokeep))
                    else:
                        f_out.write(line)
                f_out.flush()

        # log Prototype contents
        log.info("/n>> Prototype contents >>/n")
        with open(prototype_path, 'r') as f_in:
            log.info(f_in.readlines())
        log.info("/n<< Prototype contents end <</n")

        # Create Solaris package running the package creation command pkgmk
        log.info("Creating package with pkgmk")

        log.info("Root directory for pkgmk: {0}".format(os.getcwd()))
        self.spawn(['pkgmk', '-o', '-r', '.', '-d', '../', '-f',
                    prototype_path])
        os.chdir('../')
        if self.debug:
            log.info("current directory: {0}".format(os.getcwd()))

        # gzip the package folder
        log.info("creating tarball")

        make_tarball(self.sun_pkg_name, self.pkg, compress='gzip')

        if self.trans:
            log.info("Transforming package into data stream with pkgtrans")
            log.info("Current directory: {0}".format(os.getcwd()))
            self.spawn([
                'pkgtrans',
                '-s',
                os.getcwd(),
                os.path.join(os.getcwd(), self.sun_pkg_name),
                self.pkg
            ])

        for base, _, files in os.walk(os.getcwd()):
            for filename in files:
                if filename.endswith('.gz') or filename.endswith('.pkg'):
                    new_name = filename.replace(
                        '{0}'.format(self.version),
                        '{0}{1}{2}'.format(self.version, self.platf_n,
                                           self.platform_version)
                    )
                    file_path = os.path.join(base, filename)
                    file_dest = os.path.join(self.started_dir,
                                             self.dist_dir, new_name)
                    copy_file(file_path, file_dest)
            break

    def run(self):
        """Run the distutils command"""
        self.mkpath(self.dist_dir)

        self.debug = self.verbose
        build_path = 'build'
        root = os.path.join(build_path, 'sun')
        self.sun_path = os.path.join(root, self.dstroot)
        self.mkpath(self.sun_path)

        if self.debug:
            log.info("os.getcwd() {0}".format(os.getcwd()))
        install_cmd = self.reinitialize_command('install',
                                                reinit_subcommands=1)

        install_cmd.prefix = self.sun_path
        log.info("install_cmd.prefix {0}".format(install_cmd.prefix))
        if not self.debug:
            install_cmd.verbose = 0
        install_cmd.compile = False
        purelib_path = os.path.join('usr', 'lib', 'python{0}'
                                    ''.format(sys.version[0:3]),
                                    'site-packages')
        log.info("py_version {0}".format(purelib_path))
        install_cmd.install_purelib = purelib_path
        install_cmd.root = self.sun_path

        log.info("running install cmd")
        self.run_command('install')
        print("install_cmd: {0}".format(dir(install_cmd)))
        installed_files = install_cmd.get_outputs()
        print("installed_files: {0}".format(installed_files))
        log.info("install cmd finish")

        copy_tree(os.path.join(self.sun_path, self.sun_path, 'bin'),
                  os.path.join(self.sun_path, 'usr', 'bin'))

        remove_tree(os.path.join(self.sun_path, 'build'))

        man_prefix = '/usr/share/man'
        install_man_cmd = self.reinitialize_command('install_man',
                                                    reinit_subcommands=1)

        install_man_cmd.root = self.sun_path
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

        self._prepare_pgk_base(root=root)

        if self.debug:
            log.info("current directory: {0}".format(os.getcwd()))

        self._create_pkg()

        os.chdir(self.started_dir)
        if self.debug:
            log.info("current directory: {0}".format(os.getcwd()))
        if not self.keep_temp:
            remove_tree(build_path, dry_run=self.dry_run)


class BuildDistSunOScom(BuildDistSunOS):
    """This class contains the command to built a solaris distribution
       package
    """
    description = 'create a solaris distribution commercial package'
    user_options = [
        ('keep-temp', 'k',
         "keep the pseudo-installation tree around after "
         "creating the distribution archive"),
        ('trans', 't',
         "transform the package into data stream (default 'False')"),
        ('dist-dir=', 'd',
         "directory to put final built distributions in"),
        ('platform=', 'p',
         "name of the platform in resulting file "
         "(default '{0}')".format(BuildDistSunOS.platf_n)),
        ('platform-version=', 'v', "version of the platform in resulting file"
         " (default '{0}')".format(BuildDistSunOS.platf_v)),
    ]

    boolean_options = ['keep-temp', 'sign']

    def initialize_options(self):
        """Initialize the options"""
        self.name = self.distribution.get_name()
        self.version = self.distribution.get_version()
        self.keep_temp = None
        self.dist_dir = None
        self.started_dir = os.getcwd()
        self.platform_version = self.platf_v
        self.debug = False
        self.sun_pkg_name = "{0}-commercial-{1}.pkg".format(self.name,
                                                            self.version)
        self.dstroot = "dstroot"
        self.trans = False
        self.sun_path = ''

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
        root = os.path.join(build_path, 'sun')
        self.sun_path = os.path.join(root, self.dstroot)
        self.mkpath(self.sun_path)

        if self.debug:
            log.info("current directory: {0}".format(os.getcwd()))

        log.info("Current directory: {0}".format(os.getcwd()))
        bdist = self.get_finalized_command('bdist_com')
        bdist.dist_dir = root
        bdist.prefix = self.sun_path
        log.info("install_cmd.prefix {0}".format(bdist.prefix))
        if not self.debug:
            bdist.verbose = 0
        bdist.compile = False
        purelib_path = os.path.join(self.sun_path, 'usr', 'lib', 'python{0}'
                                    ''.format(sys.version[0:3]),
                                    'site-packages')
        log.info("py_version {0}".format(purelib_path))
        bdist.bdist_dir = purelib_path
        bdist.man_root = self.sun_path
        bdist.data_root = self.sun_path
        bdist.man_prefix = os.path.join('usr', 'share', 'man')
        bdist.bin_install_dir = os.path.join(self.sun_path, 'usr', 'bin')
        self.run_command('bdist_com')
        if self.debug:
            log.info("current directory: {0}".format(os.getcwd()))
        log.info("bdist_com cmd finish")

        if self.distribution.data_files:
            install_cmd = self.get_finalized_command('install_data')
            log.info("install_cmd.dist_dir {0}".format(root))
            install_cmd.install_dir = root
            log.info("install_cmd.root {0}".format(self.sun_path))
            install_cmd.root = self.sun_path
            log.info("install_cmd.prefix {0}".format(bdist.prefix))

            self.run_command('install_data')
            if self.debug:
                log.info("current directory: {0}".format(os.getcwd()))
            log.info("install_cmd cmd finish")

        # Copy necessary files to build solaris package.
        if self.debug:
            log.info('dir(bdist) {0}'.format(dir(bdist)))
            log.info('bdist.dist_name {0}'.format(bdist.dist_name))

        self._prepare_pgk_base(root=root, gpl=False)

        self._create_pkg(gpl=False)

        os.chdir(self.started_dir)
        if self.debug:
            log.info("current directory: {0}".format(os.getcwd()))
        if not self.keep_temp:
            remove_tree(build_path, dry_run=self.dry_run)
