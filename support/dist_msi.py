#
# Copyright (c) 2012, 2013, Oracle and/or its affiliates. All rights reserved.
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

"""Implements custom DistUtils commands for the MS Windows platform

This module implements custom DistUtils commands for the Microsoft
Windows platform. WiX 3.5 and py2exe are required.
"""

import fnmatch
import json
import os
import re
import sys
from distutils import log
from distutils.errors import DistutilsError
from distutils.dir_util import remove_tree
from distutils.sysconfig import get_python_version
from distutils.command.bdist_dumb import bdist_dumb
from distutils.command.install_data import install_data
from distutils.command.bdist import bdist
from distutils.util import get_platform
from distutils.file_util import copy_file

from mysql.utilities import RELEASE_STRING, COPYRIGHT
from support import wix
from support.distribution.msi_descriptor_parser import add_features

WIX_INSTALL = r"C:\Program Files (x86)\Windows Installer XML v3.5"


class _MSIDist(bdist):
    """Create a Windows Installer with Windows Executables"""
    user_options = [
        ('bdist-base=', 'b',
         "temporary directory for creating built distributions"),
        ('plat-name=', 'p',
         "platform name to embed in generated filenames "
         "(default: %s)" % get_platform()),
        ('dist-dir=', 'd',
         "directory to put final built distributions in "
         "[default: dist]"),
        ('keep-temp', 'k',
         "keep the pseudo-installation tree around after " +
         "creating the distribution"),
        ('tag=', 't',
         "Adds a tag name after the release version"),
        ('sub-version=', 's',
         "adds a subversion after the current version"),
        ]

    boolean_options = ['keep-temp']

    def initialize_options(self):
        """Initialize options"""
        self.bdist_base = None
        self.plat_name = None
        self.dist_dir = None
        self.keep_temp = False
        self.dist_type = None
        self.dist_target = None
        self.tag = ''
        self.product_name = 'MySQL Utilities'
        self.sub_version = ''

    def finalize_options(self):
        """Finalize opitons"""
        if self.plat_name is None:
            self.plat_name = self.get_finalized_command('build').plat_name

        if self.bdist_base is None:
            build_base = self.get_finalized_command('build').build_base
            self.bdist_base = os.path.join(build_base,
                                           'bdist.' + self.plat_name)

        if self.dist_dir is None:
            self.dist_dir = "dist"

        if self.tag:
            self.tag = "-{0}".format(self.tag)

    def _get_wixobj_name(self, myc_version=None, python_version=None):
        """Get the name for the wixobj-file

        Returns a string
        """
        raise NotImplemented

    def _create_msi(self, dry_run=0):
        """Create the Windows Installer using WiX
        
        Creates the Windows Installer using WiX and returns the name of
        the created MSI file.
        
        Raises DistutilsError on errors.
        
        Returns a string
        """
        # load the upgrade codes
        fp = open('support/MSWindows/upgrade_codes.json')
        upgrade_codes = json.load(fp)
        fp.close()
        
        # Version of the application being packaged
        appver = self.distribution.metadata.version
        match = re.match(r"(\d+)\.(\d+).(\d+).*", appver)
        if not match:
            raise ValueError("Failed parsing version from %s" % appver)
        (major, minor, patch) = match.groups()

        # Python version
        pyver = self.python_version
        pymajor, pyminor = pyver.split('.')[0:2]
        
        # Check whether we have an upgrade code
        try:
            upgrade_code = upgrade_codes[appver[0:3]][pyver]
        except KeyError:
            raise DistutilsError(
                "No upgrade code found for version v{appver}, "
                "Python v{pyver}".format(appver=appver, pyver=pyver))
        log.info("upgrade code for v{appver},"
                 " Python v{pyver}: {upgrade}".format(
                    appver=appver, pyver=pyver, upgrade=upgrade_code))
        
        # wixobj's basename is the name of the installer
        wixobj = self._get_wixobj_name()
        msi = os.path.abspath(
            os.path.join(self.dist_dir, wixobj.replace('.wixobj', '.msi')))
        wixer = wix.WiX(self.wxs,
                        out=wixobj,
                        msi_out=msi,
                        base_path=self.dist_dir,
                        install=self.wix_install)
        
        # WiX preprocessor variables
        if self.dist_type == 'com':
            liscense_file = 'License_com.rtf'
        else:
            liscense_file = 'License.rtf'
        params = {
            'ProductName': self.product_name,
            'ReleaseString': RELEASE_STRING,
            'Copyright': COPYRIGHT,
            'Version': '.'.join([major, minor, patch]),
            'FullVersion': appver,
            'PythonVersion': pyver,
            'PythonMajor': pymajor,
            'PythonMinor': pyminor,
            'Major_Version': major,
            'Minor_Version': minor,
            'Patch_Version': patch,
            'PythonInstallDir': 'Python%s' % pyver.replace('.', ''),
            'BuildDir': os.path.abspath(self.bdist_base),
            #'BDist': os.path.abspath(self.dist_target),
            'PyExt': 'pyc' if not self.include_sources else 'py',
            'BitmapDir': os.path.join(os.getcwd(), 'support', 'MSWindows'),
            'UpgradeCode': upgrade_code,
            'LicenseRtf': os.path.abspath(
                os.path.join('support', 'MSWindows', liscense_file)),
        }
        
        wixer.set_parameters(params)
        
        if not dry_run:
            try:
                wixer.compile(ui=True)
                wixer.link(ui=True)
            except DistutilsError:
                raise

        if not self.keep_temp:
            log.info('Cleaning up')
            os.unlink(msi.replace('.msi', '.wixobj'))
            os.unlink(msi.replace('.msi', '.wixpdb'))
            remove_tree(self.bdist_base)
        
        return msi

    def _prepare_distribution(self):
        """Prepare the distribution

        This method should be overloaded.
        """
        raise NotImplementedError

    def run(self):
        """Run the distutils command"""
        if os.name != 'nt':
            log.info("This command is only useful on Windows.")
            sys.exit(1)

        wix.check_wix_install(wix_install_path=self.wix_install,
                              dry_run=self.dry_run)
        
        self._prepare_distribution()
        
        # create the Windows Installer
        msi_file = self._create_msi(dry_run=self.dry_run)
        log.info("created MSI as %s" % msi_file)


