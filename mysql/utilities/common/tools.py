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
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307 USA
#

"""
This module contains methods for working with mysql server tools.
"""

import os

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

def get_tool_path(basedir, tool, required=True):
    """ Search for a MySQL tool and return the full path

    basedir[in]         The initial basedir to search (from mysql server)
    tool[in]            The name of the tool to find
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
                        
