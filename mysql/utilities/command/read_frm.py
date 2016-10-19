#
# Copyright (c) 2013, 2016, Oracle and/or its affiliates. All rights reserved.
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
This file contains the command to read a frm file. It requires a .frm filename,
and general options (verbosity, etc.).
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile
import uuid

from mysql.utilities.exception import UtilError
from mysql.utilities.command import serverclone
from mysql.utilities.command.serverclone import user_change_as_root
from mysql.utilities.common.frm_reader import FrmReader
from mysql.utilities.common.server import Server, stop_running_server
from mysql.utilities.common.tools import (requires_encoding, encode,
                                          requires_decoding, decode)


# The following are storage engines that cannot be read in default mode
_CANNOT_READ_ENGINE = ["PARTITION", "PERFORMANCE_SCHEMA"]
_SPAWN_SERVER_ERROR = ("Spawn server operation failed{0}. To diagnose, run "
                       "the utility again and use the --verbose option to "
                       "view the messages from the spawned server and correct "
                       "any errors presented then run the utility again.")


def _get_frm_path(dbtablename, datadir, new_db=None):
    """Form the path and discover the db and name of a frm file.

    dbtablename[in]    the database.table name in the format db:table
    datadir[in]        the path to the data directory
    new_db[in]         a new database name
                       default = None == use existing db

    Returns tuple - (db, name, path) or raises an error if .frm file
                    cannot be read
    """

    # Form the path to the .frm file. There are two possibilities:
    # a) the user has specified a full path
    # b) the user has specified a db:table combination (with/without .frm)

    path_parts = os.path.split(dbtablename)
    if ':' in dbtablename and len(path_parts[0]) == 0:
        # here we use the datadir to form the path
        path_parts = dbtablename.split(":")
        db = path_parts[0]
        table = path_parts[1]
        if datadir is None:
            datadir = ""
        frm_path = os.path.join(datadir, table)
    elif len(path_parts) == 2 and ":" in path_parts[1]:
        db, table = path_parts[1].split(":", 1)
        frm_path = os.path.join(path_parts[0], table)
    else:
        # here we decipher the last folder as the database name
        frm_path = dbtablename
        db = None
        if len(path_parts) == 2:
            path, table = path_parts
            if path == '':
                db = None
                path = None
        elif len(path_parts) == 1:
            db = None
            path = None
            table = dbtablename
        if db is None and path:
            # find database from path
            folders = path.split(os.path.sep)
            if len(folders):
                db = folders[len(folders) - 1]

    # Check that the frm_path name has .frm.
    if not frm_path.lower().endswith(".frm"):
        frm_path += ".frm"

    # Strip the .frm from table
    if table.lower().endswith('.frm'):
        table = os.path.splitext(table)[0]

    if not os.access(frm_path, os.R_OK):
        raise UtilError("Cannot read .frm file from %s." % frm_path)

    if new_db:
        db = new_db
    return (db, table, frm_path)


def _spawn_server(options):
    """Spawn a server to use for reading .frm files

    This method spawns a new server instance on the port specified by the
    user in the options dictionary.

    options[in]         Options from user

    Returns tuple - (Server instance, new datdir) or raises exception on error
    """
    verbosity = int(options.get("verbosity", 0))
    quiet = options.get("quiet", False)
    new_port = options.get("port", 3310)
    user = options.get("user", None)
    start_timeout = int(options.get("start_timeout", 10))

    # 1) create a directory to use for new datadir

    # If the user is not the same as the user running the script...
    if user_change_as_root(options):
        # Since Python libraries correctly restrict temporary folders to
        # the user who runs the script and /tmp is protected on some
        # platforms, we must create the folder in the current folder
        temp_datadir = os.path.join(os.getcwd(), str(uuid.uuid4()))
        os.mkdir(temp_datadir)
    else:
        temp_datadir = tempfile.mkdtemp()

    if verbosity > 1 and not quiet:
        print "# Creating a temporary datadir =", temp_datadir

    # 2) spawn a server pointed to temp
    if not quiet:
        if user:
            print("# Spawning server with --user={0}.".format(user))
        print "# Starting the spawned server on port %s ..." % new_port,
        sys.stdout.flush()

    bootstrap_options = {
        'new_data': temp_datadir,
        'new_port': new_port,
        'new_id': 101,
        'root_pass': "root",
        'mysqld_options': None,
        'verbosity': verbosity if verbosity > 1 else 0,
        'basedir': options.get("basedir"),
        'delete': True,
        'quiet': True if verbosity <= 1 else False,
        'user': user,
        'start_timeout': start_timeout,
    }
    if verbosity > 1 and not quiet:
        print

    try:
        serverclone.clone_server(None, bootstrap_options)
    except UtilError as error:
        if error.errmsg.startswith("Unable to communicate"):
            err = ". Clone server error: {0}".format(error.errmsg)
            proc_id = int(error.errmsg.split("=")[1].strip('.'))
            print("ERROR Attempting to stop failed spawned server. "
                  " Process id = {0}.".format(proc_id))
            if os.name == "posix":
                try:
                    os.kill(proc_id, subprocess.signal.SIGTERM)
                except OSError:
                    pass
            else:
                try:
                    subprocess.Popen("taskkill /F /T /PID %i" %
                                     proc_id, shell=True)
                except:
                    pass
            raise UtilError(_SPAWN_SERVER_ERROR.format(err))
        else:
            raise

    if verbosity > 1 and not quiet:
        print "# Connecting to spawned server"
    conn = {
        "user": "root",
        "passwd": "root",
        "host": "127.0.0.1",
        "port": options.get("port"),
    }
    server_options = {
        'conn_info': conn,
        'role': "frm_reader_bootstrap",
    }
    server = Server(server_options)
    try:
        server.connect()
    except UtilError:
        raise UtilError(_SPAWN_SERVER_ERROR.format(""))

    if not quiet:
        print "done."

    return (server, temp_datadir)


