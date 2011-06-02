#
# Copyright (c) 2010, Oracle and/or its affiliates. All rights reserved.
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

"""
This module contains methods for working with mysql server tools.
"""

import os
import shutil

def _add_basedir(search_paths, path_str):
    """ Add a basedir and all known sub directories
    
    This method builds a list of possible paths for a basedir for locating
    special MySQL files like mysqld (mysqld.exe), etc.

    search_paths[inout] List of paths to append
    path_str[in]        The basedir path to append
    """
    search_paths.append(path_str)
    search_paths.append(os.path.join(path_str, "share"))
    search_paths.append(os.path.join(path_str, "scripts"))
    search_paths.append(os.path.join(path_str, "bin"))
    search_paths.append(os.path.join(path_str, "libexec"))    
    search_paths.append(os.path.join(path_str, "mysql"))    

def get_tool_path(basedir, tool, fix_ext=True, required=True):
    """ Search for a MySQL tool and return the full path

    basedir[in]         The initial basedir to search (from mysql server)
    tool[in]            The name of the tool to find
    fix_ext[in]         If True (default is True), add .exe if running on
                        Windows.
    required[in]        If True (default is True), and error will be
                        generated and the utility aborted if the tool is
                        not found.
                        
    Returns (string) full path to tool
    """

    from mysql.utilities.exception import MySQLUtilError

    search_paths = []
    _add_basedir(search_paths, basedir)
    _add_basedir(search_paths, "/usr/local/mysql/")
    _add_basedir(search_paths, "/usr/sbin/")
    _add_basedir(search_paths, "/usr/share/")
    if os.name == "nt" and fix_ext:
        tool = tool + ".exe"
    # Search for the tool
    for path in search_paths:
        norm_path = os.path.normpath(path)
        if os.path.isdir(norm_path):
            toolpath = os.path.join(norm_path, tool)
            if os.path.isfile(toolpath):
                return toolpath
    if required:
        raise MySQLUtilError("Cannot find location of %s." % tool)
        
    return None

def delete_directory(dir):
    """Remove a directory (folder) and its contents.
    
    dir[in]           target directory
    """
    import time
    
    if os.path.exists(dir):
        # It can take up to 10 seconds for Windows to 'release' a directory
        # once a process has terminated. We wait...
        if os.name == "nt":
            stop = 10
            i = 1
            while i < stop and os.path.exists(dir):
                shutil.rmtree(dir, True)
                time.sleep(1)
                i += 1
        else:
            shutil.rmtree(dir, True)

