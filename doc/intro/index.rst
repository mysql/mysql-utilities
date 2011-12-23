.. intro-index:

###############################
Introduction to MySQL Utilities
###############################

.. toctree::

   connspec

Administration and maintenance on the MySQL server can at times be more
complicated than necessary. Sometimes tasks require tedious or even repetitive
operations that can be time consuming to type and re-type. For these reasons
and more, the MySQL Utilities were created to help out with common tasks for
both beginners and experienced database administrators.

What are the MySQL Utilities?
-----------------------------

MySQL Utilities are designed as a collection of easy to use Python scripts that
can be combined into more powerful features. The scripts internally make use of
the :ref:`mysql.utilities` module library to perform its various tasks. Since
a library of common functions is available, it is easy for a database
administrator to create her own scripts for common tasks. These utilities are
located in the scripts folder of the installation or source tree.

If, on the other hand, you have a task that is not met by these utilities or
one that can be met if you combined one or more of the utilities or even parts
of the utilities, you can easily form your own custom solution. In the
following sections, we present an example of a custom utility. First, we
examine the anatomy of a utility and then what the mysql.utilities module
library has available.

Anatomy of a MySQL Utility
---------------------------

MySQL Utilities are built using a three-tier module organization. At the top is
the command script and resides in the /scripts folder of the installation or
source tree. Included in the script is a command module designed to encapsulate
and isolate the bulk of the work for the utility. The command module resides in
the /mysql/utilities/command folder of the source tree. Command modules have
names similar to the script. A command module will include classes and methods
from one or more common modules where the abstract objects and method groups
are kept. The common modules reside in the /mysql/utilities/common folder of
the source tree. The following illustrates this arrangement using the
mysqlserverinfo utility.::

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

The utility scripts are designed to process the user input and option settings
and pass them on to the command module. Thus, the script contains only such
logic for managing and validating options. The work of the operation resides in
the command module.

Command modules are designed to be used from other Python applications. For
example, one could call the methods in the serverinfo.py module from another
Python script. This enables developers to create their own interfaces to the
utilties. It also permits developers to combine several utilities to form a
macro-level utility tailored to a specified need. For example, if there is a
need to gather server information as well as disk usage, it is possible to
import the serverinfo.py and diskusage.py modules and create a new utility
that performs both operations.

Common modules are the heart of the MySQL Utilities library. These modules
contain classes that abstract MySQL objects, devices, and mechanisms. For
example, there is a server class that contains operations to be performed on
servers like connecting (logging in) and running queries.

The MySQL Utilities Library
---------------------------

While the library is growing, the following lists the current common modules
and the major classes and methods as of the 1.0.1 release.::

  Module     Class/Method              Description
  ---------- ------------------------- ----------------------------------------
  database   Database                  perform database-level operations
  dbcompare  get_create_object         retrieve object's create statement 
             diff_objects              diff the definition of two objects
             check_consistency         check the data consistency of two tables
  format     format_tabular_list       format a list in either GRID or 
                                       delimited format to a file
             format_vertical_list      format a list in a vertical format to 
             print_list                file print a list based on format (CSV, 
                                       GRID, TAB, or VERTICAL)
  options    setup_common_options      setup option parser and options common 
                                       to all MySQL Utilities
             add_skip_options          add the common --skip options
             check_skip_options        check skip options for validity
             check_format_option       check format option for validity
             add_verbosity             add the verbosity and quiet options
             check_verbosity           check to see if both verbosity and quiet 
                                       are being used
             add_difftype              add the difftype option
             add_engines               add the engine, default-storage-engine
                                       options
             check_engine_options      check to see if storage engines listed 
                                       in options exist
             parse_connection          parse connection values
  rpl        Replication               used to establish a replication
                                       connection between a master and a slave
             get_replication_tests     return list of replication test function
                                       pointers
  server     get_connection_dictionary get the connection dictionary
             find_running_servers      check to see if there are any servers
                                       running on the local host
             connect_servers           connect to source and destination server
             Server                    used to connect to running MySQL server
                                       and perform server-level operations
  table      Index                     encapsulates an index for a given table 
                                       as defined by SHOW INDEXES FROM
             Table                     encapsulates a table for given database
                                       to perform table-level operations
  tools      get_tool_path             search for a MySQL tool and return the
                                       full path
             delete_directory          remove a directory (folder) and contents
  user       parse_user_host           parse user, passwd, host, port from
                                       user:passwd@host
             User                      used to clone the user and its grants to
                                       another user and perform user-level
                                       operations