def _get_create_statement(server, temp_datadir,
                          frm_file, version,
                          options, quiet=False):
    """Get the CREATE statement for the .frm file

    This method attempts to read the CREATE statement by copying the .frm file,
    altering the storage engine in the .frm file to MEMORY and issuing a SHOW
    CREATE statement for the table/view.

    If this method returns None, the operation was successful and the CREATE
    statement was printed. If a string is returned, there was at least one
    error (which will be printed) and the .frm file was not readable.

    The returned frm file path can be used to tell the user to use the
    diagnostic mode for reading files byte-by-byte. See the method
    read_frm_files_diagnostic() above.

    server[in]          Server instance
    temp_datadir[in]    New data directory
    frm_file[in]        Tuple containing (db, table, path) for .frm file
    version[in]         Version string for the current server
    options[in]         Options from user

    Returns string - None on success, path to frm file on error
    """
    verbosity = int(options.get("verbosity", 0))
    quiet = options.get("quiet", False)
    new_engine = options.get("new_engine", None)
    frm_dir = options.get("frm_dir", ".{0}".format(os.sep))
    user = options.get('user', 'root')

    if not quiet:
        print "#\n# Reading the %s.frm file." % frm_file[1]
    try:
        # 1) copy the file
        db = frm_file[0]
        if not db or db == ".":
            db = "test"
        db_name = db + "_temp"
        new_path = os.path.normpath(os.path.join(temp_datadir, db_name))
        if not os.path.exists(new_path):
            os.mkdir(new_path)

        new_frm = os.path.join(new_path, frm_file[1] + ".frm")

        # Check name for decoding and decode
        try:
            if requires_decoding(frm_file[1]):
                new_frm_file = decode(frm_file[1])
                frm_file = (frm_file[0], new_frm_file, frm_file[2])
                shutil.copy(frm_file[2], new_path)
            # Check name for encoding and encode
            elif requires_encoding(frm_file[1]):
                new_frm_file = encode(frm_file[1]) + ".frm"
                new_frm = os.path.join(new_path, new_frm_file)
                shutil.copy(frm_file[2], new_frm)
            else:
                shutil.copy(frm_file[2], new_path)
        except:
            _, e, _ = sys.exc_info()
            print("ERROR: {0}".format(e))

        # Set permissons on copied file if user context in play
        if user_change_as_root(options):
            subprocess.call(['chown', '-R', user, new_path])
            subprocess.call(['chgrp', '-R', user, new_path])

        server.exec_query("CREATE DATABASE IF NOT EXISTS %s" % db_name)

        frm = FrmReader(db_name, frm_file[1], new_frm, options)
        frm_type = frm.get_type()

        server.exec_query("FLUSH TABLES")
        if frm_type == "TABLE":
            # 2) change engine if it is a table
            current_engine = frm.change_storage_engine()

            # Abort read if restricted engine found
            if current_engine[1].upper() in _CANNOT_READ_ENGINE:
                print ("ERROR: Cannot process tables with the %s storage "
                       "engine. Please use the diagnostic mode to read the "
                       "%s file." % (current_engine[1].upper(), frm_file[1]))
                return frm_file[2]

            # Check server version
            server_version = None
            if version and len(current_engine) > 1 and current_engine[2]:
                server_version = (int(current_engine[2][0]),
                                  int(current_engine[2][1:3]),
                                  int(current_engine[2][3:]))
                if verbosity > 1 and not quiet:
                    print ("# Server version in file: %s.%s.%s" %
                           server_version)
                if not server.check_version_compat(server_version[0],
                                                   server_version[1],
                                                   server_version[2]):
                    versions = (server_version[0], server_version[1],
                                server_version[2], version[0], version[1],
                                version[2])
                    print ("ERROR: The server version for this "
                           "file is too low. It requires a server version "
                           "%s.%s.%s or higher but your server is version "
                           "%s.%s.%s. Try using a newer server or use "
                           "diagnostic mode." % versions)
                    return frm_file[2]

            # 3) show CREATE TABLE
            res = server.exec_query("SHOW CREATE TABLE `%s`.`%s`" %
                                    (db_name, frm_file[1]))
            create_str = res[0][1]
            if new_engine:
                create_str = create_str.replace("ENGINE=MEMORY",
                                                "ENGINE=%s" % new_engine)
            elif current_engine[1].upper() != "MEMORY":
                create_str = create_str.replace("ENGINE=MEMORY",
                                                "ENGINE=%s" %
                                                current_engine[1])
            if frm_file[0] and frm_file[0] != ".":
                create_str = create_str.replace("CREATE TABLE ",
                                                "CREATE TABLE `%s`." %
                                                frm_file[0])

            # if requested, generate the new .frm with the altered engine
            if new_engine:
                server.exec_query("ALTER TABLE `{0}`.`{1}` "
                                  "ENGINE={2}".format(db_name,
                                                      frm_file[1],
                                                      new_engine))
                new_frm_file = os.path.join(frm_dir,
                                            "{0}.frm".format(frm_file[1]))
                if os.path.exists(new_frm_file):
                    print("#\n# WARNING: Unable to create new .frm file. "
                          "File exists.")
                else:
                    try:
                        shutil.copyfile(new_frm, new_frm_file)
                        print("# Copy of .frm file with new storage "
                              "engine saved as {0}.".format(new_frm_file))
                    except (IOError, OSError, shutil.Error) as e:
                        print("# WARNING: Unable to create new .frm file. "
                              "Error: {0}".format(e))

        elif frm_type == "VIEW":
            # 5) show CREATE VIEW
            res = server.exec_query("SHOW CREATE VIEW %s.%s" %
                                    (db_name, frm_file[1]))
            create_str = res[0][1]
            if frm_file[0]:
                create_str = create_str.replace("CREATE VIEW ",
                                                "CREATE VIEW `%s`." %
                                                frm_file[0])

        # Now we must replace the string for storage engine!
        print "#\n# CREATE statement for %s:\n#\n" % frm_file[2]
        print create_str
        print
        if frm_type == "TABLE" and options.get("show_stats", False):
            frm.show_statistics()

    except:
        print ("ERROR: Failed to correctly read the .frm file. Please try "
               "reading the file with the --diagnostic mode.")
        return frm_file[2]

    return None


