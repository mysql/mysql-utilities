.. `connection specification`

Connection Parameters
=====================

To connect to a server, it is necessary to specify connection
parameters such as user name, host name, password, and perhaps also port or
socket. 

Whenever connection parameters are required, they can be specified
three different ways:

- As a dictionary containing the connection parameters.

- As a connection specification string containing the connection
  parameters.

- As a Server instance.

When providing the connection parameters as a dictionary, the
parameters are passed unchanged to the connector's ``connect``
function. This enables you to pass parameters not supported through
the other interfaces, but at least these parameters are supported:

_`user`
  The name of the user to connect as. The default if no user is supplied
  is login name of the user, as returned by `getpass.getuser`_.

_`passwd`
  The password to use when connecting. The default if no password is supplied
  is the empty password.

_`host`
  The domain name of the host or the IP address. The default iIf no host name
  is provided is 'localhost'. This field accepts host names, and IPv4 and IPv6
  addresses. It also accepts quoted values which are not validated and passed
  directly to the calling methods. This enables users to specify host names and
  IP addresses that are outside of the supported validation mechanisms.
 

_`port`
  The port to use when connecting to the server. The default if no port is
  supplied is 3306 (which is the default port for the MySQL server as well).

_`unix_socket`
  The socket to connect to (instead of using the host_ and port_ parameters).

.. _`connection specification`:

Providing the connection parameters as a string requires the string to
have the format ``user[:passwd]@host[:port][:socket]``, where some values
are optional. If a connection specification string is provided, it
is parsed using the options.parse_connection function.

.. _`getpass.getuser`: http://docs.python.org/library/getpass.html#getpass.getuser

