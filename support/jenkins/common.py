# Copyright (c) 2013, 2015, Oracle and/or its affiliates. All rights reserved.
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

"""This file contains python script to be used inside Jenkins and whose job is
to run the entire MUT test suite with different MySQL Server versions"""

from __future__ import print_function
import contextlib
import csv
import glob
import os
import re
import shlex
import shutil
import socket
import subprocess
import sys
import tarfile
import time
import zipfile

from threading import Thread
from Queue import Queue, Empty

SPECIFIC_TESTS = {
    "5.6.9": ['failover', 'failover_errors ',
              'failover_instances', 'rpl_admin_errant_transactions',
              "failover_privileges", ],
    "5.6.8": ["replication.check_gtid_version"],
}

# List of tests that should be removed from the final skip list
_IGNORE_TESTS_COMMON = set(['main.check_unsupported_server_version',
                            'performance.copy_db_multithreaded',
                            'main.test_sql_template',
                            "main.get_tool_windows",
                            ])

_IGNORE_TESTS_LINUX = set(['main.get_tool_windows']) | _IGNORE_TESTS_COMMON

_IGNORE_TESTS_WINDOWS = set(["main.check_index_best_worst_large",
                            "replication.rpl_admin_scripts",
                            "performance.copy_db_multithreaded",
                            "replication.failover_daemon_errors",
                            "replication.failover_daemon",
                             ]) | _IGNORE_TESTS_COMMON

if os.name == 'nt':
    IGNORE_TESTS = _IGNORE_TESTS_WINDOWS
else:
    IGNORE_TESTS = _IGNORE_TESTS_LINUX


class MUTOutputParser(object):
    def __init__(self, tests=None):
        self._tests = tests
        self._failed = set()
        self._skipped = set()
        self._successful = set()
        self.pattern = re.compile(r"^((?:main|experimental|replication)\.\w+)"
                                  r"\s+(?:\S+?)?(SKIP|pass|FAIL)")

    def parse(self, text):
        match = re.match(self.pattern, text)
        if match:
            test_name, result = match.groups()
            {'pass': self._successful,
             'FAIL': self._failed,
             'SKIP': self._skipped}.get(result).add(test_name)

    @property
    def failed_tests(self):
        return self._failed

    @property
    def skipped_tests(self):
        if self._tests is None:
            return self._skipped - (self._failed | self._successful |
                                    IGNORE_TESTS)
        else:
            return self._tests - (self._failed | self._successful |
                                  IGNORE_TESTS)


class MTRParser(object):
    """Parser Class whose goal is to find the port and socket in which the
    server started by MTR is listening"""

    def __init__(self):
        self.post_pattern = re.compile(r'^worker\[\d+\] Server\(s\) started, '
                                       r'not waiting for them to finish')

        self.port_pattern = re.compile(r'^worker\[\d+\] mysqld\.\d+\s+(\d+)'
                                       r'\s+(.*?\.sock)')
        self.port = None
        self.socket = None
        self.skip = False
        self.previous = ''

    def parse(self, text):
        """Parse text in order to find the port number and socket of the
        mysql server launched by MTR"""

        # if this flag is set, the information has already been found, or it
        # won't be retrieved anymore so lets skip the parsing
        if self.skip:
            return None

        # First we need to search for the post pattern.
        post_match = re.match(self.post_pattern, text)
        if post_match:
            # if found, now we should look at the previous sentence for the
            # information we want
            match = re.match(self.port_pattern, self.previous)
            if match:
                self.port = match.group(1)
                print("PORT FOUND!!!!!! {0}".format(self.port))
                self.socket = match.group(2)
                print("SOCKET FOUND!!!!!! {0}".format(self.socket))
                self.skip = True
            else:  # couldn't find socket and port information
                self.skip = True

        # Store sentence
        self.previous = text


def _is_up_and_running(address, port, max_retries=10, retry_interval=3):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    for i in range(max_retries):
        time.sleep(retry_interval)
        try:
            sock.connect((address, int(port)))
            sock.close()
            break
        except socket.error:
            continue
    else:
        return False
    return True


@contextlib.contextmanager
def working_path(new_path, verbose=False):
    old_path = os.getcwd()
    if verbose:
        print("# Changing PATH from {0} to {1}".format(old_path, new_path))
    os.chdir(new_path)
    try:
        yield
    finally:
        if verbose:
            print("# Returning to previous PATH: {0}".format(old_path))
        os.chdir(old_path)


