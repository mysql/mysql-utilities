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
This file contains the clone server utility which launches a new instance
of an existing server.
"""

import os
import subprocess
import sys
import time
import shutil

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
    
    new_data = options.get('new_data', None)
    new_port = options.get('new_port', '3307')
    root_pass = options.get('root_pass', None)
    verbosity = options.get('verbosity', 0)
    quiet = options.get('quiet', False)
    cmd_file = options.get('cmd_file', None)

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
        basedir = rows[0][1]

    # Cloning downed or offline server
    else:
        basedir = options.get("basedir", None)
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

    # Create the bootstrap file
    f_boot = open("bootstrap.sql", 'w')
    f_boot.write("CREATE DATABASE mysql;\n")
    f_boot.write("USE mysql;\n")
    f_boot.writelines(open(system_tables).readlines())
    f_boot.writelines(open(system_tables_data).readlines())
    f_boot.writelines(open(test_data_timezone).readlines())
    f_boot.writelines(open(help_data).readlines())
    f_boot.close()

    # Bootstap to setup mysql tables
    fnull = open(os.devnull, 'w')
    cmd = mysqld_path + " --no-defaults --bootstrap " + \
            " --datadir=%s --basedir=%s " % (new_data, mysql_basedir) + \
            " < bootstrap.sql"
    proc = None
    if verbosity >= 1 and not quiet:
        proc = subprocess.Popen(cmd, shell=True)
    else:
        proc = subprocess.Popen(cmd, shell=True, stdout=fnull, stderr=fnull)

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
    cmd = mysqld_path + " --no-defaults "
    if options.get('mysqld_options', None):
        cmd += options.get('mysqld_options') + " --user=root "
    cmd += "--datadir=%s " % (new_data)
    cmd += "--tmpdir=%s " % (new_data)
    cmd += "--pid-file=%s " % os.path.join(new_data, "clone.pid")
    cmd += "--port=%s " % (new_port)
    cmd += "--server-id=%s " % (options.get('new_id', 2))
    cmd += "--basedir=%s " % (mysql_basedir)
    cmd += "--socket=%s/mysql.sock " % (new_data)

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
            print "# Startup command for new server:\n%s" % cmd
        proc = subprocess.Popen(cmd, shell=True)
    else:
        proc = subprocess.Popen(cmd, shell=True, stdout=fnull, stderr=fnull)

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
        if os.name == "posix":
            cmd = mysqladmin_path + " --no-defaults -v -uroot " + \
                  "--socket=%s password %s " % (new_sock, root_pass)
        else:
            cmd = mysqladmin_path + " --no-defaults -v -uroot " + \
                  "password %s --port=%s" % (root_pass, int(new_port))
        if verbosity > 0 and not quiet:
            proc = subprocess.Popen(cmd, shell=True)
        else:
            proc = subprocess.Popen(cmd, shell=True,
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