def read_frm_files_diagnostic(frm_files, options):
    """Read a a list of frm files.

    This method reads a list of .frm files and displays the CREATE TABLE or
    CREATE VIEW statement for each. This method initiates a byte-by-byte
    read of the file.

    frm_files[in]      list of the database.table names in the format db:table
    options[in]        options for reading the .frm file
    """

    datadir = options.get("datadir", None)
    show_stats = options.get("show_stats", False)
    for frm_file in frm_files:
        db, table, frm_path = _get_frm_path(frm_file, datadir, None)

        frm = FrmReader(db, table, frm_path, options)
        frm.show_create_table_statement()
        if show_stats:
            frm.show_statistics()

    return True


def read_frm_files(file_names, options):
    """Read frm files using a spawned (bootstrapped) server.

    This method reads the list of frm files by spawning a server then
    copying the .frm files, changing the storage engine to memory,
    issuing a SHOW CREATE command, then resetting the storage engine and
    printing the resulting CREATE statement.

    file_names[in]      List of files to read
    options[in]         Options from user

    Returns list - list of .frm files that cannot be read.
    """
    test_port = options.get("port", None)
    test_basedir = options.get("basedir", None)
    test_server = options.get("server", None)

    if not test_port or (not test_basedir and not test_server):
        raise UtilError("Method requires basedir or server and port options.")

    verbosity = int(options.get("verbosity", 0))
    quiet = options.get("quiet", False)
    datadir = options.get("datadir", None)

    # 1) for each .frm, determine its type and db, table name
    if verbosity > 1 and not quiet:
        print "# Checking read access to .frm files "
    frm_files = []
    for file_name in file_names:
        db, table, frm_path = _get_frm_path(file_name, datadir)
        if not os.access(frm_path, os.R_OK):
            print "ERROR: Unable to read the file %s." % frm_path + \
                  "You must have read access to the .frm file."
        frm_files.append((db, table, frm_path))

    # 2) Spawn the server
    server, temp_datadir = _spawn_server(options)

    version_str = server.get_version()
    match = re.match(r'^(\d+\.\d+(\.\d+)*).*$', version_str.strip())
    if match:
        version = [int(x) for x in match.group(1).split('.')]
        version = (version + [0])[:3]  # Ensure a 3 elements list
    else:
        print ("# WARNING: Error parsing server version %s. Cannot compare "
               "version of .frm file." % version_str)
        version = None
    failed_reads = []
    if not quiet:
        print "# Reading .frm files"
    try:
        for frm_file in frm_files:
            # 3) For each .frm file, get the CREATE statement
            frm_err = _get_create_statement(server, temp_datadir,
                                            frm_file, version,
                                            options)
            if frm_err:
                failed_reads.append(frm_err)

    except UtilError as error:
        raise UtilError(error.errmsg)
    finally:
        # 4) shutdown the spawned server
        if verbosity > 1 and not quiet:
            print "# Shutting down spawned server"
            print "# Removing the temporary datadir"
        if user_change_as_root(options):
            try:
                os.unlink(temp_datadir)
            except OSError:
                pass  # ignore if we cannot delete

        stop_running_server(server)

    return failed_reads