def get_major_version(version):
    """Returns the major version number"""
    return version[:version.rfind('.')]


def pprint_mysql_version(version, tty_size=80):
    """Pretty prints the mysql version using tty_size chars"""
    if len(version) > (tty_size - 4):
        print("tty_size too small to fit version")

    vmid, vrest = divmod(len(version), 2)
    tmid, trest = divmod(tty_size-2, 2)
    left_spaces = tmid - vmid
    right_spaces = tmid + trest-vmid-vrest
    print('#'*tty_size)
    print("#{0}{1}{2}#".format(' '*left_spaces, version, ' '*right_spaces))
    print('#'*tty_size)


def kill_process(pid, force=False):
    if os.name == "posix":
        if force:
            os.kill(pid, subprocess.signal.SIGABRT)
        else:
            os.kill(pid, subprocess.signal.SIGTERM)
    else:
        f_out = open(os.devnull, 'w')
        ret_code = subprocess.call("taskkill /F /T /PID {0}".format(pid),
                                   shell=True, stdout=f_out, stdin=f_out)
        if ret_code not in (0, 128):
            print("Unable to successfully kill process with PID "
                  "{0}".format(pid))
        f_out.close()


@contextlib.contextmanager
def mysql_server(run_cmd, param_dict):
    """MySQL Server context manager"""
    # makes backup of environ and adds base_dir to path
    env_backup = os.environ.copy()
    base_dir = param_dict['base_dir']
    results_dir = param_dict['results_dir']
    on_posix = 'posix' in sys.builtin_module_names

    # Pick correct path separator according to the OS
    path_separator = ':' if on_posix else ';'

    # Add the mysql bin folder to path
    os.environ['PATH'] = "{0}{1}{2}".format(os.path.join(base_dir, 'bin'),
                                            path_separator, os.environ['PATH'])

    if not os.path.exists(results_dir):
        os.mkdir(results_dir)

    mtr_dir = os.path.join(base_dir, "mysql-test")
    with working_path(mtr_dir):
        mtr_parser = MTRParser()
        print("# Launching MySQL Server \n %s" % run_cmd)
        if on_posix:
            run_cmd_ = shlex.split(run_cmd)
        else:
            run_cmd_ = run_cmd

        # Run mysql-test-run
        mtr = subprocess.Popen(run_cmd_, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, shell=not on_posix,
                               universal_newlines=True)

        # Print and parse the mtr output
        print_parse_subproc(mtr, mtr_parser)

        # wait for mtr to finish
        mtr.wait()

        # Check for port
        port = mtr_parser.port
        if port is None:
            print("# ERROR: Couldn't parse the port nor the socket of "
                  "the server started by MTR")
            sys.exit(1)

        #Check if the mysql server started by mtr is running
        isUp = _is_up_and_running(address='localhost', port=port,
                                  retry_interval=10, max_retries=6)
        try:
            yield isUp, port
        finally:
            # Restore environment variables
            os.environ = env_backup

            # Get running pids
            pid_dir = os.path.join(base_dir, "mysql-test", "var", "run")
            pid_files = os.listdir(pid_dir)
            print("# Found {0} servers running".format(len(pid_files)))
            # Kill running servers
            for pid_file in pid_files:
                with open(os.path.join(pid_dir, pid_file), 'r') as pid_f:
                    pid = int(pid_f.readline().strip("\n"))
                print("# Killing MySQL Server with pid '{0}'".format(pid))
                kill_process(pid)


def get_server_info(filename):
    """Returns a tuple ((is_COMMERCIAL?,MAJOR_VERSION),NAME) with information
    from the server or None if unable to parse server version
    isCOMMERCIAL? is a Boolean value, True if server is either advanced or
    enterprise version.
    MAJOR_VERSION is a string with the major version of the server, e.g
    5.1, 5.6, 5.6...
    NAME is a string with the full name of the server
    """

    match = re.search(r'mysql\-(advanced|enterprise)?(?:\-?noinstall)'
                      r'?\-?(\d\.\d\.\d{1,2})', filename, re.IGNORECASE)
    if match:
        type_, version = match.groups()
        return (bool(type_), version), match.group(0)
    else:
        print("# Unable to recognize the server version %s" % filename)
        return None


