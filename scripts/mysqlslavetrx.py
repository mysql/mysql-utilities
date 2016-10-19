#!/usr/bin/env python
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
This file contains the replication synchronization checker utility. It is used
to check the data consistency between master and slaves (and synchronize the
data if requested by the user).
"""

import os
import sys

from mysql.utilities.common.tools import check_python_version
from mysql.utilities.command.rpl_admin import skip_slaves_trx
from mysql.utilities.common.messages import PARSE_ERR_OPTS_REQ
from mysql.utilities.common.options import (add_slaves_option, add_verbosity,
                                            check_gtid_set_format,
                                            check_password_security,
                                            setup_common_options)
from mysql.utilities.common.tools import check_connector_python
from mysql.utilities.common.topology import parse_topology_connections
from mysql.utilities.exception import UtilError, UtilRplError

# Check Python version compatibility
check_python_version()

# Check for connector/python
if not check_connector_python():
    sys.exit(1)

# Constants
NAME = "MySQL Utilities - mysqlslavetrx"
DESCRIPTION = "mysqlslavetrx - skip transactions on slaves"
USAGE = "%prog --gtid-set=gtid_set --slaves=user:pass@host:port"
EXTENDED_HELP = """
Introduction
------------
The mysqlslavetrx utility is designed to skip multiple transactions on slaves
in a quick and easy way. More specifically, it injects empty transactions
on the slaves for each GTID that will be skipped.

The utility requires GTIDs to be enabled on all slaves. It does not require
replication to be stopped. However, in some situation it is recommended.
For example, in order to skip a transaction from the master  on a slave, that
slave should be stopped otherwise the target transaction might still be
replicated (and not skipped).

Note: Only transactions (GTIDs) that were not committed can be skipped, since
two transactions cannot be applied with the same GTID. GTIDs already in the
GTID_EXECUTED set of a slave will be ignored.

The utility requires the specification of the GTID set to skip and the list of
target slaves as shown in the following example.

  # Skip the specified GTID set (three transaction: 10, 11, 12) on two slaves.

  $ mysqlslavetrx --gtid-set=ee2655ae-2e88-11e4-b7a3-606720440b68:10-12 \\
                  --slaves=rpl:pass@host2:3306,rpl:pass@host3:3306

Helpful Hints
-------------
  - Use the --dryrun option to execute the utility in dry run mode and confirm
    which transactions would be skipped with the provided input values without
    effectively skipping them.

WARNING: Skipping transactions is a useful technique to recover from erroneous
situations with replication. However, it must be applied with extreme caution
and with full knowledge of its consequences as it might lead to data
inconsistencies between the replication servers. For example, if a transaction
that insert some data 'row1' in table 't1' fails on one slave and that
transaction is skipped to solve the issue, then that data will be missing from
the slave (and no longer replicated). As a consequence the data for table 't1'
will be inconsistent with the one on the master and the other slaves because
'row1' will be missing.

"""

if __name__ == '__main__':
    # Setup the command parser with common options (excluding --).
    parser = setup_common_options(os.path.basename(sys.argv[0]),
                                  DESCRIPTION, USAGE, server=False,
                                  extended_help=EXTENDED_HELP, add_ssl=True)

    # Add option for the GTID set to skip..
    parser.add_option("--gtid-set", action="store", dest="gtid_set",
                      type="string", default=None,
                      help="set of Global Transaction Identifiers (GTID) to "
                           "skip.")

    # Add the --slaves option.
    add_slaves_option(parser)

    # Add option for the dry run mode.
    parser.add_option("--dryrun", action="store_true", dest="dry_run",
                      default=False,
                      help="determine the transactions (GTID) to be skipped "
                           "for each slave but without effectively skipping "
                           "them (injecting empty transactions) - useful to "
                           "test the transactions that would be skipped.")

    # Add verbose option (no --quiet option).
    add_verbosity(parser, False)

    # Parse the options and arguments.
    opt, args = parser.parse_args()

    # Check security settings
    check_password_security(opt, args)

    # Options --gtid-set and --slaves options are required.
    if not opt.gtid_set:
        parser.error(PARSE_ERR_OPTS_REQ.format(opt='--gtid-set'))
    if not opt.slaves:
        parser.error(PARSE_ERR_OPTS_REQ.format(opt='--slaves'))

    # Check GTID set format.
    check_gtid_set_format(parser, opt.gtid_set)

    # Parse the connection parameters for the slaves (no candidates).
    try:
        opt.master = None  # No master option available, set value to None.
        _, slaves_val, _ = parse_topology_connections(
            opt, parse_candidates=False
        )
    except UtilRplError:
        _, err, _ = sys.exc_info()
        sys.stderr.write("ERROR: {0}\n".format(err.errmsg))
        sys.exit(1)

    # Create dictionary of options
    options = {
        'verbosity': 0 if opt.verbosity is None else opt.verbosity,
        'dry_run': opt.dry_run,
    }

    # Skip transactions for the given list of slaves.
    try:
        skip_slaves_trx(opt.gtid_set, slaves_val, options)
    except UtilError:
        _, err, _ = sys.exc_info()
        sys.stderr.write("ERROR: {0}\n".format(err.errmsg))
        sys.exit(1)
