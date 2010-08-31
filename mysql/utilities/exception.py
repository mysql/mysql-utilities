class OptionError(Exception):
    """
    Exception thrown when there either an option is missing or incorrect.
    """

    def __init__(self, msg):
        self.msg = msg