def _extract_tar(filename, path='.', replace=False):
    #Extracts <filename>.tar.gz file to the <path>
    tar = tarfile.open(filename)
    (dirname, fname) = os.path.split(filename)
    # Take of .tar.gz and get the archive name
    shortname = fname[:fname.index(".tar.gz")]
    extract_foldername = os.path.join(path, shortname)
    if (os.path.exists(extract_foldername) and
            os.path.isdir(extract_foldername)):
        if replace:
            print("# Removing previously existing folder")
            shutil.rmtree(extract_foldername)
        else:
            print("# Skipping extraction, folder '{0}' already "
                  "exists".format(shortname))
            return shortname

    print("# Extracting '%s' to '%s'" % (filename, extract_foldername))
    tar.extractall(path=path)
    tar.close()
    print("# Finished extraction of %s" % filename)
    return shortname


def _extract_zip(filename, path='.', replace=False):
    #Extracts <filename>.zip file to the <path>
    zip_ = zipfile.ZipFile(filename)
    (dirname, fname) = os.path.split(filename)
    # Take of .zip and get the archive name
    shortname = next(iter(zip_.namelist())).split('/')[0]
    extract_foldername = os.path.join(path, shortname)
    if (os.path.exists(extract_foldername) and
            os.path.isdir(extract_foldername)):
        if replace:
            print("# Removing previously existing folder")
            shutil.rmtree(extract_foldername)
        else:
            print("# Skipping extraction, folder '{0}' already "
                  "exists".format(shortname))
            return shortname

    print("# Extracting '%s' to '%s'" % (filename, extract_foldername))
    zip_.extractall(path=path)
    zip_.close()
    print("# Finished extraction of %s" % filename)
    return shortname


def extract_file(filename, path='.', replace=False):
    # Checks if file is .zip or .tar.gz and calls the
    # appropriate extraction function
    _, ext = os.path.splitext(filename)
    if ext not in ['.gz', '.zip']:
        print("Unknown archive format, '{0}' is neither a zip nor a "
              "tar.gz file".format(filename))
        return None
    if ext == '.zip':
        return _extract_zip(filename, path, replace)
    else:  # is tar.gz
        return _extract_tar(filename, path, replace)


def execute(command, check_exit_status=True, env=None, out=None,
            err=None):
    print("# Executing Command: {0}".format(command))
    is_posix = True if os.name == 'posix' else False
    clist = shlex.split(command, posix=is_posix)
    exit_status = subprocess.call(clist, env=env, stdout=out,
                                  stderr=err)
    if check_exit_status and exit_status:
        print("# Exit status '{0}' after "
              "executing '{1}'".format(exit_status, command))
        sys.exit(exit_status)
    return exit_status


def execute_raw(command, check_exit_status=True, env=None, out=None,
                err=None):
    print("# Executing Command {0}".format(command))
    exit_status = subprocess.call(command, env=env, stdout=out,
                                  stderr=err, shell=True)
    if check_exit_status and exit_status:
        print("# exit status '{0}' after "
              "executing '{1}'".format(exit_status, command))
        sys.exit(exit_status)
    return exit_status


def _enqueue_output(out, queue):
    for line in iter(out.readline, b''):
        queue.put(line)
    out.close()


def print_parse_subproc(process, parser):
    q1 = Queue()
    q2 = Queue()
    t1 = Thread(target=_enqueue_output, args=(process.stdout, q1))
    t2 = Thread(target=_enqueue_output, args=(process.stderr, q2))
    t1.daemon = True
    t2.daemon = True
    t1.start()
    t2.start()
    # While process isn't finished, read output
    while process.poll() is None:
        try:  # get stdout text
            line_out = q1.get_nowait()
            print(line_out, end='')
            parser.parse(line_out)
        except Empty:
            pass
        try:  # get stderr text
            line_err = q2.get_nowait()
            print(line_err, end='')
        except Empty:
            pass

    # Read the rest of the text from the queues
    while True:
        try:  # get stdout text
            line_out = q1.get_nowait()
            print(line_out, end='')
            parser.parse(line_out)
        except Empty:
            break

    while True:
        try:  # get stderr text
            line_err = q2.get_nowait()
            print(line_err, end='')
        except Empty:
            break


