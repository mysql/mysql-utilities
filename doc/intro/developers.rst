.. `developers`:

#############################################
Introduction to extending the MySQL Utilities
#############################################

Administration and maintenance on the MySQL server can at times be
complicated. Sometimes tasks require tedious or even repetitive operations
that can be time consuming to type and re-type. For these reasons and more,
the MySQL Utilities were created to help both beginners and experienced
database administrators perform common tasks.

What are the internals of the MySQL Utilities?
----------------------------------------------

MySQL Utilities are designed as a collection of easy to use Python scripts that
can be combined to provide more powerful features. Internally, the scripts use
the mysql.utilities module library to perform its various tasks. Since
a library of common functions is available, it is easy for a database
administrator to create scripts for common tasks. These utilities are
located in the ``/scripts`` folder of the installation or source tree.

If you have a task that is not met by these utilities or
one that can be met by combining one or more of the utilities or even parts
of the utilities, you can easily form your own custom solution. The
following sections present an example of a custom utility, discussing first
the anatomy of a utility and then what the ``mysql.utilities`` module
library has available.

Anatomy of a MySQL Utility
---------------------------

MySQL Utilities use a three-tier module organization. At the top is the
command script, which resides in the ``/scripts`` folder of the installation
or source tree. Included in the script is a command module designed to
encapsulate and isolate the bulk of the work performed by the utility. The
command module resides in the ``/mysql/utilities/command`` folder of the
source tree. Command modules have names similar to the script. A command
module includes classes and methods from one or more common modules where
the abstract objects and method groups are kept. The common modules reside
in the ``/mysql/utilities/common`` folder of the source tree. The following
illustrates this arrangement using the :command:`mysqlserverinfo` utility::

  /scripts/mysqlserverinfo.py
      |
      +--- /mysql/utilities/command/serverinfo.py
              |
              +--- /mysql/utilities/common/options.py
              |
              +--- /mysql/utilities/common/server.py
              |
              +--- /mysql/utilities/common/tools.py
              |
              +--- /mysql/utilities/common/format.py

Each utility script is designed to process the user input and option settings
and pass them on to the command module. Thus, the script contains only such
logic for managing and validating options. The work of the operation resides in
the command module.

Command modules are designed to be used from other Python applications. For
example, one could call the methods in the ``serverinfo.py`` module from
another Python script. This enables developers to create their own
interfaces to the utilties. It also permits developers to combine several
utilities to form a macro-level utility tailored to a specified need. For
example, if there is a need to gather server information as well as disk
usage, it is possible to import the ``serverinfo.py`` and ``diskusage.py``
modules and create a new utility that performs both operations.

Common modules are the heart of the MySQL Utilities library. These modules
contain classes that abstract MySQL objects, devices, and mechanisms. For
example, there is a server class that contains operations to be performed on
servers, such as connecting (logging in) and running queries.

The MySQL Utilities Library
---------------------------

While the library is growing, the following lists the current common modules
and the major classes and methods as of the 1.0.1 release::

  Module     Class/Method              Description
  ---------- ------------------------- ----------------------------------------
  database   Database                  Perform database-level operations
  dbcompare  get_create_object         Retrieve object create statement 
             diff_objects              Diff definitions of two objects
             check_consistency         Check data consistency of two tables
  format     format_tabular_list       Format list in either GRID or 
                                       delimited format to a file
             format_vertical_list      Format list in a vertical format to 
                                       a file
             print_list                Print list based on format (CSV, 
                                       GRID, TAB, or VERTICAL)
  options    setup_common_options      Set up option parser and options common 
                                       to all MySQL Utilities
             add_skip_options          Add common --skip options
             check_skip_options        Check skip options for validity
             check_format_option       Check format option for validity
             add_verbosity             Add verbosity and quiet options
             check_verbosity           Check whether both verbosity and quiet 
                                       options are being used
             add_difftype              Add difftype option
             add_engines               Add engine, default-storage-engine
                                       options
             check_engine_options      Check whether storage engines listed 
                                       in options exist
             parse_connection          Parse connection values
  rpl        Replication               Establish replication connection
                                       between a master and a slave
             get_replication_tests     Return list of replication test function
                                       pointers
  server     get_connection_dictionary Get connection dictionary
             find_running_servers      Check whether any servers are
                                       running on the local host
             connect_servers           Connect to source and destination server
             Server                    Connect to running MySQL server
                                       and perform server-level operations
  table      Index                     Encapsulate index for a given table 
                                       as defined by SHOW INDEXES
             Table                     Encapsulate table for given database
                                       to perform table-level operations
  tools      get_tool_path             Search for MySQL tool and return its
                                       full path
             delete_directory          Remove directory (folder) and contents
  user       parse_user_host           Parse user, passwd, host, port from
                                       user:passwd@host
             User                      Clone user and its grants to another
                                       user and perform user-level operations

General Interface Specifications and Code Practices
---------------------------------------------------

