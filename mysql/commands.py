import MySQLdb, re

class proc:
    """Class for scanning the PROCESSLIST table."""
    def __init__(self, options):
        # Id, User, Host, db, Command, Time, State, Info
        self.__matches = 8 * [lambda x: True]
        if options.user:
            m = re.compile(options.user)
            self.__matches[1] = lambda s: m.match(s)


    def _match_row(self, row):
        if not row:
            return None
        for m,c in zip(self.__matches, row):
            # Here we should use MySQLdb.conversion instead of
            # converting (back) to a string
            if not m(str(c)):
                break
        else:
            self.__rows.append(row)  # All matched
            

    def _ask_one_server(self, host, user, port):
        conn = MySQLdb.connect(host=host, user=user)
        cursor = conn.cursor()
        cursor.execute("SHOW PROCESSLIST")
        while self._match_row(cursor.fetchone()):
            pass
        
    def execute(self, args):
        self.__rows = []
        for arg in args:
            m = re.match("(?:(\w+)@)?(\w+)(?:\:(\d+))?", arg)
            if m:
                user, host, port = m.groups()
                if port:
                    port = int(port)
                self._ask_one_server(host=host, user=user, port=port)
        return self.__rows
            
            
        


    


