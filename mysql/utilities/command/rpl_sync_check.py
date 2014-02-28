#
# Copyright (c) 2014, Oracle and/or its affiliates. All rights reserved.
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
This file contains the command to check the data consistency in a replication
topology.
"""

from mysql.utilities.common.rpl_sync import RPLSynchronizer


def check_data_consistency(master_cnx_val, slaves_cnx_val, options,
                           data_to_include=None, data_to_exclude=None,
                           check_srv_versions=True):
    """
    Check the data consistency of a replication topology.

    This function creates a replication synchronizer checker and checks the
    data consistency between the given list of servers.

    master_cnx_val[in]      Dictionary with the connection values for the
                            master.
    slaves_cnx_val[in]      List of the dictionaries with the connection
                            values for each slave.
    options[in]             Dictionary of options (discover, verbosity,
                            rpl_timeout, checksum_timeout, interval).
    data_to_include[in]     Dictionary of data (set of tables) by database to
                            check.
    data_to_exclude[in]     Dictionary of data (set of tables) by database to
                            exclude from the check.
    check_srv_versions[in]  Flag indicating if the servers version check will
                            be performed. By default True, meaning that
                            differences between server versions will be
                            reported.

    Returns the number of issues found during the consistency check.
    """
    # Create replication synchronizer.
    rpl_sync = RPLSynchronizer(master_cnx_val, slaves_cnx_val, options)
    if check_srv_versions:
        # Check server versions and report differences.
        rpl_sync.check_server_versions()
    # Check GTID support, skipping slave with GTID disabled, and report
    # GTID executed differences between master and slaves.
    rpl_sync.check_gtid_sync()
    # Check data consistency and return the number of issues found.
    return rpl_sync.check_data_sync(options, data_to_include, data_to_exclude)


def check_server_versions(master_cnx_val, slaves_cnx_val, options):
    """
    Check the server versions of a replication topology.

    This method creates a replication synchronizer checker and compares the
    server versions of the given list of servers, reporting differences
    between them.

    master_cnx_val[in]  Dictionary with the connection values for the master.
    slaves_cnx_val[in]  List of the dictionaries with the connection values
                        for each slave.
    options[in]         Dictionary of options (discover, verbosity).
    """
    # Create replication synchronizer.
    rpl_sync = RPLSynchronizer(master_cnx_val, slaves_cnx_val, options)
    # Check server versions and report differences.
    rpl_sync.check_server_versions()