The MySQL Utilities are designed and coded using mainstream coding practices
and techniques common to the Python community. Effort has been made to adhere
to the most widely accepted specifications and techniques. This includes
limiting the choice of libraries used to the default libraries found in the
Python distributions. This ensures easier installation, enhanced portability,
and fewer problems with missing libraries. Similarly, external libraries
that resort to platform-specific native code are also not used.

The class method and function signatures are designed to make use of a small
number of required parameters and all optional parameters as a single
dictionary. Consider the following method::

  def do_something_wonderful(position, obj1, obj2, options={}):
      """Does something wonderful
      
      A fictional method that does something to object 2 based on the
      location of something in object 1.
      
      position[in]   Position in obj1
      obj1[in]       First object to manipulate
      obj2[in]       Second object to manipulate
      options[in]    Option dictionary
        width        width of printout (default 75)
        iter         max iterations (default 2)
        ok_to_fail   if True, do not throw exception
                     (default True)
        
      Returns bool - True = success, Fail = failed
      """

This example is typical of the methods and classes in the library.
Notice that this method has three required parameters and a dictionary
of options that may exist.

Each method and function that uses this mechanism defines its own default
values for the items in the dictionary. A quick look at the method
documentation shows the key names for the dictionary. This can be seen in
the preceding example where the dictionary contains three keys and the
documentation lists their defaults.

To call this method and pass different values for one or more of the options,
the code may look like this::

  opt_dictionary = {
    'width'      : 100,
    'iter'       : 10,
    'ok_to_fail' : False,
  }
  result = do_something_wonderful(1, obj_1, obj_2, opt_dictionary)

The documentation block for the preceding method is the style used
throughout the library.

Example
-------

Now that you are familiar with the MySQL utilities and the supporting library
modules, let us take a look at an example that combines some of these modules to
solve a problem.

Suppose that you want to develop a new database solution and need to use
real world data and user accounts for testing. The
:command:`mysqlserverclone` MySQL utility looks like a possibility but it
makes only an instance of a running server. It does not copy data. However,
:command:`mysqldbcopy` makes a copy of the data and
:command:`mysqluserclone` clones the users. You could run each of these
utilities in sequence, and that would work, but we are lazy at heart and
want something that not only copies everything but also finds it for us.
That is, we want a one-command solution.

The good news is that this is indeed possible and very easy to do. Let us start
by breaking the problem down into its smaller components. In a nutshell, we
must perform these tasks:

* Connect to the original server
* Find all of the databases
* Find all of the users
* Make a clone of the original server
* Copy all of the databases
* Copy all of the users

If you look at the utilities and the modules just listed, you see that we have
solutions and primitives for each of these operations. So you need not even
call the MySQL utilities directly (although you could). Now let us dive into
the code for this example.

The first task is to connect to the original server. We use the same
connection mechanism as the other MySQL utilities by specifying a ``--server``
option like this::

    parser.add_option("--server", action="store", dest="server",
                      type="string", default="root@localhost:3306",
                      help="connection information for original server in " + \
                      "the form: <user>:<password>@<host>:<port>:<socket>")

Once we process the options and arguments, connecting to the server is easy:
Use the ``parse_connection`` method to take the server option values and get
a dictionary with the connection values. All of the heavy diagnosis and
error handling is done for us, so we just need to check for exceptions::

    from mysql.utilities.common.options import parse_connection

    try:
        conn = parse_connection(opt.server)
    except:
        parser.error("Server connection values invalid or cannot be parsed.")

Now that we have the connection parameters, we create a class instance of
the server using the ``Server`` class from the ``server`` module and then
connect. Once again, we check for exceptions::

    from mysql.utilities.common.server import Server

    server_options = {
        'conn_info' : conn,
        'role'      : "source",
    }
    server1 = Server(server_options)
    try:
        server1.connect()
    except UtilError, e:
        print "ERROR:", e.errmsg

The next item is to get a list of all of the databases on the server. We use
the new server class instance to retrieve all of the databases on the server::

    db_list = []
    for db in server1.get_all_databases():
        db_list.append((db[0], None))

If you wanted to supply your own list of databases, you could use an option
like the following. You could also add an ``else`` clause which would enable
you to either get all of the databases by omitting the ``--databases``
option or supply your own list of databases (for example,
``--databases=db1,db2,db3``)::

    parser.add_option("-d", "--databases", action="store", dest="dbs_to_copy",
                      type="string", help="comma-separated list of databases "
                      "to include in the copy (omit for all databases)",
                      default=None)

    if opt.dbs_to_copy is None:
        for db in server1.get_all_databases():
            db_list.append((db[0], None))
    else:
        for db in opt.dbs_to_copy.split(","):
            db_list.append((db, None))

Notice we are creating a list of tuples. This is because the ``dbcopy`` module
uses a list of tuples in the form (*old_db*, *new_db*) to enable you to copy a
database to a new name. For our purposes, we do not want a rename so we leave
the new name value set to ``None``.

Next, we want a list of all of the users. Once again, you could construct the
new solution to be flexible by permitting the user to specify the users
to copy. We leave this as an exercise.