class MSIBuiltDist(_MSIDist):
    """Create a Built MSI distribution with executables"""
    description = 'create a Built MSI distribution with executables'
    user_options = _MSIDist.user_options + [
        ('wix-install', None,
         "location of the Windows Installer XML installation\n"
         "[default: %s]" % WIX_INSTALL),
        ]

    python_version = get_python_version()
    wxs = 'support/MSWindows/mysql_utilities.xml'
    fix_txtfiles = ['README.txt', 'LICENSE.txt']
    
    def initialize_options(self):
        """Initialize the options"""
        _MSIDist.initialize_options(self)
        self.wix_install = None
        self.include_sources = False
    
    def finalize_options(self):
        """Finalize the options"""
        _MSIDist.finalize_options(self)
        if not self.wix_install:
            self.wix_install = WIX_INSTALL
        pck_fabric = False
        add_doczip = False
        for pck_name in self.distribution.packages:
            if 'fabric' in pck_name:
                pck_fabric = True
                log.info('-Adding Fabric')
        if self.distribution.data_files:
            for dest, data_files in self.distribution.data_files:
                for data_file in data_files:
                    log.info('data_file: {0}'.format(data_file))
                    doczip_pattern = 'data/mysql-fabric-doctrine-?.?.?.zip'
                    if fnmatch.fnmatch(data_file, doczip_pattern):
                        head, tail = os.path.split(data_file)
                        add_doczip = tail or head
                        log.info('-Adding doctrine extensions')
        if pck_fabric or add_doczip:
            base_xml_path = "support/MSWindows/mysql_utilities.xml"
            result_xml_path = 'support/MSWindows/mysql_utilities_fab-doc.xml'
            add_features(base_xml_path, result_xml_path,
                         add_fabric=pck_fabric,
                         add_doczip=add_doczip,
                         log=log)
            for root, _dirs, files in os.walk('support/MSWindows/'):
                log.info('Checking for new msi descriptor at: {0}'.format(root))
                for afile in files:
                    log.info('file: {0}'.format(afile))
                if 'mysql_utilities_fab-doc.xml' in files:
                    log.info('new msi descriptor found')
                else:
                    log.info('new msi descriptor not found')
            self.wxs = result_xml_path

    def _get_wixobj_name(self, app_version=None, python_version=None):
        """Get the name for the wixobj-file

        Return string
        """
        appver = app_version or self.distribution.metadata.version
        pyver = python_version or self.python_version
        if self.plat_name:
            platform = '-' + self.plat_name
        return ("mysql-utilities-{app_version}{sub_version}{tag}"
                "{platform}.wixobj").format(app_version=appver, 
                                            sub_version=self.sub_version,
                                            python_version=pyver,
                                            tag=self.tag,
                                            platform=platform)

    def _prepare_distribution(self):
        """Prepare the distribution"""
        log.info('===== installing data =====')
        install_data = self.reinitialize_command('install_data',
                                                     reinit_subcommands=1)
        install_data.install_dir = self.bdist_base
        log.info("installing to %s" % self.bdist_base)
        self.run_command('install_data')
        log.info('install_data finish')
        
        buildexe = self.get_finalized_command('build_exe')
        buildexe.build_exe = self.bdist_base 
        buildexe.run()

        # copy text files and correct newlines
        for txtfile in self.fix_txtfiles:
            log.info("creating and fixing text file %s", txtfile)
            builttxt = os.path.join(self.bdist_base, txtfile)
            open(builttxt, 'w').write(open(txtfile).read())


