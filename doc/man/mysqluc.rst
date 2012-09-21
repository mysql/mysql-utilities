
.. _`mysqluc`:

#####################################################################
``mysqluc`` - Command line client for running MySQL Utilities
#####################################################################

SYNOPSIS
--------

::

 mysqluc [--help | --version | [ | --verbose | --quiet |] --width=<num> |
          --utildir=<path> | --execute <command list>  <variable>=<value>]

DESCRIPTION
-----------

This utility provides a command line environment for running MySQL Utilities.

The mysqluc utility, hence console, allows users to execute any of the
currently installed MySQL Utilities command. The option `:option:--utildir` is
used to provide a path to the MySQL Utilities if the location is different from
when the utility is executed.

The console has a list of console or base commands. These allow the user to
interact with the features of the console itself. The list of base commands is
shown below along with a brief description.::

Command                 Description                                        
----------------------  ---------------------------------------------------
help utilities          Display list of all utilities supported.           
help <utility>          Display help for a specific utility.               
help | help commands    Show this list.                                    
exit | quit             Exit the console.                                  
set <variable>=<value>  Store a variable for recall in commands.           
show options            Display list of options specified by the user on   
                        launch.                                            
show variables          Display list of variables.                         
<ENTER>                 Press ENTER to execute command.                    
<ESCAPE>                Press ESCAPE to clear the command entry.           
<DOWN>                  Press DOWN to retrieve the previous command.       
<UP>                    Press UP to retrieve the next command in history.  
<TAB>                   Press TAB for type completion of utility, option,  
                        or variable names.                                 
<TAB><TAB>              Press TAB twice for list of matching type          
                        completion (context sensitive).                    

One of the most helpful base commands is the ability to see the options for a
given utility by typing 'help <utility>'. When the user types this command and
presses ENTER, the console will display a list of all of the options for the
utility.

The console provides tab completion for all commands, options for utilities,
and user-defined variables. Tab completion for commands allows users to specify
the starting N characters of a command and press TAB to complete the command.
If there are more than one command that matches the prefix, and the user
presses TAB twice, a list of all possible matches is displayed.

Tab completion for options is similar. The user must first type a valid MySQL
Utility command then types the first N characters of a command and presses TAB,
for example --verb<TAB>. In this case, the console will complete the option.
For the cases where an option requires a value, the console will complete the
option name and append the '=' character. Tab completion for options works for
both the full name and the alias (if available). If the user presses TAB twice,
the console will display a list of matching options. Pressing TAB twice
immediately after typing the name of a MySQL Utility will display a list of all
options for that utility.

Tab completion for variables works the same as that for options. In this case,
the user must first type the '$' character then press TAB. For example, if a
variable $SERVER1 exists, when the user types --server=$SER<TAB>, the console
will complete the $SERVER variable name. For cases where there are multiple
variables, pressing TAB twice will display a list of all matches to the first
$+N characters. Pressing TAB twice after typing only the $ character will
display a list of all variables.

Note: the console does not require typing the 'mysql' prefix for the utility.
For example, if the user types 'disku<TAB>' the console will complete the
command with 'diskusage '.

Executing utilities is accomplished by typing the complete command and pressing
ENTER. The user does not have to type 'python' or provide the '.py' file
extension. The console will add these if neeeded. 

The user can also run commands using the `:option:--execute` option. The value
for this option is a semi-colon separated list of commands to execute. These
can be base commands or MySQL Utility commands. The console will execute each
command and display the output. All commands to be run by the console must
appear inside a quoted string and separated by semi-colons. Commands outside
of the quoted string will be treated as arguments for the mysqluc utility
itself and thus ignored for execution.

Note: if there is an error in the console or
related code, the console will stop executing commands at the point of failure.
Commands may also be piped into the console using a mechanism like 'echo
"<commands>" | mysqluc". 

