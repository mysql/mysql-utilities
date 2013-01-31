# MySQL Connector/Python - MySQL driver written in Python.
# Copyright (c) 2012, Oracle and/or its affiliates. All rights reserved.

# MySQL Connector/Python is licensed under the terms of the GPLv2
# <http://www.gnu.org/licenses/old-licenses/gpl-2.0.html>, like most
# MySQL Connectors. There are special exceptions to the terms and
# conditions of the GPLv2 as it is applied to this software, see the
# FLOSS License Exception
# <http://www.mysql.com/about/legal/licensing/foss-exception.html>.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301 USA

"""Implements the Distutils command 'bdist_com_msi'

Implements the Distutils command 'bdist_com_msi' which creates a built
commercial distribution Windows Installer using Windows Installer XML 3.5.
The WiX file is available in the folder '/support/MSWindows/' of the
Connector/Python source.
"""

import sys
import os
import subprocess
import json
import re
from distutils import log
from distutils.errors import DistutilsError
from distutils.dir_util import remove_tree
from distutils.sysconfig import get_python_version
from distutils.command.bdist_dumb import bdist_dumb
from distutils.command.install_data import install_data
from distutils.command.bdist import bdist

from mysql.utilities import RELEASE_STRING, COPYRIGHT
from support import wix

WIX_INSTALL = r"C:\Program Files (x86)\Windows Installer XML v3.5"

class _MSIDist(bdist):
    """"Create a MSI distribution"""
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
        
        # version variables for Connector/Python and Python
        mycver = self.distribution.metadata.version
        match = re.match("(\d+)\.(\d+).(\d+).*", mycver)
        if not match:
            raise ValueError("Failed parsing version from %s" % mycver)
        (major, minor, patch) = match.groups()
        pyver = self.python_version
        pymajor = pyver[0]
        
        # check whether we have an upgrade code
        try:
            upgrade_code = upgrade_codes[mycver[0:3]][pyver]
        except KeyError:
            raise DistutilsError("No upgrade code found for version v%s, "
                                 "Python v%s" % mycver, pyver)
        log.info("upgrade code for v%s, Python v%s: %s" % (
                 mycver, pyver, upgrade_code))
        
        # wixobj's basename is the name of the installer
        wixobj = self._get_wixobj_name()
        msi = os.path.abspath(
            os.path.join(self.dist_dir, wixobj.replace('.wixobj', '.msi')))
        wixer = wix.WiX(self.wxs,
                        out=wixobj,
                        msi_out=msi,
                        base_path=self.build_base,
                        install=self.wix_install)
        
        # WiX preprocessor variables
        params = {
            'ProductName': 'MySQL Utilities',
            'ReleaseString': RELEASE_STRING,
            'Copyright': COPYRIGHT,
            'Version': '.'.join([major, minor, patch]),
            'FullVersion': mycver,
            'PythonVersion': pyver,
            'PythonMajor': pymajor,
            'Major_Version': major,
            'Minor_Version': minor,
            'Patch_Version': patch,
            'PythonInstallDir': 'Python%s' % pyver.replace('.', ''),
            'BaseDist': os.path.abspath(self.base_dist),
            'SitePkgDist': os.path.abspath(os.path.join(
                self.base_dist, 'Lib', 'site-packages')),
            'ScriptsDist': os.path.abspath(os.path.join(
                self.base_dist, 'Scripts')),
            'UpgradeCode': upgrade_code,
            'ManualPDF': os.path.abspath(os.path.join('docs', 'mysql-utilities.pdf')),
            'ManualHTML': os.path.abspath(os.path.join('docs', 'mysql-utilities.html')),
        }
        
        wixer.set_parameters(params)
        
        if not dry_run:
            try:
                wixer.compile()
                wixer.link()
            except DistutilsError:
                raise

        if not self.keep_temp and not dry_run:
            log.info('WiX: cleaning up')
            os.unlink(msi.replace('.msi', '.wixpdb'))
        
        return msi

    def _prepare_distribution(self):
        raise NotImplemented

    def run(self):
        """Run the distutils command"""
        # build command: just to get the build_base
        cmdbuild = self.get_finalized_command("build")
        self.build_base = cmdbuild.build_base
        
        # Some checks
        if os.name != 'nt':
            log.info("This command is only useful on Windows. "
                     "Forcing dry run.")
            self.dry_run = True
        wix.check_wix_install(wix_install_path=self.wix_install,
                              dry_run=self.dry_run)
        
        self._prepare_distribution()
        
        # create the Windows Installer
        msi_file = self._create_msi(dry_run=self.dry_run)
        log.info("created MSI as %s" % msi_file)
        
        if not self.keep_temp:
            remove_tree(self.build_base, dry_run=self.dry_run)

class SourceMSI(_MSIDist):
    """Create a Source MSI distribution"""
    description = 'create a source MSI distribution'
    user_options = [
        ('bdist-dir=', 'd',
         "temporary directory for creating the distribution"),
        ('keep-temp', 'k',
         "keep the pseudo-installation tree around after " +
         "creating the distribution archive"),
        ('dist-dir=', 'd',
         "directory to put final source distributions in"),
        ('wix-install', None,
         "location of the Windows Installer XML installation"
         "(default: %s)" % WIX_INSTALL),
    ]

    boolean_options = [
        'keep-temp', 'include-sources'
    ]
    
    def initialize_options (self):
        """Initialize the options"""
        self.bdist_dir = None
        self.keep_temp = 0
        self.dist_dir = None
        self.wix_install = WIX_INSTALL
        self.python_version = get_python_version()
    
    def finalize_options(self):
        """Finalize the options"""
        if self.bdist_dir is None:
            bdist_base = self.get_finalized_command('bdist').bdist_base
            self.bdist_dir = os.path.join(bdist_base, 'dist')

        self.set_undefined_options('bdist',
                                   ('dist_dir', 'dist_dir'))

        self.wxs = 'support/MSWindows/mysql_utilities.xml'
        self.fix_txtfiles = ['README.txt', 'LICENSE.txt']

    def _get_wixobj_name(self, myc_version=None, python_version=None):
        """Get the name for the wixobj-file

        Return string
        """
        mycver = myc_version or self.distribution.metadata.version
        pyver = python_version or self.python_version
        return "mysql-utilities-%s-py%s.wixobj" % (
            mycver, pyver)

    def _prepare_distribution(self):
        """Prepare the distribution"""
        cmd = self.reinitialize_command('install', reinit_subcommands=0)
        cmd.compile = False
        cmd.dry_run = self.dry_run
        cmd.keep_temp = True
        cmd.prefix = os.path.join('dist', self.distribution.get_fullname())
        self.run_command('install')
        self.base_dist = cmd.prefix

        # copy text files and correct newlines
        for txtfile in self.fix_txtfiles:
            log.info("creating and fixing text file %s", txtfile)
            builttxt = os.path.join(self.base_dist, txtfile)
            open(builttxt, 'w').write(open(txtfile).read())


