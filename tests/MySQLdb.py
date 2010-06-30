
"""
This is a fake MySQLdb that acts as a mock object.
"""

class Error(BaseException):
    "Base class for all exceptions in this package"
    pass

class OperationalError(Error):
    pass

def _userkey(user, password, host, port):
    # To be able to distinguish between non-existant and empty
    # passwords we always add quotes to the key if there really is a
    # password
    if password:
        password = "'" + password + "'"
    return "%s:%s@%s:%s" % (user, password, host, str(port))

class MockCursor:
    def __init__(self, result):
        self.__result = result

    def execute(self, stmt):
        self.__current = iter(self.__result[stmt.upper()])

    def __iter__(self):
        return self

    def next(self):
        return self.__current.next()

    def fetchone(self):
        try:
            return self.__current.next()
        except StopIteration:
            return None

class MockConnection:
    def __init__(self, user, password, host, port):
        self.user = user
        self.password = password
        self.host = host
        self.port = port
        self._result = {}

    def cursor(self):
        return MockCursor(self._result)

    def _key(self):
        "Get a unique key for the connection"
        return _userkey(self.user, self.password, self.host, self.port)

    def _store_result(self, command, resultset):
        self._result[command] = resultset

_connection = {}

def create_connection(user, password='', host="localhost", port=3306):
    "Create a new connection to be used as a mock connection"

    global _connection
    connection = MockConnection(user, password, host, port)
    _connection[connection._key()] = connection
    return connection 


def remove_connection(connection):
    global _connection
    del _connection[connection._key()]


def add_command_result(connection, command, resultset):
    global _connection
    _connection[connection._key()]._store_result(command.upper(), resultset)


def connect(user, password="", host="localhost", port=3306):
    "Mock connect function mimicing the real MySQLdb.connect."
    global _connection
    server_key = _userkey(user, password, host, port)
    try:
        return _connection[server_key]
    except KeyError:
        raise OperationalError, "Key: %s: Available: %s" % (server_key, _connection.keys())