class BuiltCommercialMSI(_MSIDist):
    """Create a Built Commercial MSI distribution"""
    description = 'create a commercial built MSI distribution'
    user_options = [
        ('bdist-base=', 'd',
         "temporary directory for creating the distribution"),
        ('keep-temp', 'k',
         "keep the pseudo-installation tree around after " +
         "creating the distribution archive"),
        ('dist-dir=', 'd',
         "directory to put final built distributions in"),
        ('include-sources', None,
         "exclude sources built distribution (default: True)"),
        ('wix-install', None,
         "location of the Windows Installer XML installation"
         "(default: %s)" % wix.WIX_INSTALL_PATH),
        ('tag=', 't',
         "Adds a tag name after the release version"),
        ('sub-version=', 's',
         "adds a subversion after the current version"),
    ]

    boolean_options = [
        'keep-temp', 'include-sources'
    ]
    
    def initialize_options (self):
        """Initialize the options"""
        self.bdist_base = None
        self.tag = ''
        self.keep_temp = 0
        self.dist_dir = None
        self.plat_name = None
        self.include_sources = False
        self.wix_install = wix.WIX_INSTALL_PATH
        self.python_version = get_python_version()
        self.dist_type =''#'com'
        self.sub_version = ''
    
    def finalize_options(self):
        """Finalize the options"""
        self.set_undefined_options('bdist',
                                   ('dist_dir', 'dist_dir'),
                                   ('plat_name', 'plat_name'))

        self.wxs = 'support/MSWindows/mysql_utilities_com.xml'
        self.fix_txtfiles = ['README_com.txt', 'LICENSE_com.txt']
        if self.tag:
            self.tag = "-{0}".format(self.tag)

    def _get_wixobj_name(self, app_version=None, python_version=None):
        """Get the name for the wixobj-file

        Return string
        """
        appver = app_version or self.distribution.metadata.version
        pyver = python_version or self.python_version

        if self.plat_name:
            platform = '-' + self.plat_name

        return ("mysql-utilities-commercial-{app_version}{sub_version}{tag}"
                "{platform}.wixobj").format(app_version=appver,
                                            sub_version=self.sub_version,
                                            python_version=pyver,
                                            tag=self.tag,
                                            platform=platform)

    def _prepare_distribution(self):
        """Prepare the distribution"""
        cmdbdist = self.get_finalized_command("bdist_com")
        cmdbdist.dry_run = self.dry_run
        cmdbdist.keep_temp = True
        self.run_command("bdist_com")

        log.info("building exes at {0}".format(cmdbdist.bdist_dir))
        buildexe = self.get_finalized_command('build_exe')
        buildexe.build_exe = cmdbdist.bdist_dir 
        buildexe.run()
        docfiles = [
            (os.path.join(cmdbdist.dist_target, 'LICENSE_com.txt'),
             os.path.join(cmdbdist.bdist_dir, 'LICENSE_com.txt')),
            (os.path.join(cmdbdist.dist_target, 'README_com.txt'),
             os.path.join(cmdbdist.bdist_dir, 'README_com.txt'))
        ]
        for src, dst in docfiles:
            self.copy_file(src, dst)
        self.bdist_base = cmdbdist.bdist_dir
        # This sets name for various items as install directory.
        self.product_name = 'MySQL Utilities commercial'


