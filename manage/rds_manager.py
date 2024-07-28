import os
import subprocess
import boto3
from botocore.exceptions import ClientError
from aws_credentials import aws as aws_credentials_source, rds as rds_credentials_source
from local_postgres_manager import LocalPostgresManager


class RDSConfig:
    def __init__(self, region, db_instance_identifier, db_instance_class, engine, master_username, master_user_password, db_name, vpc_id, subnet_group_name, security_group_name, permissions):
        self.region = region
        self.db_instance_identifier = db_instance_identifier
        self.db_instance_class = db_instance_class
        self.engine = engine
        self.master_username = master_username
        self.master_user_password = master_user_password
        self.db_name = db_name
        self.vpc_id = vpc_id
        self.subnet_group_name = subnet_group_name
        self.security_group_name = security_group_name
        self.permissions = permissions


class RDSManager:
    def __init__(self, config, aws_credentials=None, ec2_client=None, ec2_manager=None, local_db_credentials=None, local_dump_restore_config_versions=None):
        self.config = config
        self.local_db_credentials = local_db_credentials
        self.local_db_manager = LocalPostgresManager(self.local_credentials_to_db_config(local_db_credentials), local_dump_restore_config_versions.__dict__) if local_db_credentials else None
        self.rds_client = boto3.client(
            'rds',
            region_name=config.region,
            aws_access_key_id=aws_credentials.access_key if aws_credentials else None,
            aws_secret_access_key=aws_credentials.secret_key if aws_credentials else None
        )
        self.ec2_client = ec2_client if ec2_client else (ec2_manager.ec2_client if ec2_manager else boto3.client(
            'ec2',
            region_name=config.region,
            aws_access_key_id=aws_credentials.access_key if aws_credentials else None,
            aws_secret_access_key=aws_credentials.secret_key if aws_credentials else None
        ))
        self.ec2_manager = ec2_manager

    def full_flow(self, setup_security=False, security_mode=None, create_instance=True, transfer_data=False, transfer_config=None):
        """Complete flow for setting up an RDS instance."""
        security_group_id = self.get_or_create_security_group()
        if setup_security:
            self.setup_security_group(security_group_id, mode=security_mode)
            self.add_security_group_to_rds(security_group_id)
        db_instance_id = self.create_db_instance(create_instance=create_instance)
        if transfer_data:
            self.transfer_data(transfer_config)
        return db_instance_id

    @staticmethod
    def local_credentials_to_db_config(local_db_credentials):
        """Convert SQLCredentials to a simpler db_config dictionary for local database operations."""
        attr_lmbd = lambda attr, default=None: getattr(local_db_credentials, attr) if hasattr(local_db_credentials, attr) else default
        if local_db_credentials:
            return {
                'dbname': local_db_credentials.dbname,
                'user': local_db_credentials.user,
                'password': local_db_credentials.password,
                'host': attr_lmbd('host', 'localhost'),  # Assuming the local database runs on the same machine
                'port': attr_lmbd('port', 5432),  # Default PostgreSQL port
                'pg_path': attr_lmbd('pg_path'),
            }
        else:
            print("Local database credentials are not set.")
            return None

    def get_rds_db_url(self):
        """Retrieve the RDS database URL for connection."""
        rds_db_config = self.get_rds_db_config()
        return f"postgresql://{rds_db_config['user']}:{rds_db_config['password']}@{rds_db_config['host']}/{rds_db_config['dbname']}"

    def transfer_data(self, transfer_config, public=False):
        """Transfers specified columns from a local table to an RDS instance using the provided configuration."""
        self.local_db_manager.create_temp_table(
            transfer_config.source_table,
            transfer_config.columns,
            transfer_config.temp_table_name,
            source_schema=transfer_config.source_schema,
            temp_schema=transfer_config.temp_schema
        )
        table_name = transfer_config.temp_table_name
        schema = transfer_config.temp_schema

        dump_file_path = f"/tmp/{table_name}.dump" if os.name == 'posix' else fr"tmp\{table_name}.dump"
        new_version_dict = self.local_db_manager.pg_dump_restore_between_versions(table_name, schema=schema)
        new_port = new_version_dict.get('port')
        new_pg_path = new_version_dict.get('pg_path')
        full_dump_path = self.local_db_manager.dump_table(table_name, dump_file_path, schema=schema, port=new_port, pg_path=new_pg_path)
        rds_db_url = self.get_rds_db_url()
        self.restore_table_to_rds(full_dump_path, table_name=table_name, public=public, rds_db_url=rds_db_url)
        self.verify_data_transfer_via_ssh(table_name, schema=schema, rds_db_url=rds_db_url)

    def transfer_pg_dump_to_rds_ec2_ssh(self, local_dump_path, rds_db_url):
        """ Transfer the PostgreSQL dump file from local to RDS via the EC2 instance. """

        # Step 1: Transfer the dump file to the EC2 instance
        self.ec2_manager.upload_file_to_ec2(local_dump_path, '/tmp/sentiment_temp.dump')
        # Step 2: Restore the dump file to the RDS instance from the EC2 instance
        # schema_option = f"--schema={schema}" if schema else ""
        restore_command = f"pg_restore -d {rds_db_url} /tmp/sentiment_temp.dump"
        self.ec2_manager._run_commands_via_ssh([restore_command])

    def restore_table_to_rds(self, dump_file_path, table_name=None, schema='public', public=False, rds_db_url=None, drop_if_exists=True):
        """Restores a table dump to the RDS database, considering schema and drops the table if it exists."""
        if not rds_db_url:
            rds_db_url = self.get_rds_db_url()
        if drop_if_exists:
            drop_table_command = f"psql {rds_db_url} -c \"DROP TABLE IF EXISTS {schema}.{table_name} CASCADE;\""
            # _drop_table_command = f'"DROP TABLE IF EXISTS {schema}.{table_name} CASCADE;"'
            # drop_table_command = [
            #     "psql",
            #     rds_db_url,
            #     "-c",
            #     _drop_table_command
            # ]
            try:
                # Drop the table if it exists
                print("Executing command (subprocess):", drop_table_command)
                subprocess.run(drop_table_command, shell=False, check=True)
                print(f"Table {schema}.{table_name} dropped if it existed.")
            except subprocess.CalledProcessError as e:
                print(f"Failed to drop table {schema}.{table_name}. Error: {e.stderr}")

        if public:
            restore_command = f"pg_restore -d {rds_db_url} {dump_file_path}"
            try:
                subprocess.run(restore_command, shell=True, check=True)
                print(f"Restored {dump_file_path} to RDS")
            except subprocess.CalledProcessError as e:
                print(f"Failed to restore {dump_file_path} to RDS Error: {e.stderr}")
        else:
            self.transfer_pg_dump_to_rds_ec2_ssh(dump_file_path, rds_db_url)
        print(f"Restored from {dump_file_path} to RDS")

    def verify_data_transfer_via_ssh(self, table, rds_db_url=None, schema='public'):
        """Verify the data transfer by checking the table or schema in the RDS via SSH."""
        if not rds_db_url:
            rds_db_url = self.get_rds_db_url()
        verification_commands = []
        if table:
            verification_commands.append(
                f'psql {rds_db_url} -c "SELECT COUNT(*) FROM {schema}.{table};"'
            )
        else:
            verification_commands.append(
                f'psql {rds_db_url} -c "SELECT table_name FROM information_schema.tables WHERE table_schema = \'{schema}\';"'
            )

        self.ec2_manager._run_commands_via_ssh(verification_commands)

    def get_rds_db_config(self):
        db_config = {
            'dbname': self.config.db_name if self.config.db_name else "postgres",
            'user': self.config.master_username,
            'password': self.config.master_user_password,
            'host': self.fetch_rds_endpoint(),
            'port': 5432
        }
        return db_config

    def fetch_rds_endpoint(self):
        try:
            response = self.rds_client.describe_db_instances(DBInstanceIdentifier=self.config.db_instance_identifier)
            if response['DBInstances']:
                return response['DBInstances'][0]['Endpoint']['Address']
            else:
                print("No RDS instances found for identifier.")
                return None
        except Exception as e:
            print(f"Error fetching RDS endpoint: {e}")
            return None

    def find_db_instance(self):
        """Find an existing RDS instance by identifier."""
        try:
            response = self.rds_client.describe_db_instances(DBInstanceIdentifier=self.config.db_instance_identifier)
            if response['DBInstances']:
                print(f"Found existing RDS instance: {self.config.db_instance_identifier}")
                return response['DBInstances'][0]
        except ClientError as e:
            if e.response['Error']['Code'] == 'DBInstanceNotFound':
                print(f"RDS instance {self.config.db_instance_identifier} not found.")
            else:
                print(f"Error describing RDS instance: {e}")
        return None

    def create_db_instance(self, create_instance=True):
        """Create an RDS instance with the given configuration."""
        existing_instance = self.find_db_instance()
        if existing_instance:
            return existing_instance['DBInstanceIdentifier']
        if not create_instance:
            return None
        try:
            response = self.rds_client.create_db_instance(
                DBInstanceIdentifier=self.config.db_instance_identifier,
                DBInstanceClass=self.config.db_instance_class,
                Engine=self.config.engine,
                MasterUsername=self.config.master_username,
                MasterUserPassword=self.config.master_user_password,
                DBName=self.config.db_name,
                VpcSecurityGroupIds=[self.get_or_create_security_group()],
                DBSubnetGroupName=self.config.subnet_group_name,
                AllocatedStorage=20,  # Fixed size for example, adjust as needed
                MultiAZ=False,
                PubliclyAccessible=True
            )
            print(f"RDS instance created: {response['DBInstance']['DBInstanceIdentifier']}")
            return response['DBInstance']['DBInstanceIdentifier']
        except ClientError as e:
            print(f"Failed to create RDS instance: {e}")
            return None

    def get_or_create_security_group(self):
        """Retrieve or create a security group for the RDS instance."""
        try:
            security_group_id = self.ec2_manager.create_or_get_security_group(self.config.security_group_name, description='', vpc_id=self.config.vpc_id)
            return security_group_id
            # response = self.ec2_client.describe_security_groups(Filters=[{'Name': 'group-name', 'Values': [self.config.security_group_name]}])
            # if response['SecurityGroups']:
            #     security_group_id = response['SecurityGroups'][0]['GroupId']
            #     print(f"Using existing security group: {security_group_id}")
            # else:
            #     sg_response = self.ec2_client.create_security_group(
            #         GroupName=self.config.security_group_name,
            #         Description='RDS db security group',
            #         VpcId=self.config.vpc_id
            #     )
            #     security_group_id = sg_response['GroupId']
            #     print(f"Created security group: {security_group_id}")
            #     self.setup_security_group(security_group_id, mode='add')
            # return security_group_id
        except ClientError as e:
            print(f"Failed to create or retrieve security group: {e}")
            return None

    def setup_security_group(self, security_group_id, permissions=None, mode='add'):
        """Set up the security group rules."""
        if mode is None:
            mode = 'add'
        permissions = permissions if permissions else self.config.permissions

        if mode == 'replace':
            # Revoke all existing rules
            try:
                existing_permissions = self.ec2_client.describe_security_groups(GroupIds=[security_group_id])['SecurityGroups'][0]['IpPermissions']
                if existing_permissions:
                    self.ec2_client.revoke_security_group_ingress(GroupId=security_group_id, IpPermissions=existing_permissions)
                    print('Existing security group ingress rules revoked.')
            except ClientError as e:
                print(f'Error revoking existing security group ingress rules: {e}')

        # Authorize new rules
        if mode in ['add', 'replace']:
            try:
                self.ec2_client.authorize_security_group_ingress(
                    GroupId=security_group_id,
                    IpPermissions=permissions
                )
                print('Security group ingress rules set successfully.')
            except ClientError as e:
                print(f'Error setting security group ingress rules: {e}')

    def add_security_group_to_rds(self, security_group_id):
        """Add a security group to an RDS instance."""
        db_instance_identifier  = self.config.db_instance_identifier
        try:
            response = self.rds_client.describe_db_instances(DBInstanceIdentifier=db_instance_identifier)
            current_security_groups = response['DBInstances'][0]['VpcSecurityGroups']
            current_security_group_ids = [sg['VpcSecurityGroupId'] for sg in current_security_groups]

            if security_group_id not in current_security_group_ids:
                current_security_group_ids.append(security_group_id)

            response = self.rds_client.modify_db_instance(
                DBInstanceIdentifier=db_instance_identifier,
                VpcSecurityGroupIds=current_security_group_ids,
                ApplyImmediately=True
            )

            print(f"Updated security groups for RDS instance '{db_instance_identifier}': {current_security_group_ids}")
            return response
        except ClientError as e:
            print(f"Failed to add security group to RDS instance: {e}")
            return None


if __name__ == '__main__':
    rds_permissions = [
        {'IpProtocol': 'tcp', 'FromPort': 5432, 'ToPort': 5432, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}  # PostgreSQL
    ]

    rds_config = RDSConfig(
        region='il-central-1',
        db_instance_identifier=rds_credentials_source.db_identifier,
        db_instance_class='db.t3.micro',
        engine='PostgreSQL',
        master_username=rds_credentials_source.master_username,
        master_user_password=rds_credentials_source.master_user_password,
        db_name=None,
        vpc_id='vpc-abc123',
        subnet_group_name='default',
        security_group_name='launch-wizard-1',
        permissions=rds_permissions
    )

    rds_manager = RDSManager(rds_config, aws_credentials=aws_credentials_source)
    rds_manager.full_flow(security_mode='add')
