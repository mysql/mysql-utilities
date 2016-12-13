#
# Copyright (c) 2014, 2016, Oracle and/or its affiliates. All rights reserved.
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
This file contains a base class that implements a POSIX daemon.
"""

import os
import sys
import time
import atexit
import signal
import logging

from mysql.utilities.exception import UtilDaemonError


class Daemon(object):
    """Posix Daemon.

    This is a base class for implementing a POSIX daemon.
    """
    def __init__(self, pidfile, umask=0o27, chdir="/", stdin=None, stdout=None,
                 stderr=None):
        """Constructor

        pidfile[in]  pid filename.
        umask[in]    posix umask.
        chdir[in]    working directory.
        stdin[in]    standard input object.
        stdout[in]   standard output object.
        stderr[in]   standard error object.
        """
        self.pid = None
        self.pidfile = os.path.realpath(os.path.normpath(pidfile))
        self.umask = umask
        self.chdir = chdir
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr

    def _report(self, message, level=logging.INFO, print_msg=True):
        """Log message if logging is on.

        This method will log the message presented if the log is turned on.
        Specifically, if options['log_file'] is not None. It will also
        print the message to stdout.

        This method should be overridden when subclassing Daemon.

        message[in]    message to be printed.
        level[in]      level of message to log. Default = INFO.
        print_msg[in]  if True, print the message to stdout. Default = True.
        """
        raise NotImplementedError("_report() method is not implemented.")

    def run(self, *args, **kwargs):
        """It will be called after the process has been daemonized by start()
        or restart.

        This method should be overridden when subclassing Daemon.
        """
        raise NotImplementedError("run() method is not implemented.")

    def start(self, detach_process=True):
        """Starts the daemon.

        It will start the daemon if detach_process is True.
        """
        if detach_process:
            # Check for a pidfile presence
            try:
                with open(self.pidfile, "rb") as f:
                    self.pid = int(f.read().strip())
            except IOError:
                self.pid = None
            except SystemExit:
                self.pid = None
            except ValueError:
                self.pid = None

            if self.pid:
                # Daemon already runs
                msg = ("pidfile {0} already exists. The daemon is already "
                       "running?".format(self.pidfile))
                self._report(msg, logging.CRITICAL)
                raise UtilDaemonError(msg)

            # Start the daemon
            self.daemonize()

        # Run automatic failover
        return self.run()

    def cleanup(self):
        """It will be called during the process to stop the daemon.

        This method should be overridden when subclassing Daemon.
        """
        raise NotImplementedError("cleanup() method is not implemented.")

    def stop(self):
        """Stops the daemon.

        It will stop the daemon by sending a signal.SIGTERM to the process.
        """
        # Get the pid from the pidfile
        try:
            with open(self.pidfile, "rb") as f:
                self.pid = int(f.read().strip())
        except IOError:
            self._report("pidfile {0} does not exist.".format(self.pidfile),
                         logging.ERROR)
            return False
        except ValueError:
            self._report("Invalid pid in pidfile {0}.".format(self.pidfile),
                         logging.ERROR)
            return False

        # Kill the daemon process
        try:
            while 1:
                os.kill(self.pid, signal.SIGTERM)
                time.sleep(0.1)
        except OSError as err:
            strerror = err.strerror
            if err.errno == 3:  # No such process
                if os.path.exists(self.pidfile):
                    self.delete_pidfile()
            else:
                msg = "Unable to delete pidfile: {0}".format(strerror)
                self._report(msg, logging.ERROR)
                raise UtilDaemonError(msg)

        return True

    def restart(self):
        """Restarts the daemon.

        It will execute a stop and start on the daemon.
        """
        self.stop()
        return self.start()

    def daemonize(self):
        """Creates the daemon.

        It will fork a child process and then exit parent. By performing a
        double fork, set the current process's user id, change the current
        working directory, set the current numeric umask, redirect standard
        streams and write the pid to a file.
        """
        def redirect_stream(system_stream, target_stream):
            """Redirect a system stream to a specified file.
            """
            if target_stream is None:
                target_f = os.open(os.devnull, os.O_RDWR)
            else:
                target_f = target_stream.fileno()
            os.dup2(target_f, system_stream.fileno())

        def fork_then_exit_parent(error_message):
            """Fork a child process, then exit the parent process.
            """
            try:
                pid = os.fork()
                if pid > 0:
                    os._exit(0)  # pylint: disable=W0212
            except OSError as err:
                msg = "{0}: [{1}] {2}".format(error_message, err.errno,
                                              err.strerror)
                self._report(msg, logging.CRITICAL)
                raise UtilDaemonError(msg)

        # Fork
        fork_then_exit_parent("Failed first fork.")

        try:
            os.setsid()
            os.chdir(self.chdir)
            os.umask(self.umask)
        except Exception as err:
            msg = "Unable to change directory ({0})".format(err)
            self._report(msg, logging.CRITICAL)
            raise UtilDaemonError(msg)

        # Double fork
        fork_then_exit_parent("Failed second fork.")

        # Redirect streams
        redirect_stream(sys.stdin, self.stdin)
        redirect_stream(sys.stdout, self.stdout)
        redirect_stream(sys.stderr, self.stderr)

        # Call a cleanup task to unregister the master.
        atexit.register(self.cleanup)
        # write pidfile
        atexit.register(self.delete_pidfile)
        pid = str(os.getpid())
        try:
            with open(self.pidfile, "w") as f:
                f.write("{0}\n".format(pid))
        except IOError as err:
            msg = "Unable to write pidfile: {0}".format(err.strerror)
            self._report(msg, logging.CRITICAL)
            raise UtilDaemonError(msg)

    def delete_pidfile(self):
        """Deletes pidfile.
        """
        try:
            os.remove(self.pidfile)
        except (OSError, IOError) as err:
            msg = "Unable to delete pidfile: {0}".format(err.strerror)
            self._report(msg, logging.ERROR)
            raise UtilDaemonError(msg)
