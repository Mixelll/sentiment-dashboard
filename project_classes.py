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
    def __init__(self, instance_id: str = None, key_path: str = None):
        self.instance_id = instance_id
        self.key_path = key_path


class RDSCredentials:
    def __init__(self, db_identifier: str = None, master_username: str = None, master_user_password: str = None, host: str = None, port: int = None,
                 engine: str = None, dbname: str = None):
        self.db_identifier = db_identifier
        self.master_username = master_username
        self.master_user_password = master_user_password
        self.host = host
        self.port = port
        self.engine = engine
        self.dbname = dbname


class GitHubCredentials:
    def __init__(self, username: str = None, token: str = None):
        self.username = username
        self.token = token


class DataTransferConfig:
    def __init__(self, source_table, columns, temp_table_name, source_schema=None, temp_schema=None, pg_path=None):
        self.source_table = source_table
        self.columns = columns
        self.temp_table_name = temp_table_name
        self.source_schema = source_schema
        self.temp_schema = temp_schema
        self.pg_path = pg_path


class LocalDumpRestoreConfig:
    def __init__(self, source_port, target_port, pg_path=None, output_pg_path=None):
        self.source_port = source_port
        self.target_port = target_port
        self.pg_path = pg_path
        self.output_pg_path = output_pg_path

