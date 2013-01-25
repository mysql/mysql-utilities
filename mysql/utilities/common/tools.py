#
# Copyright (c) 2010, 2013, Oracle and/or its affiliates. All rights reserved.
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
import time
import subprocess

from mysql.utilities.common.format import print_list
from mysql.utilities.exception import UtilError


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


def get_tool_path(basedir, tool, fix_ext=True, required=True,
                  defaults_paths=[], search_PATH=False):
    """Search for a MySQL tool and return the full path

    basedir[in]         The initial basedir to search (from mysql server)
    tool[in]            The name of the tool to find
    fix_ext[in]         If True (default is True), add .exe if running on
                        Windows.
    required[in]        If True (default is True), and error will be
                        generated and the utility aborted if the tool is
                        not found.
    defaults_paths[in]  Default list of paths to search for the tool.
                        By default an empty list is assumed, i.e. [].
    search_PATH[in]     Boolean value that indicates if the paths specified by
                        the PATH environment variable will be used to search
                        for the tool. By default the PATH will not be searched,
                        i.e. search_PATH=False.
    Returns (string) full path to tool
    """

    search_paths = []

    if basedir:
        # Add specified basedir path to search paths
        _add_basedir(search_paths, basedir)
    if defaults_paths and len(defaults_paths):
        # Add specified default paths to search paths
        for path in defaults_paths:
            search_paths.append(path)
    else:
        # Add default basedir paths to search paths
        _add_basedir(search_paths, "/usr/local/mysql/")
        _add_basedir(search_paths, "/usr/sbin/")
        _add_basedir(search_paths, "/usr/share/")

    # Search in path from the PATH environment variable
    if search_PATH:
        for path in os.environ['PATH'].split(os.pathsep):
            search_paths.append(path)

    if os.name == "nt" and fix_ext:
        tool = tool + ".exe"
    # Search for the tool
    for path in search_paths:
        norm_path = os.path.normpath(path)
        if os.path.isdir(norm_path):
            toolpath = os.path.join(norm_path, tool)
            if os.path.isfile(toolpath):
                return toolpath
            else:
                if tool == "mysqld.exe":
                    toolpath = os.path.join(norm_path, "mysqld-nt.exe")
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


def show_file_statistics(file_name, wild=False, out_format="GRID"):
    """Show file statistics for file name specified

    file_name[in]    target file name and path
    wild[in]         if True, get file statistics for all files with prefix of
                     file_name. Default is False
    out_format[in]   output format to print file statistics. Default is GRID.
    """

    def _get_file_stats(path, file_name):
        stats = os.stat(os.path.join(path, file_name))
        return ((file_name, stats.st_size, time.ctime(stats.st_ctime),
                 time.ctime(stats.st_mtime)))

    columns = ["File", "Size", "Created", "Last Modified"]
    rows = []
    path, filename = os.path.split(file_name)
    if wild:
        for root, dirs, files in os.walk(path):
            for f in files:
                if f.startswith(filename):
                    rows.append(_get_file_stats(path, f))
    else:
        rows.append(_get_file_stats(path, filename))

    print_list(sys.stdout, out_format, columns, rows)


def remote_copy(filepath, user, host, local_path, verbosity=0):
    """Copy a file from a remote machine to the localhost.

    filepath[in]       The full path and file name of the file on the remote
                       machine
    user[in]           Remote login
    local_path[in]     The path to where the file is to be copie

    Returns bool - True = succes, False = failure or exception
    """

    if os.name == "posix":  # use scp
        run_cmd = "scp %s@%s:%s %s" % (user, host, filepath, local_path)
        if verbosity > 1:
            print "# Command =", run_cmd
        print "# Copying file from %s:%s to %s:" % (host, filepath, local_path)
        proc = subprocess.Popen(run_cmd, shell=True)
        ret_val = proc.wait()
    else:
        print "Remote copy not supported. Please use UNC paths and omit " + \
              "the --remote-login option to use a local copy operation."
    return True
