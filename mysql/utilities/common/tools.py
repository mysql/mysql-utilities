#
# Copyright (c) 2010, 2016, Oracle and/or its affiliates. All rights reserved.
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

import inspect
import os
import re
import sys
import shlex
import shutil
import socket
import subprocess
import time

try:
    import ctypes
except ImportError:
    pass

from mysql.utilities import (PYTHON_MIN_VERSION, PYTHON_MAX_VERSION,
                             CONNECTOR_MIN_VERSION)
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
                  defaults_paths=None, search_PATH=False, quote=False):
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
    quote[in]           If True, the result path is surrounded with the OS
                        quotes.
    Returns (string) full path to tool
    """
    if not defaults_paths:
        defaults_paths = []
    search_paths = []
    if quote:
        if os.name == "posix":
            quote_char = "'"
        else:
            quote_char = '"'
    else:
        quote_char = ''
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
                return r"%s%s%s" % (quote_char, toolpath, quote_char)
            else:
                if tool == "mysqld.exe":
                    toolpath = os.path.join(norm_path, "mysqld-nt.exe")
                    if os.path.isfile(toolpath):
                        return r"%s%s%s" % (quote_char, toolpath, quote_char)
    if required:
        raise UtilError("Cannot find location of %s." % tool)

    return None


def delete_directory(path):
    """Remove a directory (folder) and its contents.

    path[in]           target directory
    """
    if os.path.exists(path):
        # It can take up to 10 seconds for Windows to 'release' a directory
        # once a process has terminated. We wait...
        if os.name == "nt":
            stop = 10
            i = 1
            while i < stop and os.path.exists(path):
                shutil.rmtree(path, True)
                time.sleep(1)
                i += 1
        else:
            shutil.rmtree(path, True)


def estimate_free_space(path, unit_multiple=2):
    """Estimated free space for the given path.

    Calculates free space for the given path, returning the value
    on the size given by the unit_multiple.

    path[in]             the path to calculate the free space for.
    unit_multiple[in]    the unit size given as a multiple.
                         Accepts int values > to zero.
                         Size    unit_multiple
                          bytes        0
                          Kilobytes    1
                          Megabytes    2
                          Gigabytes    3
                         and so on...

    Returns folder/drive free space (in bytes)
    """
    unit_size = 1024 ** unit_multiple
    if os.name == 'nt':
        free_bytes = ctypes.c_ulonglong(0)
        ctypes.windll.kernel32.GetDiskFreeSpaceExW(ctypes.c_wchar_p(path),
                                                   None, None,
                                                   ctypes.pointer(free_bytes))
        return free_bytes.value / unit_size
    else:
        st = os.statvfs(path)  # pylint: disable=E1101
        return st.f_bavail * st.f_frsize / unit_size


def execute_script(run_cmd, filename=None, options=None, verbosity=False):
    """Execute a script.

    This method spawns a subprocess to execute a script. If a file is
    specified, it will direct output to that file else it will suppress
    all output from the script.

    run_cmd[in]        command/script to execute
    filename[in]       file path name to file, os.stdout, etc.
                       Default is None (do not log/write output)
    options[in]        arguments for script
                       Default is no arguments ([])
    verbosity[in]      show result of script
                       Default is False

    Returns int - result from process execution
    """
    if options is None:
        options = []
    if verbosity:
        f_out = sys.stdout
    else:
        if not filename:
            filename = os.devnull
        f_out = open(filename, 'w')

    is_posix = (os.name == "posix")
    command = shlex.split(run_cmd, posix=is_posix)

    if options:
        command.extend([str(opt) for opt in options])

    if verbosity:
        print("# SCRIPT EXECUTED: {0}".format(" ".join(command)))

    try:
        proc = subprocess.Popen(command, shell=False,
                                stdout=f_out, stderr=f_out)
    except:
        _, err, _ = sys.exc_info()
        raise UtilError(str(err))

    ret_val = proc.wait()
    if not verbosity:
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
    else:  # must be windows
        run_cmd = "ping -n %s %s" % (timeout, host)

    ret_val = execute_script(run_cmd)

    return (ret_val == 0)


def parse_mysqld_version(vers_str):
    """ Parse the MySQL version string.

    vers_str[in]     MySQL Version from client

    Returns string = version string
    """
    pattern = r"mysqld(?:\.exe)?\s+Ver\s+(\d+\.\d+\.\S+)\s"
    match = re.search(pattern, vers_str)
    if not match:
        return None
    version = match.group(1)
    try:
        # get the version digits. If more than 2, we get first 3 parts
        # pylint: disable=W0612
        maj_ver, min_ver, dev = version.split(".", 2)
        rel = dev.split("-", 1)
        return (maj_ver, min_ver, rel[0])
    except:
        return None


def get_mysqld_version(mysqld_path):
    """Return the version number for a mysqld executable.

    mysqld_path[in]    location of the mysqld executable

    Returns tuple - (major, minor, release), or None if error
    """
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
    # strip path for long, unusual paths that contain version number
    fixed_str = "{0} {1}".format("mysqld", line.strip(mysqld_path))
    return parse_mysqld_version(fixed_str)


def show_file_statistics(file_name, wild=False, out_format="GRID"):
    """Show file statistics for file name specified

    file_name[in]    target file name and path
    wild[in]         if True, get file statistics for all files with prefix of
                     file_name. Default is False
    out_format[in]   output format to print file statistics. Default is GRID.
    """

    def _get_file_stats(path, file_name):
        """Return file stats
        """
        stats = os.stat(os.path.join(path, file_name))
        return ((file_name, stats.st_size, time.ctime(stats.st_ctime),
                 time.ctime(stats.st_mtime)))

    columns = ["File", "Size", "Created", "Last Modified"]
    rows = []
    path, filename = os.path.split(file_name)
    if wild:
        for _, _, files in os.walk(path):
            for f in files:
                if f.startswith(filename):
                    rows.append(_get_file_stats(path, f))
    else:
        rows.append(_get_file_stats(path, filename))

    # Local import is needed because of Python compability issues
    from mysql.utilities.common.format import print_list
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
            print("# Command =%s" % run_cmd)
        print("# Copying file from %s:%s to %s:" %
              (host, filepath, local_path))
        proc = subprocess.Popen(run_cmd, shell=True)
        proc.wait()
    else:
        print("Remote copy not supported. Please use UNC paths and omit "
              "the --remote-login option to use a local copy operation.")
    return True


def check_python_version(min_version=PYTHON_MIN_VERSION,
                         max_version=PYTHON_MAX_VERSION,
                         raise_exception_on_fail=False,
                         name=None, print_on_fail=True,
                         exit_on_fail=True,
                         return_error_msg=False):
    """Check the Python version compatibility.

    By default this method uses constants to define the minimum and maximum
    Python versions required. It's possible to override this by passing new
    values on ``min_version`` and ``max_version`` parameters.
    It will run a ``sys.exit`` or raise a ``UtilError`` if the version of
    Python detected it not compatible.

    min_version[in]               Tuple with the minimum Python version
                                  required (inclusive).
    max_version[in]               Tuple with the maximum Python version
                                  required (exclusive).
    raise_exception_on_fail[in]   Boolean, it will raise a ``UtilError`` if
                                  True and Python detected is not compatible.
    name[in]                      String for a custom name, if not provided
                                  will get the module name from where this
                                  function was called.
    print_on_fail[in]             If True, print error else do not print
                                  error on failure.
    exit_on_fail[in]              If True, issue exit() else do not exit()
                                  on failure.
    return_error_msg[in]          If True, and is not compatible
                                  returns (result, error_msg) tuple.
    """

    # Only use the fields: major, minor and micro
    sys_version = sys.version_info[:3]

    # Test min version compatibility
    is_compat = min_version <= sys_version

    # Test max version compatibility if it's defined
    if is_compat and max_version:
        is_compat = sys_version < max_version

    if not is_compat:
        if not name:
            # Get the utility name by finding the module
            # name from where this function was called
            frm = inspect.stack()[1]
            mod = inspect.getmodule(frm[0])
            mod_name = os.path.splitext(
                os.path.basename(mod.__file__))[0]
            name = '%s utility' % mod_name

        # Build the error message
        if max_version:
            max_version_error_msg = 'or higher and lower than %s' % \
                '.'.join([str(el) for el in max_version])
        else:
            max_version_error_msg = 'or higher'

        error_msg = (
            'The %(name)s requires Python version %(min_version)s '
            '%(max_version_error_msg)s. The version of Python detected was '
            '%(sys_version)s. You may need to install or redirect the '
            'execution of this utility to an environment that includes a '
            'compatible Python version.'
        ) % {
            'name': name,
            'sys_version': '.'.join([str(el) for el in sys_version]),
            'min_version': '.'.join([str(el) for el in min_version]),
            'max_version_error_msg': max_version_error_msg
        }

        if raise_exception_on_fail:
            raise UtilError(error_msg)

        if print_on_fail:
            print('ERROR: %s' % error_msg)

        if exit_on_fail:
            sys.exit(1)

        if return_error_msg:
            return is_compat, error_msg

    return is_compat


def check_port_in_use(host, port):
    """Check to see if port is in use.

    host[in]            Hostname or IP to check
    port[in]            Port number to check

    Returns bool - True = port is available, False is not available
    """
    try:
        sock = socket.create_connection((host, port))
    except socket.error:
        return True
    sock.close()
    return False


def requires_encoding(orig_str):
    r"""Check to see if a string requires encoding

    This method will check to see if a string requires encoding to be used
    as a MySQL file name (r"[\w$]*").

    orig_str[in]        original string

    Returns bool - True = requires encoding, False = does not require encoding
    """
    ok_chars = re.compile(r"[\w$]*")
    parts = ok_chars.findall(orig_str)
    return len(parts) > 2 and parts[1].strip() == ''


def encode(orig_str):
    r"""Encode a string containing non-MySQL observed characters

    This method will take a string containing characters other than those
    recognized by MySQL (r"[\w$]*") and covert them to embedded ascii values.
    For example, "this.has.periods" becomes "this@002ehas@00e2periods"

    orig_str[in]        original string

    Returns string - encoded string or original string
    """
    # First, find the parts that match valid characters
    ok_chars = re.compile(r"[\w$]*")
    parts = ok_chars.findall(orig_str)

    # Now find each part that does not match the list of valid characters
    # Save the good parts
    i = 0
    encode_parts = []
    good_parts = []
    for part in parts:
        if not len(part):
            continue
        good_parts.append(part)
        if i == 0:
            i = len(part)
        else:
            j = orig_str[i:].find(part)
            encode_parts.append(orig_str[i:i + j])
            i += len(part) + j

    # Next, convert the non-valid parts to the form @NNNN (hex)
    encoded_parts = []
    for part in encode_parts:
        new_part = "".join(["@%04x" % ord(c) for c in part])
        encoded_parts.append(new_part)

    # Take the good parts and the encoded parts and reform the string
    i = 0
    new_parts = []
    for part in good_parts[:len(good_parts) - 1]:
        new_parts.append(part)
        new_parts.append(encoded_parts[i])
        i += 1
    new_parts.append(good_parts[len(good_parts) - 1])

    # Return the new string
    return "".join(new_parts)


def requires_decoding(orig_str):
    """Check to if a string required decoding

    This method will check to see if a string requires decoding to be used
    as a filename (has @NNNN entries)

    orig_str[in]        original string

    Returns bool - True = requires decoding, False = does not require decoding
    """
    return '@' in orig_str


def decode(orig_str):
    r"""Decode a string containing @NNNN entries

    This method will take a string containing characters other than those
    recognized by MySQL (r"[\w$]*") and covert them to character values.
    For example, "this@002ehas@00e2periods" becomes "this.has.periods".

    orig_str[in]        original string

    Returns string - decoded string or original string
    """
    parts = orig_str.split('@')
    if len(parts) == 1:
        return orig_str
    new_parts = [parts[0]]
    for part in parts[1:]:
        # take first four positions and convert to ascii
        new_parts.append(chr(int(part[0:4], 16)))
        new_parts.append(part[4:])
    return "".join(new_parts)


def check_connector_python(print_error=True,
                           min_version=CONNECTOR_MIN_VERSION):

    """Check to see if Connector Python is installed and accessible and
    meets minimum required version.

    By default this method uses constants to define the minimum
    C/Python version required. It's possible to override this by passing  a new
    value to ``min_version`` parameter.

    print_error[in]               If True, print error else do not print
                                  error on failure.
    min_version[in]               Tuple with the minimum C/Python version
                                  required (inclusive).

    """
    is_compatible = True
    try:
        import mysql.connector  # pylint: disable=W0612
    except ImportError:
        if print_error:
            print("ERROR: The MySQL Connector/Python module was not found. "
                  "MySQL Utilities requires the connector to be installed. "
                  "Please check your paths or download and install the "
                  "Connector/Python from http://dev.mysql.com.")
        return False
    else:
        try:
            sys_version = mysql.connector.version.VERSION[:3]
        except AttributeError:
            is_compatible = False

    if is_compatible and sys_version >= min_version:
        return True
    else:
        if print_error:
            print("ERROR: The MYSQL Connector/Python module was found "
                  "but it is either not properly installed or it is an "
                  "old version. MySQL Utilities requires Connector/Python "
                  "version > '{0}'. Download and install Connector/Python "
                  "from http://dev.mysql.com.".format(min_version))
        return False


def print_elapsed_time(start_time):
    """Print the elapsed time to stdout (screen)

    start_time[in]      The starting time of the test
    """
    stop_time = time.time()
    display_time = stop_time - start_time
    print("Time: {0:.2f} sec\n".format(display_time))


def join_and_build_str(list_of_strings, sep=', ', last_sep='and'):
    """Buils and returns a string from a list of elems.

    list_of_strings[in]    the list of strings that will be joined into a
                           single string.
    sep[in]                the separator that will be used to group all strings
                           except the last one.
    last_sep[in]           the separator that is used in last place
    """
    if list_of_strings:
        if len(list_of_strings) > 1:
            res_str = "{0} {1} {2}".format(
                sep.join(list_of_strings[:-1]), last_sep, list_of_strings[-1])
        else:  # list has a single elem
            res_str = list_of_strings[0]
    else:  # if list_of_str is empty, return empty string
        res_str = ""
    return res_str
