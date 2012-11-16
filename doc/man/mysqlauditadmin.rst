.. `mysqlauditadmin`:

####################################################
``mysqlauditadmin`` - Audit Log Maintenance Utility
####################################################

SYNOPSIS
--------

::

 mysqlauditadmin [OPTIONS]...
 mysqlauditadmin [OPTIONS]... [COMMAND]
 mysqlauditadmin --server=user:pass@host:port [--show-options] [COMMAND [--value=VALUE]]
 mysqlauditadmin --file-stats --audit-log-name=FULL_PATH
 mysqlauditadmin copy --audit-log-name=FULL_PATH --copy-to=DESTINATION [--remote-login=user:host] 

 
DESCRIPTION
-----------

This utility allows users to perform maintenance action on the audit log, 
enabling them to monitor the audit log file growth and control its rotation. 
Here, rotation refers to the action of replacing the current audit log file by 
a new one for continuous use, renaming (with a timestamp extension) and copying 
the previously used audit log file to a defined location.

In particular, the utility allows the users to view and modify some audit log 
control variables, display the audit log file status, perform on-demand rotation 
of the log file and copy files to other locations. These features enable users to 
easily monitor the audit log file growth and control its rotation (automatically 
based on the defined file size threshold, or manually by a on-demand command).

The following commands are available to manage the audit log:

**copy**
This command copies the audit log specified by :option:`--audit-log-name` to the
destination path specified by :option:`--copy-to`. The :option:`--remote-login` 
can be used for remote login for copying log files. Note: the destination path 
must be locally accessible by the current user.

**policy**
This command is used to change the audit logging policy. The accepted values 
are ALL, NONE, LOGINS, QUERIES, DEFAULT, and must be set using the 
:option:`--value`. The defined policy values have the following meaning: 
ALL - log all events; NONE - log nothing; LOGINS - log only login events; 
QUERIES - log only query events; DEFAULT - set the default log policy. 
The :option:`--server` is also required to execute this command.

**rotate_on_size**
This command sets the file size threshold for automatic rotation of the audit 
log (i.e., variable audit_log_rotate_on_size). The value is set using the 
:option:`--value` and must be in the range (0, 4294967295). This command also 
requires the :option:`--server` to be specified. Note: if the variable is set 
with a value that is not a multiple of 4096, then it is truncated to the 
nearest multiple. 

**rotate**
This command is used to perform an on-demand audit log rotation, and only 
requires the specification of :option:`--server`. Note: this command has no 
effect if the audit log file size is smaller than 4096 (i.e., minimum allowed
value greater than 0 for the audit_log_rotate_on_size variable).


OPTIONS
-------

:command:`mysqlauditadmin` accepts the following command-line options:

.. option:: --audit-log-name=AUDIT_LOG_FILE

   Full path and file name for the audit log file. 
   Used by the :option:`--file-stats` option and the **copy** command.

.. option:: --copy-to=COPY_DESTINATION

   The location to copy the specified audit log file. 
   The path must be locally accessible for the current user.

.. option:: --file-stats

   Display the audit log file statistics.

.. option:: --help

   Display a help message and exit.

.. option:: --remote-login=REMOTE_LOGIN

   User name and host to be used for remote login for
   copying log files, in the format <*user*>:<*host or IP*>.
   Password will be prompted.

.. option:: --server=SERVER

   Connection information for the server in
   <*user*>[:<*passwd*>]@<*host*>[:<*port*>][:<*socket*>] format.

.. option:: --show-options

   Display the audit log system variables.

.. option:: --value=VALUE

   Value used to set variables based on the specified commands
   (i.e., **policy** and  **rotate_on_size**).

.. option::  --verbose, -v

   Specify how much information to display. Use this option
   multiple times to increase the amount of information.  For example,
   :option:`-v` = verbose, :option:`-vv` = more verbose, :option:`-vvv` =
   debug.

.. option:: --version

   Display version information and exit.


NOTES
-----

This utility can only be applied to servers with the audit log plug-in enabled.

This utility requires the use of Python version 2.7 or higher, but does not 
support Python 3.


LIMITATIONS
-----

The :option:`--remote-login` option is not supported on Windows platforms. In
Windows, please use UNC paths and perform a local copy operation, omitting the
:option:`--remote-login` option.


EXAMPLES
--------

