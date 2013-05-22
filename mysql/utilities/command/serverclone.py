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
This file contains the clone server utility which launches a new instance
of an existing server.
"""

import os
import re
import subprocess
import sys
import time
import shlex
import shutil

from mysql.utilities.common.tools import check_port_in_use

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
    """

    from mysql.utilities.common.server import Server
    from mysql.utilities.exception import UtilError
    from mysql.utilities.common.tools import get_tool_path

    new_data = os.path.abspath(options.get('new_data', None))
    new_port = options.get('new_port', '3307')
    root_pass = options.get('root_pass', None)
    verbosity = options.get('verbosity', 0)
    quiet = options.get('quiet', False)
    cmd_file = options.get('cmd_file', None)
    mysqld_options = options.get('mysqld_options', '')

    if not check_port_in_use('localhost', int(new_port)):
       raise UtilError("Port in use. Please choose an available port.")

    # Clone running server
    if conn_val is not None:
        # Try to connect to the MySQL database server.
        server1_options = {
            'conn_info' : conn_val,
            'role'      : "source",
        }
        server1 = Server(server1_options)
        server1.connect()

        if not quiet:
            print "# Cloning the MySQL server running on %s." % conn_val["host"]

        basedir = ""
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

    # If datadir exists, has data, and user said it was Ok, delete it
    if os.path.exists(new_data) and options.get("delete", False) and \
       os.listdir(new_data):
        shutil.rmtree(new_data, True)

    # Create new data directory if it does not exist
    if not os.path.exists(new_data):
        if not quiet:
            print "# Creating new data directory..."
        try:
            res = os.mkdir(new_data)
        except:
            raise UtilError("Unable to create directory '%s'" % new_data)


    if not quiet:
        print "# Configuring new instance..."
        print "# Locating mysql tools..."

    mysqld_path = get_tool_path(basedir, "mysqld")
    mysqladmin_path = get_tool_path(basedir, "mysqladmin")
    mysql_basedir = get_tool_path(basedir, "share/english/errgmsg.sys",
                                  False, False)
    mysql_basedir = basedir
    if os.path.exists(os.path.join(basedir, "local/mysql/share/")):
        mysql_basedir = os.path.join(mysql_basedir, "local/mysql/")
    # for source trees
    elif os.path.exists(os.path.join(basedir, "/sql/share/english/")):
        mysql_basedir = os.path.join(mysql_basedir, "/sql/")
    system_tables = get_tool_path(basedir, "mysql_system_tables.sql", False)
    system_tables_data = get_tool_path(basedir,
                                        "mysql_system_tables_data.sql", False)
    test_data_timezone = get_tool_path(basedir,
                                        "mysql_test_data_timezone.sql", False)
    help_data = get_tool_path(basedir, "fill_help_tables.sql", False)

    if verbosity >= 3 and not quiet:
        print "# Location of files:"
        locations = [
            ("mysqld", mysqld_path),
            ("mysqladmin", mysqladmin_path),
            ("mysql_system_tables.sql", system_tables),
            ("mysql_system_tables_data.sql", system_tables_data),
            ("mysql_test_data_timezone.sql", test_data_timezone),
            ("fill_help_tables.sql", help_data),
        ]
        if cmd_file is not None:
            locations.append(("write startup command to", cmd_file))

        for location in locations:
            print "# % 28s: %s" % location

    # Create the new mysql data with mysql_import_db-like process
    if not quiet:
        print "# Setting up empty database and mysql tables..."

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
        for line in lines:
            line = line.strip()
            # Don't fail when InnoDB is turned off (Bug#16369955) (Ugly hack)
            if (sqlfile == system_tables and
                "SET @sql_mode_orig==@@SES" in line and innodb_disabled):
                for line in lines:
                    if 'SET SESSION sql_mode=@@sql' in line:
                        break
            sql.append(line)

    # Bootstap to setup mysql tables
    fnull = open(os.devnull, 'w')
    cmd = [
        mysqld_path,
        "--no-defaults",
        "--bootstrap",
        "--datadir={0}".format(new_data),
        "--basedir={0}".format(os.path.abspath(mysql_basedir)),
        ]
    proc = None
    if verbosity >= 1 and not quiet:
        proc = subprocess.Popen(cmd, shell=False, stdin=subprocess.PIPE)
    else:
        proc = subprocess.Popen(cmd, shell=False, stdin=subprocess.PIPE,
                                stdout=fnull, stderr=fnull)
    proc.communicate('\n'.join(sql))

    # Wait for subprocess to finish
    res = proc.wait()

    # Kill subprocess just in case it didn't finish - Ok if proc doesn't exist
    if int(res) != 0:
        if os.name == "posix":
            try:
                os.kill(proc.pid, subprocess.signal.SIGTERM)
            except OSError:
                pass
        else:
            try:
                retval = subprocess.Popen("taskkill /F /T /PID %i" % proc.pid,
                                          shell=True)
            except:
                pass

    # Drop the bootstrap file
    if os.path.isfile("bootstrap.sql"):
        os.unlink("bootstrap.sql")

    # Start the instance
    if not quiet:
        print "# Starting new instance of the server..."

    cmd = [mysqld_path, '--no-defaults']
    cmd.extend([
        '--datadir={0}'.format(new_data),
        '--tmpdir={0}'.format(new_data),
        '--pid-file={0}'.format(os.path.join(new_data, "clone.pid")),
        '--port={0}'.format(new_port),
        '--server-id={0}'.format(options.get('new_id', 2)),
        '--basedir={0}'.format(mysql_basedir),
        '--socket={0}'.format(os.path.join(new_data, 'mysql.sock')),
        ])

    if mysqld_options:
        if isinstance(mysqld_options, (list, tuple)):
            cmd.extend(mysqld_options)
        else:
            new_opts = mysqld_options.strip(" ")
            # Drop the --mysqld=
            if new_opts.startswith("--mysqld="):
                new_opts = new_opts[9:]
            if new_opts.startswith('"') and new_opts.endswith('"'):
                cmd.extend(shlex.split(new_opts.strip('"')))
            elif new_opts.startswith("'")  and new_opts.endswith("'"):
                cmd.extend(shlex.split(new_opts.strip("'")))
            # Special case where there is only 1 option
            elif len(new_opts.split("--")) == 1:
                cmd.append(mysqld_options)
            else:
                cmd.extend(shlex.split(new_opts))
        cmd.append('--user=root')

    # Strip spaces from each option
    cmd = [opt.strip(' ') for opt in cmd]

    # Write startup command if specified
    if cmd_file is not None:
        if verbosity >= 0 and not quiet:
            print "# Writing startup command to file."
        cfile = open(cmd_file, 'w')
        if os.name == 'posix' and cmd_file.endswith('.sh'):
            cfile.write("#!/bin/sh\n")
        cfile.write("# Startup command generated by mysqlserverclone.\n")
        cfile.write("%s\n" % cmd)
        cfile.close()

    if verbosity >= 1 and not quiet:
        if verbosity >= 2:
            print("# Startup command for new server:\n"
                  "{0}".format(" ".join(cmd)))
        proc = subprocess.Popen(cmd, shell=False)
    else:
        proc = subprocess.Popen(cmd, shell=False, stdout=fnull, stderr=fnull)

    # Try to connect to the new MySQL instance
    if not quiet:
        print "# Testing connection to new instance..."
    new_sock = None
    port_int = None
    if os.name == "posix":
        new_sock = os.path.join(new_data, "mysql.sock")
    port_int = int(new_port)

    conn = {
        "user"   : "root",
        "passwd" : "",
        "host"   : conn_val["host"] if conn_val is not None else "localhost",
        "port"   : port_int,
        "unix_socket" : new_sock
    }
    server2_options = {
        'conn_info' : conn,
        'role'      : "clone",
    }
    server2 = Server(server2_options)

    stop = 10 # stop after 10 attempts
    i = 0
    while i < stop:
        i += 1
        time.sleep(1)
        try:
            server2.connect()
            i = stop + 1
        except:
            pass
        finally:
            if verbosity >= 1 and not quiet:
                print "# trying again..."

    if i == stop:
        raise UtilError("Unable to communicate with new instance.")
    elif not quiet:
        print "# Success!"

    # Set the root password
    if root_pass:
        if not quiet:
            print "# Setting the root password..."
        cmd = [mysqladmin_path, '--no-defaults', '-v', '-uroot']
        if os.name == "posix":
            cmd.append("--socket={0}".format(new_sock))
        else:
            cmd.append("--port={0}".format(int(new_port)))
        cmd.extend(["password", root_pass])
        if verbosity > 0 and not quiet:
            proc = subprocess.Popen(cmd, shell=False)
        else:
            proc = subprocess.Popen(cmd, shell=False,
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
