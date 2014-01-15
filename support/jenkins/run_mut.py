# Copyright (c) 2013, 2014, Oracle and/or its affiliates. All rights reserved.
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

from __future__ import print_function, absolute_import
import os
import sys
import glob
import shutil
from collections import namedtuple

from support.jenkins.common import (
    MUTOutputParser, get_server_info, working_path, copy_connector,
    extract_file, get_major_version, pprint_mysql_version, mysql_server,
    load_databases, run_mut, execute, SPECIFIC_TESTS, get_mut_test_list)


if os.name == 'nt':
    from support.jenkins.commands import COMMANDS_WINDOWS as COMMANDS
else:
    from support.jenkins.commands import COMMANDS_LINUX as COMMANDS

if __name__ == '__main__':
    WORKSPACE = os.environ["WORKSPACE"]
    UTILS_HOME = os.path.realpath(os.environ["UTILS_HOME"])
    CONNECTOR_HOME = os.environ["CONNECTOR_HOME"]
    BINARIES_HOME = os.environ["BINARIES_HOME"]
    SERVERS_DIR = os.path.join(WORKSPACE, "SERVERS")
    RUN_COVERAGE = (True if os.environ["RUN_COVERAGE"].lower() == "true"
                    else False)
    FORCE = (True if os.environ["FORCE"].lower() == "true"
             else False)
    LOAD_DATABASES = (True if os.environ["LOAD_DATABASES"].lower() ==
                      "true" else False)
    VERBOSE = (True if os.environ["VERBOSE"].lower() == "true"
               else False)
    BASE_SERVER_ID = os.environ["BASE_SERVER_ID"]
    BUILD_NUMBER = os.environ["BUILD_NUMBER"]
    DB_FILES_HOME = os.environ["DB_FILES_HOME"]
    MUT_HOME = os.path.join(WORKSPACE, "mysql-test")
    OVERRIDE_MUT_CMD = os.environ.get("OVERRIDE MUT RUN_CMD", None)
    MYSQL_VERSION = os.environ["MYSQL_VERSION"]

    print("\n==================== *SETUP* ====================\n")
    print("WORKSPACE: {0}".format(WORKSPACE))
    print("MUT_HOME: {0}".format(MUT_HOME))
    print("MySQL Binaries: {0}".format(BINARIES_HOME))
    print("RUN COVERAGE: {0}".format(RUN_COVERAGE))
    print("FORCE MUT: {0}".format(FORCE))
    print("VERBOSE MODE: {0}".format(VERBOSE))
    print("UTILS_HOME: {0}".format(UTILS_HOME))
    print("DATABASE FILES HOME: {0}".format(DB_FILES_HOME))
    print("LOAD DATABASES: {0}".format(LOAD_DATABASES))
    print("OVERRIDE MUT CMD: {0}".format(OVERRIDE_MUT_CMD))

    BUILD_RESULTS = os.path.join(WORKSPACE, "BUILD_RESULTS")
    # Get list of tests and create the parser
    if MYSQL_VERSION == "ALL":
        output_parser = MUTOutputParser(get_mut_test_list(WORKSPACE))
    else:
        output_parser = MUTOutputParser()

    #Copy Connector
    with working_path(WORKSPACE):
        copy_connector(CONNECTOR_HOME)
    print("# Adding utilities folder to the PYTHONPATH")
    # add utilities to the pythonpath
    if 'PYTHONPATH' in os.environ:
        os.environ['PYTHONPATH'] = "{0};{1}".format(WORKSPACE,
                                                    os.environ['PYTHONPATH'])
    else:
        os.environ['PYTHONPATH'] = WORKSPACE

    dbs_to_load = []
    if LOAD_DATABASES:
        print("# Bulding list of databases to load into servers")
        # Employee db only needs to be loaded for check_index_best_worst_large
        if (OVERRIDE_MUT_CMD is None or "check_index_best_worst_large" in
                OVERRIDE_MUT_CMD or "--do-tests=check" in OVERRIDE_MUT_CMD
                or "--suite=main" in OVERRIDE_MUT_CMD):
            emp_db_path = os.path.join(DB_FILES_HOME, 'employees_db',
                                       'employees.sql')
            if os.path.exists(emp_db_path):
                dbs_to_load.append(emp_db_path)
            else:
                print("# WARNING: Could not find employees db in "
                      "'{0}".format(emp_db_path))
        # World db only needs to be loaded for compare_db_large teste
        if (OVERRIDE_MUT_CMD is None or "compare_db_large" in OVERRIDE_MUT_CMD
                or "--do-tests=compare" in OVERRIDE_MUT_CMD
                or "--suite=main" in OVERRIDE_MUT_CMD):
            world_db_path = os.path.join(DB_FILES_HOME, 'world_innodb.sql')
            if os.path.exists(world_db_path):
                dbs_to_load.append(world_db_path)
            else:
                print("# WARNING: Could not find world_innodb db in "
                      "'{0}'".format(world_db_path))

    print("\n==================== *EXTRACTING SERVERS* ====================\n")
    # Create namedTuple to store server information
    serverTuple = namedtuple('ServerTuple', 'fullname shortname version '
                                            'is_commercial')
    server_list = []
    exit_status = 0
    archive_wildcard = "*.zip" if os.name == 'nt' else "*.tar.gz"
    for server in glob.glob(os.path.join(BINARIES_HOME, archive_wildcard)):
        server_info = get_server_info(server)
        if server_info is not None:
            ((is_commercial, mysql_version), shortname) = server_info
            # Extract only if it is the correct version
            if mysql_version == MYSQL_VERSION or MYSQL_VERSION == 'ALL':
                fname = extract_file(server, path=SERVERS_DIR, replace=True)
                if fname is not None:
                    server_list.append(serverTuple(fname, shortname,
                                                   mysql_version,
                                                   is_commercial))

    print("\n==================== *RUNNING TESTS* ====================\n")
    # If coverage flag is set, change sitecustomize.py file to enable
    # coverage report between subprocesses
    if RUN_COVERAGE:
        os.environ['COVERAGE_PROCESS_START'] = os.path.join(UTILS_HOME,
                                                            'coveragerc')
        with working_path(WORKSPACE):
            with open('sitecustomize.py', 'a') as f:
                f.write('import coverage; coverage.process_startup()')

    if len(server_list) == 0:
        print("# ERROR: Couldn't find suitable servers")
        sys.exit(1)

    # For each server version
    for i, server in enumerate(server_list):
        base_dir = os.path.join(SERVERS_DIR, server.fullname)
        if os.path.isdir(base_dir):
            print("# Entering server folder: '%s'" % base_dir)
            # try to find specific version command list,
            # else fall back to major version command list
            cmd_lst = COMMANDS.get(server.version,
                                   COMMANDS[get_major_version(
                                       server.version)])

            # For each cmd tuple for the specified server version
            for j, cmd_tpl in enumerate(cmd_lst):
                # calculate server port and server_id
                server_id = str(int(BASE_SERVER_ID) + i*100+j)

                # Create dictionary with all the required parameters to
                # successfully launch a mysql server
                param_dict = {'base_dir': base_dir,
                              'server_id': server_id,
                              'results_dir': BUILD_RESULTS,
                              'shortname': server.shortname,
                              }

                # Create MySQL version message
                version_msg = ("Running MySQL {0} using the '{1}' "
                               "command".format(server.version, cmd_tpl[0]))

                # Pretty print the MySQL version
                pprint_mysql_version(version_msg)

                # set the executable part the run command according to the OS
                if os.name == 'nt':
                    cmd_exec = r'.\mysql-test-run.pl'
                else:
                    cmd_exec = './mysql-test-run.pl'

                # Fill the dynamic fields in the arguments of the command to
                # start the server
                cmd_args = cmd_tpl[1].format(**param_dict)

                # Piece together the entire run command
                run_cmd = "{0} {1}".format(cmd_exec, cmd_args)

                # Load audit-log plugin for commercial servers
                if(get_major_version(server.version) in ['5.5', '5.6']
                        and server.is_commercial):
                    if os.name == 'nt':
                        run_cmd = ("{0} --mysqld=--plugin_load="
                                   "audit_log.dll".format(run_cmd))
                    else:
                        run_cmd = ("{0} --mysqld=--plugin_load="
                                   "audit_log.so".format(run_cmd))

                with mysql_server(run_cmd, param_dict) as (server_up, port):
                    if server_up:
                        # get specific tests for version, if any
                        specific_t = SPECIFIC_TESTS.get(server.version, None)

                        # Check if database needs to be loaded

                        if LOAD_DATABASES:
                            if (specific_t is None
                                    or "check_index_best_worst_large"
                                    in specific_t
                                    or "compare_db_large" in specific_t):
                                # Load Databases
                                load_databases(os.path.join(base_dir, 'bin'),
                                               dbs_to_load, port=port)
                        with working_path(MUT_HOME):
                            exit_status += run_mut(
                                port=port, parser=output_parser,
                                specific_tests=specific_t, env=os.environ,
                                force=FORCE, verbose=VERBOSE,
                                override_cmd=OVERRIDE_MUT_CMD
                            )
                    else:
                        print("# Server didn't start as expected, "
                              "it might need more time to boot")

    print("\n==================== *GLOBAL RESULTS* ====================\n")
    print("\n\nTESTS THAT FAILED AT LEAST ONCE: \n "
          "{0}".format(' '.join(sorted(output_parser.failed_tests))))
    print("\n\nTESTS THAT WERE ALWAYS SKIPPED: \n "
          "{0}\n\n\n".format(' '.join(sorted(output_parser.skipped_tests))))

    if RUN_COVERAGE:
        with working_path(MUT_HOME):
            execute("coverage combine")
            execute("coverage html -i")
            execute("coverage xml")
            shutil.move('htmlcov', os.path.join(BUILD_RESULTS, 'coverage'))

    if exit_status or len(output_parser.failed_tests):
        sys.exit(1)
    else:
        sys.exit(0)