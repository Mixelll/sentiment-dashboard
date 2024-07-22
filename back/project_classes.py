class SQLCredentials:
    def __init__(self, dbname: str = None, user: str = None, password: str = None):
        self.dbname = dbname
        self.user = user
        self.password = password
