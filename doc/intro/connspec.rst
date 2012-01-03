.. `connection specification`

Connection Parameters
=====================

When connecting to a server it is necessary to specify connection
parameters such as user, host, password, and maybe also port and
socket. 

Whenever connection parameters are required, they can be specified in
three different ways:

- As a dictionary containing the connection parameters.

- As a :ref:`connection specification` string, which is a string
  containing the connection parameters.

- As a :ref:`Server instance`.

When providing the connection parameters as a dictionary, the
parameters are passed unchanged to the connectors ``connect``
function. This enables you to pass on parameters not supported through
the other interfaces, but at least these parameters are supported:

_`user`
  The name of the user to connect as. If no user is supplied, the
  login name of the user, as returned by `getpass.getuser`_, will be
  used.

_`passwd`
  The password to use when connecting. If no password is supplied, the
  empty password is assumed.

_`host`
  The domain name of the host or the IP address. If no hostname is provided,
  'localhost' will be used. This field accepts hostnames, IPv4, and IPv6
  addresses. It also accepts quoted values which are not validated and passed
  directly to the calling methods. This enables users to specify host names and
  IP addresses that are outside of the supported validation mechanisms.
 

_`port`
  The port to use when connecting to the server. If no port is
  supplied, the default port 3306 is used (which is the default port
  for the MySQL server as well).

_`unix_socket`
  The socket to connect to (instead of using the host_ and port_
  above).

.. _`connection specification`:

Providing the connection parameters as a string requires the string to
have the format ``user:password@host:port:socket``, where some values
are optional. If a connection specification string is provided, it
will be parsed using the :ref:`options.parse_connection` function.

.. _`getpass.getuser`: http://docs.python.org/library/getpass.html#getpass.getuser