The console also allows users to set user-defined variables for commonly used
values in options. The syntax is simply 'set VARNAME=VALUE'. The user can see a
list of all variables by entering the 'show variables' command. To use the
values of these variables in utility commands, the user must prefix the value
with a '$'. For example, --server=$SERVER1 will substitute the value of the
SERVER1 user-defined variable when the utility is executed.

Note: user-defined variables have a session lifetime. They are not saved from
one execution to another of the users console.

User-defined variables may also be set by passing them as arguments to the
mysqluc command. For example, to set the SERVER1 variable and launch the
console, the user can launch the console using this command.::

$ mysqluc SERVER1=root@localhost

The user can provide any number of user-defined variables but they must contain
a value and no spaces around the '=' character. Once the console is launched,
the user can see all variables using the 'show variables' command.


OPTIONS
-------

.. option:: --version

   show program's version number and exit

.. option:: --help

   show the program's help page

.. option:: --verbose, -v

   control how much information is displayed. For example, -v =
   verbose, -vv = more verbose, -vvv = debug

.. option:: --quiet

   suppress all informational messages

.. option:: --execute <commands>, -e <commands>
   
   Execute commands and exit. Multiple commands are separated with semi-colons.
   Note: some platforms may require double quotes around command list. 

.. option:: --utildir <path>

   location of utilities

.. option:: --width <number>

   Display width

.. _`mysqluc-notes`:

NOTES
-----

Using the `:option:--execute` option or piping commands to the console may
require quotes or double quotes (for example, on Windows). 

EXAMPLES
--------

To launch the console, use this command::

  $ mysqluc
    
The following demonstrates launching the console and running the console
command 'help utilities' to see a list of all utilities supported. The console
will execute the command then exit.::

  $ mysqluc -e "help utilities"

  Utility           Description                                              
  ----------------  ---------------------------------------------------------
  mysqlindexcheck   check for duplicate or redundant indexes                 
  mysqlrplcheck     check replication                                        
  mysqluserclone    clone a MySQL user account to one or more new users      
  mysqldbcompare    compare databases for consistency                        
  mysqldiff         compare object definitions among objects where the       
                    difference is how db1.obj1 differs from db2.obj2         
  mysqldbcopy       copy databases from one server to another                
  mysqlreplicate    establish replication with a master                      
  mysqldbexport     export metadata and data from databases                  
  mysqldbimport     import metadata and data from files                      
  mysqlmetagrep     search metadata                                          
  mysqlprocgrep     search process information                               
  mysqldiskusage    show disk usage for databases                            
  mysqlserverinfo   show server information                                  
  mysqlserverclone  start another instance of a running server 

The following demonstrates launching the console to run several commands using
the `:option:--execute` option to including setting a variable for a server
connection and executing a utility using variable substitution. Note: it may be
necessary to escape the '$' on some platforms (for example, Linux). Output
below is an excerpt and is representational only.::

  $ mysqluc -e "set SERVER=root@host123; mysqldiskusage --server=\$SERVER"

  # Source on host123: ... connected.
  
  NOTICE: Your user account does not have read access to the datadir. Data
  sizes will be calculated and actual file sizes may be omitted. Some features
  may be unavailable.
  
  # Database totals:
  +--------------------+--------------+
  | db_name            |       total  |
  +--------------------+--------------+
  ...
  | world              |           0  |
  ...
  +--------------------+--------------+
  
  Total database disk usage = 1,072,359,052 bytes or 1022.00 MB
  
  #...done.

The following demonstrates launching the console using the commands shown above
but piped into the console on the command line. The results are the same as
above.::

  $ echo "set SERVER=root@host123; mysqldiskusage --server=\$SERVER" | mysqluc
  
The following demonstrates launching the console and setting variables via the
command line.::

  $ mysqluc SERVER=root@host123 VAR_A=57 -e "show variables"

  Variable  Value                                                            
  --------  -----------------------------------------------------------------
  SERVER    root@host123                                                     
  VAR_A     57                                                               


COPYRIGHT
---------

Copyright (c) 2011, Oracle and/or its affiliates. All rights reserved.

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