def run_mut(port, parser, specific_tests=None, env=None, force=False,
            verbose=False, override_cmd=None):
    environ = env if env is not None else os.environ
    print("\n\n\n\n ####### Running MUT #######\n\n")
    command = "python mut.py --server=root@localhost:{0} ".format(port)

    if override_cmd:
        command = "{0} {1}".format(command, override_cmd)

    elif specific_tests:  # Override cmd has priority over specific tests
        tests = " ".join(specific_tests)
        command = "{0} {1}".format(command, tests)

    if force:
        command = "{0} -f".format(command)
    if verbose:
        command = "{0} -vvv".format(command)

    print("# Executing command: {0}".format(command))
    on_posix = 'posix' in sys.builtin_module_names
    clist = shlex.split(command, posix=on_posix)
    proc = subprocess.Popen(clist, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, env=environ)

    print_parse_subproc(proc, parser)
    proc.wait()
    exit_status = proc.returncode
    if exit_status:
        print("\n\n# ERROR Exit status '{0}' after executing command "
              "'{1}'".format(exit_status, command))
    return exit_status


def copy_connector(connector_path):
    """Installs the connector python on connector_path to the current
    working directory.

    connector_path [in]   path where we can find the connector python

    it must be called on the root of the utilities folder"""
    cwd = os.getcwd()
    # check if we are on the root of the utilities folder
    dest_folder = cwd
    install_cmd = ("python setup.py install --root={0} --install-lib=. "
                   "".format(dest_folder))

    with working_path(os.path.normpath(connector_path)):
        print ("Installing connector using command '{0}'".format(install_cmd))
        subprocess.call(install_cmd, shell=True)


def _read_disabled_tests(filename):
    disabled_tests = set()
    with open(filename) as f:
        csv_reader = csv.reader(f)
        for row in csv_reader:
            if row[0][0] != '#':
                disabled_tests.add(row[0])
    return disabled_tests


def get_mut_test_list(util_base):
    """Returns a set with the name of all of MUT's tests
    util_base must be the full_path to the base of the utilities
    """

    # check if we are on the root of the utilities folder
    is_root = ('.bzr' in os.listdir(util_base) and
               "mysql-test" in os.listdir(util_base))
    if not is_root:
        print("# Error: please chdir to the root utilities folder")
        sys.exit(1)

    # Get all the disabled_tests
    disabled_tests = _read_disabled_tests(os.path.join(util_base, "mysql-test",
                                                       "disabled"))
    test_names = set()

    # Get main suite test names and remove
    suite_tests = glob.iglob(os.path.join(util_base, 'mysql-test', "t",
                                          "*.py"))
    test_names.update(["main.{0}".format(os.path.basename(test[:-3]))
                       for test in suite_tests])

    # get other suites' test names
    suite_folders = os.listdir(os.path.join(util_base, "mysql-test", "suite"))
    for suite in suite_folders:
        suite_tests = glob.iglob(os.path.join(util_base, "mysql-test", "suite",
                                 suite, "t", "*.py"))
        test_names.update(["{0}.{1}".format(suite, os.path.basename(test[:-3]))
                           for test in suite_tests])

    return test_names - (disabled_tests | set(["main.__init__"]))


def load_databases(bin_path, database_files, user='root',
                   passwd=None, host='127.0.0.1', port=3306):
    """load all the .sql files in the in the order found in <database_files>
    list using the mysql client executable found in <bin_path>. """
    if not ('mysql' in os.listdir(bin_path) or
            'mysql.exe' in os.listdir(bin_path)):
        print("# error: could not find mysql client executable "
              "in '{0}'".format(bin_path))
        sys.exit(1)
    for db_file in database_files:
        path, filename = os.path.split(db_file)
        if os.path.splitext(filename)[1] != '.sql':  # only load *.sql files
            print("# WARNING: We can only load *.sql files, '{0}' could not "
                  "be loaded and will be skipped".format(db_file))

        with working_path(path):
            if os.name == 'nt':  # if windows use .exe extension
                cmd = "{0} -u {1} --host={2} --port={3}".format(
                    os.path.join(os.path.realpath(bin_path), 'mysql.exe'),
                    user, host, port)
            else:  # Unix
                cmd = "{0} -u {1} --host={2} --port={3}".format(
                    os.path.join(os.path.realpath(bin_path), 'mysql'),
                    user, host, port)

            if passwd is not None:
                cmd = "{0} --password={1}".format(cmd, passwd)
            cmd = "{0} < {1}".format(cmd, filename)
            execute_raw(cmd)
            print("# Database file '{0}' loaded into database running on "
                  "port '{1}'".format(db_file, port))
