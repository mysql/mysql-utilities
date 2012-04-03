#
# Copyright (c) 2010, 2012 Oracle and/or its affiliates. All rights reserved.
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
import sys
import shutil

def _add_basedir(search_paths, path_str):
    """Add a basedir and all known sub directories
    
    This method builds a list of possible paths for a basedir for locating
    special MySQL files like mysqld (mysqld.exe), etc.

    search_paths[inout] List of paths to append
    path_str[in]        The basedir path to append
    """
    search_paths.append(path_str)
    search_paths.append(os.path.join(path_str, "sql"))       # for source trees
    search_paths.append(os.path.join(path_str, "client"))    # for source trees
    search_paths.append(os.path.join(path_str, "share"))
    search_paths.append(os.path.join(path_str, "scripts"))
    search_paths.append(os.path.join(path_str, "bin"))
    search_paths.append(os.path.join(path_str, "libexec"))    
    search_paths.append(os.path.join(path_str, "mysql"))    


def get_tool_path(basedir, tool, fix_ext=True, required=True):
    """Search for a MySQL tool and return the full path

    basedir[in]         The initial basedir to search (from mysql server)
    tool[in]            The name of the tool to find
    fix_ext[in]         If True (default is True), add .exe if running on
                        Windows.
    required[in]        If True (default is True), and error will be
                        generated and the utility aborted if the tool is
                        not found.
                        
    Returns (string) full path to tool
    """

    from mysql.utilities.exception import UtilError

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
        raise UtilError("Cannot find location of %s." % tool)
        
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


def execute_script(run_cmd, file=None):
    """Execute a script.
    
    This method spawns a subprocess to execute a script. If a file is
    specified, it will direct output to that file else it will suppress
    all output from the script.
    
    run_cmd[in]        command/script to execute
    file[in]           file path name to file, os.stdout, etc.
                       Default is None (do not log/write output)
    
    Returns int - result from process execution
    """
    import subprocess

    if file is None:
        file = os.devnull
    f_out = open(file, 'w')
    proc = subprocess.Popen(run_cmd, shell=True, stdout=f_out, stderr=f_out)
    ret_val = proc.wait()
    f_out.close()
    return ret_val


def ping_host(host, timeout):
    """Execute 'ping' against host to see if it is alive.
    
    host[in]           hostname or IP to ping
    timeout[in]        timeout in seconds to wait
                       
    returns bool - True = host is reachable via ping
    """
    if sys.platform == "darwin":
        run_cmd = "ping -o -t %s %s" % (timeout, host)
    elif os.name == "posix":
        run_cmd = "ping -w %s %s" % (timeout, host)
    else: # must be windows
        run_cmd = "ping -n %s %s" % (timeout, host)

    ret_val = execute_script(run_cmd)

    return (ret_val == 0)


def get_mysqld_version(mysqld_path):
    """Return the version number for a mysqld executable.

    mysqld_path[in]    location of the mysqld executable
    
    Returns tuple - (major, minor, release), or None if error
    """
    import subprocess
    
    args = [
        " --version",
    ]
    out = open("version_check", 'w')
    proc = subprocess.Popen("%s --version" % mysqld_path,
                            stdout=out, stderr=out, shell=True)
    proc.wait()
    out.close()
    out = open("version_check", 'r')
    line = None
    for line in out.readlines():
        if "Ver" in line:
            break
    out.close()
    
    try:
        os.unlink('version_check')
    except:
        pass
    
    if line is None:
        return None
    version = line.split(' ', 5)[3]
    try:
        maj, min, dev = version.split(".")
        rel = dev.split("-")
        return (maj, min, rel[0])
    except:
        return None
        
    return None