In this case, we do not have a primitive for getting all users created on a
server. But we do have the ability to run a query and process the results.
Fortunately, there is a simple SQL statement that can retrieve all of the users
on a server. For our purposes, we get all of the users except the root 
and anonymous users, then add each to a list for processing later::

    users = server1.exec_query("SELECT user, host "
                               "FROM mysql.user "
                               "WHERE user != 'root' and user != ''")
    for user in users:
        user_list.append(user[0]+'@'+user[1])

Now we must clone the original server and create a viable running instance.
When you examine the :command:`mysqlserverclone` utility code, you see that
it calls another module located in the ``/mysql/utilities/command`` sub
folder. These modules are where all of the work done by the utilities take
place. This enables you to create new combinations of the utilities by
calling the actual operations directly. Let's do that now to clone the
server.

The first thing you notice in examining the ``serverclone`` module is that
it takes a number of parameters for the new server instance. We supply those
in a similar way as options::

    parser.add_option("--new-data", action="store", dest="new_data",
                      type="string", help="the full path to the location "
                      "of the data directory for the new instance")
    parser.add_option("--new-port", action="store", dest="new_port",
                      type="string", default="3307", help="the new port "
                           "for the new instance - default=%default")
    parser.add_option("--new-id", action="store", dest="new_id",
                      type="string", default="2", help="the server_id for "
                           "the new instance - default=%default")

    from mysql.utilities.command import serverclone

    try:
        res = serverclone.clone_server(conn, opt.new_data, opt.new_port,
                                        opt.new_id, "root", None, False, True)
    except exception.UtilError, e:
        print "ERROR:", e.errmsg
        exit(1)

As you can see, the operation is very simple. We just added a few options we
needed like ``--new-data``, ``--new-port``, and ``--new-id`` (much like
:command:`mysqlserverclone`) and supplied some default values for the other
parameters.

Next, we need to copy the databases. Once again, we use the command module
for :command:`mysqldbcopy` to do all of the work for us. First, we need the
connection parameters for the new instance. This is provided in the form of
a dictionary. We know the instance is a clone, so some of the values are
going to be the same and we use a default root password, so that is also
known. Likewise, we specified the data directory and, since we are running
on a Linux machine, we know what the socket path is. (For Windows machines,
you can leave the socket value None.) We pass this dictionary to the copy
method::

    dest_values = {
        "user"   : conn.get("user"),
        "passwd" : "root",
        "host"   : conn.get("host"),
        "port"   : opt.new_port,
        "unix_socket" : os.path.join(opt.new_data, "mysql.sock")
    }

In this case, a number of options are needed to control how the copy works
(for example, if any objects are skipped). For our purposes, we want all
objects to be copied so we supply only the minimal settings and let the
library use the defaults. This example shows how you can 'fine tune' the
scripts to meet your specific needs without having to specify a lot of
additional options in your script. We enable the quiet option on so as not
to clutter the screen with messages, and tell the copy to skip databases
that do not exist (in case we supply the ``--databases`` option and provide
a database that does not exist)::

    options = {
        "quiet" : True,
        "force" : True
    }

The actual copy of the databases is easy. Just call the method and supply the
list of databases::

    from mysql.utilities.command import dbcopy

    try:
        dbcopy.copy_db(conn, dest_values, db_list, options)
    except exception.UtilError, e:
        print "ERROR:", e.errmsg
        exit(1)

Lastly, we copy the user accounts. Once again, we must provide a dictionary
of options and call the command module directly. In this case, the
``userclone`` module provides a method that clones one user to one or more
users so we must loop through the users and clone them one at a time::

    from mysql.utilities.command import userclone

    options = {
        "overwrite" : True,
        "quiet"     : True,
        "globals"   : True
    }

    for user in user_list:
        try:
            res = userclone.clone_user(conn, dest_values, user,
                                       (user,), options)
        except exception.UtilError, e:
            print "ERROR:", e.errmsg
            exit(1)

We are done. As you can see, constructing new solutions from the MySQL utility
command and common modules is easy and is limited only by your imagination.

Enhancing the Example
---------------------

A complete solution for the example named ``copy_server.py`` is located in
the ``/docs/intro/examples`` folder. It is complete in so far as this
document explains, but it can be enhanced in a number of ways. The following
briefly lists some of the things to consider adding to make this example
utility more robust.

* Table locking: Currently, databases are not locked when copied. To
  achieve a consistent copy of the data on an active server, you may want to
  add table locking or use transactions (for example, if you are using InnoDB)
  for a more consistent copy.
* Skip users not associated with the databases being copied.
* Do not copy users with only global privileges.
* Start replication after all of the users are copied (makes this example a
  clone and replicate scale out solution).
* Stop new client connections to the server during the copy.

Conclusion
----------

If you find some primitives missing or would like to see more specific
functionality in the library or scripts, please contact us with your ideas or
better still, write them yourselves! We welcome all suggestions in code or
text.  To file a feature request or bug report, visit http://bugs.mysql.com.
For discussions, visit http://forums.mysql.com/list.php?155.