General Interface Specifications and Code Practices
---------------------------------------------------

The MySQL Utilities are designed and coded using mainstream coding practices
and techniques common to the Python community. Effort has been made to adhere
to the most widely accepted specifications and techniques. This includes
limiting the choice of libraries used to the default libraries found in the
Python distributions. This ensures easier installation, enhanced portability,
and fewer problems with missing libraries. Similarly, external libraries
that resort to platform specific native code are also not used.

The class method and function signatures are designed to make use of a small
number of required parameters and all optional parameters as a single
dictionary. Consider the following method.::

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

This example is typical of the methods and classes in the library. Notice this
method has three required parameters and a dictionary of options that may exist.

Each method and function that uses this mechanism defines its own default
values for the items in the dictionary. A quick look at the method
documentation will list the key names for the dictionary. This can be seen in
the example above where the dictionary contains three keys and the
documentation lists their defaults.

To call this method and pass different values for one or more of the options,
the code may look similar to the following.::

  opt_dictionary = {
    'width'      : 100,
    'iter'       : 10,
    'ok_to_fail' : False,
  }
  result = do_something_wonderful(1, obj_1, obj_2, opt_dictionary)

The documentation block for the above method is the style used throughout the
library. 

Example
-------

Now that you are familiar with the MySQL utilities and the supporting library
modules, let us take a look at an example of combining some of these modules to
solve a problem.

Suppose you want to develop a new database solution and need to use real world
data and user accounts for testing. The MySQL utility, mysqlserverclone, looks
like a possibility but it only makes an instance of a running server - it does
not copy data. However, mysqldbcopy makes a copy of the data and mysqluserclone
makes clones of the users. You could run each of these utilities in sequence,
and that would work, but we are lazy at heart so we want something that will not
only copy everything but also find it for us - we want a one command solution.

The good news here is this is indeed possible and very easy to do. Let us start
with breaking the problem down into its smaller components. In a nutshell, we
need to do the following tasks:

* connect to the original server
* find all of the databases
* find all of the users
* make a clone of the original server
* copy all of the databases
* copy all of the users

If you look at the utilities and the modules listed above, you will see we have
solutions and primitives for each of these operations. So you don't even have
to call the MySQL utilities directly (but you could). Now let us dive into
the code for this example.

The first thing we need is to connect to the original server. We use the same
connection mechanism as the other MySQL utilities by specifying a --server
option like this:::

    parser.add_option("--server", action="store", dest="server",
                      type="string", default="root@localhost:3306",
                      help="connection information for original server in " + \
                      "the form: <user>:<password>@<host>:<port>:<socket>")

Once we process the options and arguments, connecting to the server is easy and
can be done like the following. Here we use the parse_connection method to take
the server option values and get a dictionary with the connection values. All
of the heavy diagnosis and error handling is done for us so we just need to
check for exceptions.::

    from mysql.utilities.common.options import parse_connection

    try:
        conn = parse_connection(opt.server)
    except:
        parser.error("Server connection values invalid or cannot be parsed.")

Now that we have the connection parameters, we create a class instance of the
server using the Server class from the server module and then connect. Once
again, we check for exceptions.::

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
the new server class instance to retrieve all of the databases on the server.::

    db_list = []
    for db in server1.get_all_databases():
        db_list.append((db[0], None))

If you wanted to supply your own list of databases, you could use an option
like the following. You could also add an else clause which would allow you to
either get all of the databases by omitting the --databases option or supply
your own list of databases (e.g. --databases=db1,db2,db3).::

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