To display the audit log system variables, run the following command::

  $ mysqlauditadmin --show-options --server=root@localhost:3310
  #
  # Audit Log Variables and Options
  #
  +---------------------------+---------------+
  | Variable_name             | Value         |
  +---------------------------+---------------+
  | audit_log_buffer_size     | 1048576       |
  | audit_log_file            | audit.log     |
  | audit_log_flush           | OFF           |
  | audit_log_policy          | ALL           |
  | audit_log_rotate_on_size  | 0             |
  | audit_log_strategy        | ASYNCHRONOUS  |
  +---------------------------+---------------+

To perform a (manual) rotation of the audit log file, 
use the following command::

  $ mysqlauditadmin --server=root@localhost:3310 rotate
  #
  # Executing ROTATE command.
  #

To display the audit log file statistics, run the following command::

  $ mysqlauditadmin --file-stats --audit-log-name=../SERVER/data/audit.log
  +------------------------------+--------+---------------------------+---------------------------+
  | File                         | Size   | Created                   | Last Modified             |
  +------------------------------+--------+---------------------------+---------------------------+
  | audit.log                    | 3258   | Wed Sep 26 11:07:43 2012  | Wed Sep 26 11:07:43 2012  |
  | audit.log.13486539046497235  | 47317  | Wed Sep 26 11:05:04 2012  | Wed Sep 26 11:05:04 2012  |
  +------------------------------+--------+---------------------------+---------------------------+

To change the audit log policy to log only query events, and show the 
system variables before and after the execution of the **policy** command, 
use the following command::

  $ mysqlauditadmin --show-options --server=root@localhost:3310 \
    policy --value=QUERIES
  #
  # Showing options before command.
  #
  # Audit Log Variables and Options
  #
  +---------------------------+---------------+
  | Variable_name             | Value         |
  +---------------------------+---------------+
  | audit_log_buffer_size     | 1048576       |
  | audit_log_file            | audit.log     |
  | audit_log_flush           | OFF           |
  | audit_log_policy          | ALL           |
  | audit_log_rotate_on_size  | 0             |
  | audit_log_strategy        | ASYNCHRONOUS  |
  +---------------------------+---------------+
  
  #
  # Executing POLICY command.
  #
  
  #
  # Showing options after command.
  #
  # Audit Log Variables and Options
  #
  +---------------------------+---------------+
  | Variable_name             | Value         |
  +---------------------------+---------------+
  | audit_log_buffer_size     | 1048576       |
  | audit_log_file            | audit.log     |
  | audit_log_flush           | OFF           |
  | audit_log_policy          | QUERIES       |
  | audit_log_rotate_on_size  | 0             |
  | audit_log_strategy        | ASYNCHRONOUS  |
  +---------------------------+---------------+

To change the audit log automatic file rotation size to 32535, and 
show the system variables before and after the execution of the 
**rotate_on_size** command, use the following command. (Notice that 
the value set is actually 28672 because the specified rotate_on_size 
value is truncated to a multiple of 4096)::
  
  $ mysqlauditadmin --show-options --server=root@localhost:3310 \
    rotate_on_size --value=32535
  #
  # Showing options before command.
  #
  # Audit Log Variables and Options
  #
  +---------------------------+---------------+
  | Variable_name             | Value         |
  +---------------------------+---------------+
  | audit_log_buffer_size     | 1048576       |
  | audit_log_file            | audit.log     |
  | audit_log_flush           | OFF           |
  | audit_log_policy          | ALL           |
  | audit_log_rotate_on_size  | 0             |
  | audit_log_strategy        | ASYNCHRONOUS  |
  +---------------------------+---------------+
  
  #
  # Executing ROTATE_ON_SIZE command.
  #
  
  #
  # Showing options after command.
  #
  # Audit Log Variables and Options
  #
  +---------------------------+---------------+
  | Variable_name             | Value         |
  +---------------------------+---------------+
  | audit_log_buffer_size     | 1048576       |
  | audit_log_file            | audit.log     |
  | audit_log_flush           | OFF           |
  | audit_log_policy          | ALL           |
  | audit_log_rotate_on_size  | 28672         |
  | audit_log_strategy        | ASYNCHRONOUS  |
  +---------------------------+---------------+

To perform a copy of a audit log file to another location, 
use the following command::

  $ mysqlauditadmin --audit-log-name=../SERVER/data/audit.log.13486539046497235 \
    copy --copy-to=/BACKUP/Audit_Logs

To copy a audit log file from a remote server/location to the current location
(user password will be prompted), use the following command::

  $ mysqlauditadmin --audit-log-name=audit.log.13486539046497235 \
    copy --remote-login=user:host --copy-to=.


COPYRIGHT
---------

Copyright (c) 2012, Oracle and/or its affiliates. All rights reserved.

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; version 2 of the License.

This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301 USA
