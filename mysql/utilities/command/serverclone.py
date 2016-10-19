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
This file contains the clone server utility which launches a new instance
of an existing server.
"""

import getpass
import os
import subprocess
import tempfile
import time
import shlex
import shutil

from mysql.utilities.common.tools import (check_port_in_use,
                                          estimate_free_space,
                                          get_mysqld_version,
                                          get_tool_path)
from mysql.utilities.common.messages import WARN_OPT_SKIP_INNODB
from mysql.utilities.common.server import Server
from mysql.utilities.exception import UtilError

MAX_DATADIR_SIZE = 200
MAX_SOCKET_PATH_SIZE = 107
# Required free disk space in MB to create the data directory.
REQ_FREE_SPACE = 120
LOW_SPACE_ERRR_MSG = ("The new data directory {directory} has low free space"
                      "remaining, please free some space and try again. \n"
                      "mysqlserverclone needs at least {megabytes} MB to run "
                      "the new server instance.\nUse force option to ignore "
                      "this Error.")

# Set of sql statements to use during server bootstrap to create the
# root@localhost user account for MySQL versions equal or greater than 5.7.5
_CREATE_ROOT_USER = [
    "CREATE TEMPORARY TABLE tmp_user LIKE user;\n",
    ("REPLACE INTO tmp_user (Host, User, Password, Select_priv, Insert_priv, "
     "Update_priv, Delete_priv, Create_priv, Drop_priv, Reload_priv, "
     "Shutdown_priv, Process_priv, File_priv, Grant_priv, References_priv, "
     "Index_priv, Alter_priv, Show_db_priv, Super_priv, "
     "Create_tmp_table_priv, Lock_tables_priv, Execute_priv, Repl_slave_priv, "
     "Repl_client_priv, Create_view_priv, Show_view_priv, "
     "Create_routine_priv, Alter_routine_priv, Create_user_priv, Event_priv, "
     "Trigger_priv, Create_tablespace_priv, ssl_cipher, x509_issuer, "
     "x509_subject) VALUES ('localhost', 'root', '', 'Y', 'Y', 'Y', 'Y', 'Y', "
     "'Y', 'Y', 'Y', 'Y', 'Y', 'Y', 'Y', 'Y', 'Y', 'Y', 'Y', 'Y', 'Y', 'Y', "
     "'Y', 'Y', 'Y', 'Y', 'Y', 'Y', 'Y', 'Y', 'Y', 'Y', '','', '');\n"),
    "REPLACE INTO user SELECT * FROM tmp_user WHERE @had_user_table=0;\n"
    "DROP TABLE tmp_user;\n"]


def clone_server(conn_val, options):
    """Clone an existing server

    This method creates a new instance of a running server using a datadir
    set to the new_data parametr, with a port set to new_port, server_id
    set to new_id and a root password of root_pass. You can also specify
    additional parameters for the mysqld command line as well as turn on
    verbosity mode to display more diagnostic information during the clone
    process.

    The method will build a new base database installation from the .sql
    files used to construct a new installation. Once the database is
    created, the server will be started.

    dest_val[in]        a dictionary containing connection information
                        including:
                        (user, password, host, port, socket)
    options[in]         dictionary of options:
      new_data[in]        An existing path to create the new database and use
                          as datadir for new instance
                          (default = None)
      new_port[in]        Port number for new instance
                          (default = 3307)
      new_id[in]          Server_id for new instance
                          (default = 2)
      root_pass[in]       Password for root user on new instance (optional)
      mysqld_options[in]  Additional command line options for mysqld
      verbosity[in]       Print additional information during operation
                          (default is 0)
      quiet[in]           If True, do not print messages.
                          (default is False)
      cmd_file[in]        file name to write startup command
      start_timeout[in]   Number of seconds to wait for server to start
    """
    new_data = os.path.abspath(options.get('new_data', None))
    new_port = options.get('new_port', '3307')
    root_pass = options.get('root_pass', None)
    verbosity = options.get('verbosity', 0)
    user = options.get('user', 'root')
    quiet = options.get('quiet', False)
    cmd_file = options.get('cmd_file', None)
    start_timeout = int(options.get('start_timeout', 10))
    mysqld_options = options.get('mysqld_options', '')
    force = options.get('force', False)
    quote_char = "'" if os.name == "posix" else '"'

    if not check_port_in_use('localhost', int(new_port)):
        raise UtilError("Port {0} in use. Please choose an "
                        "available port.".format(new_port))

    # Check if path to database files is greater than MAX_DIR_SIZE char,
    if len(new_data) > MAX_DATADIR_SIZE and not force:
        raise UtilError("The --new-data path '{0}' is too long "
                        "(> {1} characters). Please use a smaller one. "
                        "You can use the --force option to skip this "
                        "check".format(new_data, MAX_DATADIR_SIZE))

    # Clone running server
    if conn_val is not None:
        # Try to connect to the MySQL database server.
        server1_options = {
            'conn_info': conn_val,
            'role': "source",
        }
        server1 = Server(server1_options)
        server1.connect()
        if not quiet:
            print "# Cloning the MySQL server running on %s." % \
                conn_val["host"]

        # Get basedir
        rows = server1.exec_query("SHOW VARIABLES LIKE 'basedir'")
        if not rows:
            raise UtilError("Unable to determine basedir of running server.")
        basedir = os.path.normpath(rows[0][1])

    # Cloning downed or offline server
    else:
        basedir = os.path.abspath(options.get("basedir", None))
        if not quiet:
            print "# Cloning the MySQL server located at %s." % basedir

    new_data_deleted = False
    # If datadir exists, has data, and user said it was Ok, delete it
    if os.path.exists(new_data) and options.get("delete", False) and \
       os.listdir(new_data):
        new_data_deleted = True
        shutil.rmtree(new_data, True)

    # Create new data directory if it does not exist
    if not os.path.exists(new_data):
        if not quiet:
            print "# Creating new data directory..."
        try:
            os.mkdir(new_data)
        except OSError as err:
            raise UtilError("Unable to create directory '{0}', reason: {1}"
                            "".format(new_data, err.strerror))

    # After create the new data directory, check for free space, so the errors
    # regarding invalid or inaccessible path had been dismissed already.
    # If not force specified verify and stop if there is not enough free space
    if not force and os.path.exists(new_data) and \
       estimate_free_space(new_data) < REQ_FREE_SPACE:
        # Don't leave empty folders, delete new_data if was previously deleted
        if os.path.exists(new_data) and new_data_deleted:
            shutil.rmtree(new_data, True)
        raise UtilError(LOW_SPACE_ERRR_MSG.format(directory=new_data,
                                                  megabytes=REQ_FREE_SPACE))

    # Check for warning of using --skip-innodb
    mysqld_path = get_tool_path(basedir, "mysqld")
    version_str = get_mysqld_version(mysqld_path)
    # convert version_str from str tuple to integer tuple if possible
    if version_str is not None:
        version = tuple([int(digit) for digit in version_str])
    else:
        version = None
    if mysqld_options is not None and (
            "--skip-innodb" in mysqld_options or
            "--innodb" in mysqld_options) and version is not None and \
            version >= (5, 7, 5):
        print("# WARNING: {0}".format(WARN_OPT_SKIP_INNODB))

    if not quiet:
        print "# Configuring new instance..."
        print "# Locating mysql tools..."

    mysqladmin_path = get_tool_path(basedir, "mysqladmin")

    mysql_basedir = basedir
    if os.path.exists(os.path.join(basedir, "local/mysql/share/")):
        mysql_basedir = os.path.join(mysql_basedir, "local/mysql/")
    # for source trees
    elif os.path.exists(os.path.join(basedir, "/sql/share/english/")):
        mysql_basedir = os.path.join(mysql_basedir, "/sql/")

    locations = [
        ("mysqld", mysqld_path),
        ("mysqladmin", mysqladmin_path),
    ]

    # From 5.7.6 version onwards, bootstrap is done via mysqld with the
    # --initialize-insecure option, so no need to get information about the
    # sql system tables that need to be loaded.
    if version < (5, 7, 6):
        system_tables = get_tool_path(basedir, "mysql_system_tables.sql",
                                      False)
        system_tables_data = get_tool_path(basedir,
                                           "mysql_system_tables_data.sql",
                                           False)
        test_data_timezone = get_tool_path(basedir,
                                           "mysql_test_data_timezone.sql",
                                           False)
        help_data = get_tool_path(basedir, "fill_help_tables.sql", False)
        locations.extend([("mysql_system_tables.sql", system_tables),
                          ("mysql_system_tables_data.sql", system_tables_data),
                          ("mysql_test_data_timezone.sql", test_data_timezone),
                          ("fill_help_tables.sql", help_data), ])

    if verbosity >= 3 and not quiet:
        print "# Location of files:"
        if cmd_file is not None:
            locations.append(("write startup command to", cmd_file))

        for location in locations:
            print "# % 28s: %s" % location

    # Create the new mysql data with mysql_import_db-like process
    if not quiet:
        print "# Setting up empty database and mysql tables..."

    fnull = open(os.devnull, 'w')

    # For MySQL versions before 5.7.6, use regular bootstrap procedure.
    # pylint: disable=R0101
    if version < (5, 7, 6):
        # Get bootstrap SQL statements
        sql = list()
        sql.append("CREATE DATABASE mysql;")
        sql.append("USE mysql;")
        innodb_disabled = False
        if mysqld_options:
            innodb_disabled = '--innodb=OFF' in mysqld_options
        for sqlfile in [system_tables, system_tables_data, test_data_timezone,
                        help_data]:
            lines = open(sqlfile, 'r').readlines()
            # On MySQL 5.7.5, the root@localhost account creation was
            # moved from the system_tables_data sql file into the
            # mysql_install_db binary. Since we don't use mysql_install_db
            # directly we need to create the root user account ourselves.
            if (version is not None and version == (5, 7, 5) and
                    sqlfile == system_tables_data):
                lines.extend(_CREATE_ROOT_USER)
            for line in lines:
                line = line.strip()
                # Don't fail when InnoDB is turned off (Bug#16369955)
                # (Ugly hack)
                if (sqlfile == system_tables and
                        "SET @sql_mode_orig==@@SES" in line and
                        innodb_disabled):
                    for line in lines:
                        if 'SET SESSION sql_mode=@@sql' in line:
                            break
                sql.append(line)

        # Bootstap to setup mysql tables
        cmd_opts = [
            mysqld_path,
            "--no-defaults",
            "--bootstrap",
            "--datadir={0}".format(new_data),
            "--basedir={0}".format(os.path.abspath(mysql_basedir)),
        ]

        if verbosity >= 1 and not quiet:
            proc = subprocess.Popen(cmd_opts, shell=False,
                                    stdin=subprocess.PIPE)
        else:
            proc = subprocess.Popen(cmd_opts, shell=False,
                                    stdin=subprocess.PIPE,
                                    stdout=fnull, stderr=fnull)
        proc.communicate('\n'.join(sql))

    # From 5.7.6 onwards, mysql_install_db has been replaced by mysqld and
    # the --initialize option
    else:
        cmd_opts = [
            mysqld_path,
            "--no-defaults",
            "--initialize-insecure=on",
            "--datadir={0}".format(new_data),
            "--basedir={0}".format(os.path.abspath(mysql_basedir))
        ]
        if verbosity >= 1 and not quiet:
            proc = subprocess.Popen(cmd_opts, shell=False,
                                    stdin=subprocess.PIPE)
        else:
            proc = subprocess.Popen(cmd_opts, shell=False,
                                    stdin=subprocess.PIPE,
                                    stdout=fnull, stderr=fnull)
    # Wait for subprocess to finish
    res = proc.wait()
    # Kill subprocess just in case it didn't finish - Ok if proc doesn't exist
    if int(res) != 0:
        if os.name == "posix":
            try:
                os.kill(proc.pid, subprocess.signal.SIGTERM)
            except OSError as error:
                if not str(error.strerror).startswith("No such process"):
                    raise UtilError("Failed to complete initialization of "
                                    "clone. Pid = '{0}'".format(proc.pid))
        else:
            ret_code = subprocess.call("taskkill /F /T /PID "
                                       "{0}".format(proc.pid), shell=True)

            # return code 0 means it was successful and 128 means it tried
            # to kill a process that doesn't exist
            if ret_code not in (0, 128):
                raise UtilError("Failed to complete initialization of clone."
                                " Pid = {0}. Return code {1}"
                                "".format(proc.pid, ret_code))

    # Drop the bootstrap file
    if os.path.isfile("bootstrap.sql"):
        os.unlink("bootstrap.sql")

    # Start the instance
    if not quiet:
        print "# Starting new instance of the server..."

    # If the user is not the same as the user running the script...
    # and this is a Posix system... and we are running as root
    if user_change_as_root(options):
        subprocess.call(['chown', '-R', user, new_data])
        subprocess.call(['chgrp', '-R', user, new_data])

    socket_path = os.path.join(new_data, 'mysql.sock')
    # If socket path is too long, use mkdtemp to create a tmp dir and
    # use it instead to store the socket
    if os.name == 'posix' and len(socket_path) > MAX_SOCKET_PATH_SIZE:
        socket_path = os.path.join(tempfile.mkdtemp(), 'mysql.sock')
        if not quiet:
            print("# WARNING: The socket file path '{0}' is too long (>{1}), "
                  "using '{2}' instead".format(
                      os.path.join(new_data, 'mysql.sock'),
                      MAX_SOCKET_PATH_SIZE, socket_path))

    cmd = {
        'datadir': '--datadir={0}'.format(new_data),
        'tmpdir': '--tmpdir={0}'.format(new_data),
        'pid-file': '--pid-file={0}'.format(
            os.path.join(new_data, "clone.pid")),
        'port': '--port={0}'.format(new_port),
        'server': '--server-id={0}'.format(options.get('new_id', 2)),
        'basedir': '--basedir={0}'.format(mysql_basedir),
        'socket': '--socket={0}'.format(socket_path),
    }
    if user:
        cmd.update({'user': '--user={0}'.format(user)})
    if mysqld_options:
        if isinstance(mysqld_options, (list, tuple)):
            cmd.update(dict(zip(mysqld_options, mysqld_options)))
        else:
            new_opts = mysqld_options.strip(" ")
            # Drop the --mysqld=
            if new_opts.startswith("--mysqld="):
                new_opts = new_opts[9:]
            if new_opts.startswith('"') and new_opts.endswith('"'):
                list_ = shlex.split(new_opts.strip('"'))
                cmd.update(dict(zip(list_, list_)))
            elif new_opts.startswith("'") and new_opts.endswith("'"):
                list_ = shlex.split(new_opts.strip("'"))
                cmd.update(dict(zip(list_, list_)))
            # Special case where there is only 1 option
            elif len(new_opts.split("--")) == 1:
                cmd.update({mysqld_options: mysqld_options})
            else:
                list_ = shlex.split(new_opts)
                cmd.update(dict(zip(list_, list_)))

    # set of options that must be surrounded with quotes
    options_to_quote = set(["datadir", "tmpdir", "basedir", "socket",
                            "pid-file"])

    # Strip spaces from each option
    for key in cmd:
        cmd[key] = cmd[key].strip(' ')

    # Write startup command if specified
    if cmd_file is not None:
        if verbosity >= 0 and not quiet:
            print "# Writing startup command to file."
        cfile = open(cmd_file, 'w')
        comment = " Startup command generated by mysqlserverclone.\n"
        if os.name == 'posix' and cmd_file.endswith('.sh'):
            cfile.write("#!/bin/sh\n")
            cfile.write("#{0}".format(comment))
        elif os.name == 'nt' and cmd_file.endswith('.bat'):
            cfile.write("REM{0}".format(comment))
        else:
            cfile.write("#{0}".format(comment))

        start_cmd_lst = ["{0}{1}{0} --no-defaults".format(quote_char,
                                                          mysqld_path)]

        # build start command
        for key, val in cmd.iteritems():
            if key in options_to_quote:
                val = "{0}{1}{0}".format(quote_char, val)
            start_cmd_lst.append(val)
        cfile.write("{0}\n".format(" ".join(start_cmd_lst)))
        cfile.close()

    if os.name == "nt" and verbosity >= 1:
        cmd.update({"console": "--console"})

    start_cmd_lst = [mysqld_path, "--no-defaults"]
    sorted_keys = sorted(cmd.keys())
    start_cmd_lst.extend([cmd[val] for val in sorted_keys])
    if verbosity >= 1 and not quiet:
        if verbosity >= 2:
            print("# Startup command for new server:\n"
                  "{0}".format(" ".join(start_cmd_lst)))
        proc = subprocess.Popen(start_cmd_lst, shell=False)
    else:
        proc = subprocess.Popen(start_cmd_lst, shell=False, stdout=fnull,
                                stderr=fnull)

    # Try to connect to the new MySQL instance
    if not quiet:
        print "# Testing connection to new instance..."
    new_sock = None

    if os.name == "posix":
        new_sock = socket_path
    port_int = int(new_port)

    conn = {
        "user": "root",
        "passwd": "",
        "host": conn_val["host"] if conn_val is not None else "localhost",
        "port": port_int,
        "unix_socket": new_sock
    }

    server2_options = {
        'conn_info': conn,
        'role': "clone",
    }
    server2 = Server(server2_options)

    i = 0
    while i < start_timeout:
        i += 1
        time.sleep(1)
        try:
            server2.connect()
            i = start_timeout + 1
        except:
            pass
        finally:
            if verbosity >= 1 and not quiet:
                print "# trying again..."

    if i == start_timeout:
        raise UtilError("Unable to communicate with new instance. "
                        "Process id = {0}.".format(proc.pid))
    elif not quiet:
        print "# Success!"

    # Set the root password
    if root_pass:
        if not quiet:
            print "# Setting the root password..."
        cmd_opts = [mysqladmin_path, '--no-defaults', '-v', '-uroot']
        if os.name == "posix":
            cmd_opts.append("--socket={0}".format(new_sock))
        else:
            cmd_opts.append("--port={0}".format(int(new_port)))
        cmd_opts.extend(["password", root_pass])
        if verbosity > 0 and not quiet:
            proc = subprocess.Popen(cmd_opts, shell=False)
        else:
            proc = subprocess.Popen(cmd_opts, shell=False,
                                    stdout=fnull, stderr=fnull)

        # Wait for subprocess to finish
        res = proc.wait()

    if not quiet:
        conn_str = "# Connection Information:\n"
        conn_str += "#  -uroot"
        if root_pass:
            conn_str += " -p%s" % root_pass
        if os.name == "posix":
            conn_str += " --socket=%s" % new_sock
        else:
            conn_str += " --port=%s" % new_port
        print conn_str
        print "#...done."

    fnull.close()


def user_change_as_root(options):
    """ Detect if the user context must change for spawning server as root

    This method checks to see if the current user executing the utility is
    root and there is a different user being requested. If the user being
    requested is None or is root and we are running as root or the user
    being requested is the same as the current user, the method returns False.

    Note: This method only works for POSIX systems. It returns False for
          non-POSIX systems.

    options[in]         Option dictionary

    Returns bool - user context must occur
    """
    user = options.get('user', 'root')
    if not user or os.name != 'posix':
        return False
    return getpass.getuser() != user and getpass.getuser() == 'root'