Notice we are creating a list of tuples. This is because the dbcopy module
uses a list of tuples in the form (old_db, new_db) to allow you to copy a
database to a new name. For our purposes, we don't want a rename so we leave
the new name value set to None.

Next, we want a list of all of the users. Once again, you could construct the
new solution to be flexible by allowing the user to specify the users she wants
to copy. We leave this as an exercise.

In this case, we do not have a primitive for getting all users created on a
server. But we do have the ability to run a query and process the results.
Fortunately, there is a simple SQL statement that can retrieve all of the users
on a server. For our purposes, we get all of the users except the root user
and the anonymous user(s). We then add each to a list for processing later.::

    users = server1.exec_query("SELECT user, host "
                               "FROM mysql.user "
                               "WHERE user != 'root' and user != ''")
    for user in users:
        user_list.append(user[0]+'@'+user[1])

Now we must clone the original server and create a viable running instance.
When you examine the mysqlserverclone utility code, you will see it calls
another module located in the mysql.utilities.command sub folder. These modules
are where all of the work of the utilities take place. This allows you to
create new combinations of the utilities by calling the actual operations
directly. Let's do that now to clone the server.

The first thing you notice in examining the serverclone module is that it takes
a number of parameters for the new server instance. We will supply those in a
similar way as options.::

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
needed like --new-data, --new-port, and --new-id (much like mysqlserverclone)
and supplied some default values for the other parameters.

Next, we need to start copying the databases. Once again, we will use the
command module for mysqldbcopy to do all of the work for us. First, we need the
connection parameters to the new instance. This is provided in the form of a
dictionary. We know the instance is a clone so some of the values are going to
be the same and we use a default root password so that is also known. Likewise,
we specified the data directory and, since we are running on a Linux machine,
we know what the socket path is. Note: for Windows machines, you can leave the
socket value None. We will pass this dictionary to the copy method.::

    dest_values = {
        "user"   : conn.get("user"),
        "passwd" : "root",
        "host"   : conn.get("host"),
        "port"   : opt.new_port,
        "unix_socket" : os.path.join(opt.new_data, "mysql.sock")
    }

In this case, there are also a number options needed to control how the copy
works (i.e. if any objects are skipped). For our purposes, we want all objects
to be copied so we will supply only the minimal settings and let the library
use the defaults. This example shows how you can 'fine tune' the scripts to
meet your specific needs without having to specify a lot of additional options
in your script. We will set the quiet option on so we won't clutter the screen
with messages and tell the copy to skip databases that don't exist (in case we
supply the --databases option and provide a database that doesn't exist).::

    options = {
        "quiet" : True,
        "force" : True
    }

The actual copy of the databases is easy. Just call the method and supply the
list of databases.::

    from mysql.utilities.command import dbcopy

    try:
        dbcopy.copy_db(conn, dest_values, db_list, options)
    except exception.UtilError, e:
        print "ERROR:", e.errmsg
        exit(1)

Lastly, we copy the user accounts. Once again, we need to provide a dictionary
of options and we will call the command module directly. Note however, the
userclone module provides a method that clones one user to one or more users so
we will have to loop through the users and clone them one at a time.::

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

We're done. As you can see, constructing new solutions from the MySQL utility
command and common modules is easy and is limited only by your imagination.

Enhancing the Example
---------------------

A complete solution for the example named copy_server.py is located in the
/docs/intro/examples folder. It is complete in so far as this document explains,
but it can be enhanced in a number of ways. The following briefly lists some
of the things you may want to consider adding to make this example a more
robust utility.

* table locking : currently, the databases are not locked when copied. To
  achieve a consistent copy of the data on an active server, you may want to
  add table locking or use transactions (e.g. if you are using InnoDB) for a
  more consistent copy.
* skip users not associated with the databases being copied
* do not copy users with only global privileges
* start replication after all of the users are copied (makes this example a
  clone and replicate scale out solution)
* stopping new client connections to the server during the copy

Conclusion
----------

If you find some primitives missing or would like to see more specific
functionality in the library or scripts, please contact us with your ideas or
better still - write them yourselves! We welcome all suggestions in code or
text.
