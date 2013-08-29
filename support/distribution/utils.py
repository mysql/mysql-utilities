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

"""Miscellaneous utility functions"""

import os
import gzip
import tarfile

from distutils.sysconfig import get_python_version

def get_dist_name(distribution, source_only_dist=False, platname=None,
                  python_version=None, commercial=False, hide_pyver=False):
    """Get the distribution name
    
    Get the distribution name usually used for creating the egg file. The
    Python version is excluded from the name when source_only_dist is True.
    The platname will be added when it is given at the end.
    
    Returns a string.
    """
    name = distribution.metadata.name
    if commercial:
        name += '-commercial'
    name += '-' + distribution.metadata.version
    if not hide_pyver and (not source_only_dist or python_version):
        pyver = python_version or get_python_version()
        name += '-py' + pyver
    if platname:
        name += '-' + platname
    return name

def get_magic_tag():
    try:
        # For Python Version >= 3.2
        from imp import get_tag
        return get_tag()
    except ImportError:
        return ''

def unarchive_targz(tarball):
    """Unarchive a tarball

    Unarchives the given tarball. If the tarball has the extension
    '.gz', it will be first uncompressed.

    Returns the path to the folder of the first unarchived member.

    Returns str.
    """
    orig_wd = os.getcwd()

    (dstdir, tarball_name) = os.path.split(tarball)
    if dstdir:
        os.chdir(dstdir)

    if '.gz' in tarball_name:
        new_file = tarball_name.replace('.gz', '')
        gz = gzip.GzipFile(tarball_name)
        tar = open(new_file, 'wb')
        tar.write(gz.read())
        tar.close()
        tarball_name = new_file

    tar = tarfile.TarFile(tarball_name)
    tar.extractall()

    os.unlink(tarball_name)
    os.chdir(orig_wd)

    return os.path.abspath(os.path.join(dstdir, tar.getmembers()[0].name))
