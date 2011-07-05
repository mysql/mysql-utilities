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
the :ref:`mysql.utilities` module library to perform it's various tasks. Since
a library of common functions is available, it is easy for a database
administrator to create her own scripts for common tasks.

There are several useful utilities that you can use without modification to
perform a variety of tasks. These utilities include the following and are
located in the scripts folder.

* mysqldbcopy.py : copy one or more databases from one server to another
* mysqldbexport.py : export one or more databases to a file in a variety of
  formats: comma-separated values (CSV), tab-separated values (TAB), executable
  statements (SQL), tabular form (GRID) like mysql monitor, or vertical
  (VERTICAL) like the \G option in mysql monitor.
* mysqldbimport.py : import one or more databases from a file in one of the
  formats from mysqlexport
* mysqlindexcheck.py : search for redundant or duplicate indexes in one or
  more tables
* mysqlmetagrep.py : search for phrases in object metadata
* mysqlprocgrep.py : search for processes
* mysqlreplicate.py : quick replication setup among two servers
* mysqlserverclone.py : make a new instance of a running server
* mysqluserclone.py : copy one user and her grants to one or more users

If, on the other hand, you have a task that is not met by these utilities or
one that can be met if you combined one or more of the utilities or even parts
of the utilities, you can easily form your own custom solution. In the
following sections, we present an example of a custom utility. First, we
examine what the mysql.utilities module library has available.

The MySQL Utilities Library
---------------------------

There are a number of modules in the mysql.utilities sub folders that provide
abstracts of many of the operations for a MySQL database system. The following
briefly summarizes the modules in the common sub folder.

* database.py : abstraction of a MySQL database (e.g. exists, get objects, etc.)
* format.py : screen formatting module
* options.py : common setup options for utilities
* rpl.py : abstraction of the replicate operations
* server.py : abstraction of a MySQL server (e.g. connect, execute
  queries, etc.)
* table.py : abstraction of a MySQL table (e.g. exists, get indexes, etc.)
* tools.py : helper module designed to locate mysql tools (e.g. find
  mysql monitor)
* user.py : abstraction of a MySQL user (e.g. exists, get grants, etc.)

Additionally, each of the scripts has an associated module located in the
mysql.utilities.command folder whereby the script itself is responsible for
managing the parameters, options, and error handling. The command module
executes the bulk of the operation. All of the MySQL utilities are constructed
this way on purpose to provide the ability to use the utilities via another
Python code module or script. The command modules are named appropriately for
their task and each is fully documented.

Now that you are familiar with the MySQL utilities and the supporting library
modules, let us take a look at an example of combining some of these modules to
solve a problem.

Example
-------

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
        'conn_vals' : conn,
        'role'      : "source",
    }
    server1 = Server(server_options)
    try:
        server1.connect()
    except MySQLUtilError, e:
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
    except exception.MySQLUtilError, e:
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
    except exception.MySQLUtilError, e:
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
        except exception.MySQLUtilError, e:
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
