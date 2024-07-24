class SQLCredentials:
    def __init__(self, dbname: str = None, user: str = None, password: str = None):
        self.dbname = dbname
        self.user = user
        self.password = password


class AWSCredentials:
    def __init__(self, access_key: str = None, secret_key: str = None):
        self.access_key = access_key
        self.secret_key = secret_key


class S3Credentials:
    def __init__(self, bucket_name: str = None):
        self.bucket_name = bucket_name


class EC2Credentials:
    def __init__(self, key_name: str = None):
        self.key_name = key_name


class RDSCredentials:
    def __init__(self, master_username: str = None, master_user_password: str = None):
        self.master_username = master_username
        self.master_user_password = master_user_password
