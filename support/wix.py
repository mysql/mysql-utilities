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

import os
import subprocess
from distutils import log
from distutils.errors import DistutilsError

WIX_INSTALL_PATH = r"C:\Program Files (x86)\Windows Installer XML v3.5"

def check_wix_install(wix_install_path=None, required_version='3.5',
                      dry_run=0):
    """Check the WiX installation

    Check whether the WiX tools are available in given wix_install_path
    and also check the required_version.

    Raises DistutilsError when the tools are not available or
    when the version is not correct.
    """
    wix_install_path = wix_install_path or WIX_INSTALL_PATH
    candle = os.path.join(wix_install_path, 'bin/candle.exe')
    if (not (os.path.isfile(candle) and os.access(candle, os.X_OK))
        and not dry_run):
        raise DistutilsError("Could not find candle.exe under %s" %
                             wix_install_path)

    cmd = [
        os.path.join(wix_install_path, 'bin/candle.exe'),
        '-?'
    ]

    if dry_run:
        return
    prc = subprocess.Popen(' '.join(cmd),
                           stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE)
    data = prc.communicate()[0]
    try:
        verline = data.split("\n")[0].strip()
    except TypeError:
        # Must be Python v3
        verline = data.decode('utf8').split("\n")[0].strip()

    wix_version = verline.split(' ')[-1][:3]
    if wix_version != required_version:
        raise DistutilsError("Required WiX v%s, we found v%s" %
                             (required_version, wix_version))

class WiX(object):
    """Class for creating a Windows Installer using WiX"""
    def __init__(self, wxs, out=None, msi_out=None,
                 base_path=None, install=None):
        """Constructor
        
        The Windows Installer will be created using the WiX document
        wxs. The msi_out argument can be used to set the name of the
        resulting Windows Installer (.msi file).
        The argument install can be used to point to the WiX installation.
        The default location is:
            '%s'
        Temporary and other files needed to create the Windows Installer
        will be by default created in the current working dir. You can
        change this using the base_path argument.
        """ % (WIX_INSTALL_PATH)
        if out:
            self.set_out(out)
        self._msi_out = msi_out
        self._wxs = wxs
        self._install = install
        self._base_path = base_path
        if self._install:
            self._bin = os.path.join(self._install, 'bin')
        else:
            self._bin = None
        self._parameters = None

    def set_parameters(self, parameters):
        """Set parameters to use in the WXS document(s)"""
        self._parameters = parameters

    def set_out(self, out):
        """Set the name of the resulting Windows Installer"""
        self._out = out

    def _run_tool(self, cmdname, cmdargs):
        """Runs a WiX tool
        
        Run the given command with arguments.
        
        Raises DistutilsError on errors.
        """
        cmd = [
            os.path.join(self._bin, cmdname)
        ]
        cmd += cmdargs

        log.debug("Running: %s", ' '.join(cmd))
        prc = subprocess.Popen(' '.join(cmd),
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
        (stdoutdata, stderrdata) = prc.communicate()
        
        for line in stdoutdata.splitlines():
            try:
                if 'warning' in line:
                    log.info(line)
                elif 'error' in line:
                    raise DistutilsError('WiX Error: ' + line)
            except TypeError:
                if b'warning' in line:
                    log.info(line)
                elif b'error' in line:
                    raise DistutilsError('WiX Error: ' + line.decode('utf8'))
            except DistutilsError:
                raise
                
        if prc.returncode:
            raise DistutilsError("%s exited with return code %d" % (
                                 cmdname, prc.returncode))

    def compile(self, wxs=None, out=None, parameters=None):
        wxs = wxs or self._wxs
        log.info("WiX: Compiling %s" % wxs)
        out = out or self._out
        objfile = os.path.join(self._base_path, out)
        cmdargs = [
            r'-nologo',
            r'-out %s' % (objfile),
            r'-v',
            wxs,
        ]
        if parameters:
            params = dict(
                self._parameters.items() + parameters.items())
        else:
            params = self._parameters

        for parameter, value in params.items():
            cmdargs.append('-d%s="%s"' % (parameter, value))

        self._run_tool('candle.exe', cmdargs)

    def link(self, wixobj=None, base_path=None):
        wixobj = wixobj or self._out
        base_path = base_path or self._base_path
        msi_out = self._msi_out or wixobj.replace('.wixobj','.msi')
        log.info("WiX: Linking %s" % wixobj)

        # light.exe -b option does not seem to work, we change to buld dir
        cwd = os.getcwd()
        os.chdir(base_path)
        cmdargs = [
            r'-nologo',
            r'-sw1076',
            r'-out %s' % msi_out,
            wixobj,
        ]

        self._run_tool('light.exe', cmdargs)
        os.chdir(cwd)

