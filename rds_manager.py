import boto3
from botocore.exceptions import ClientError
from aws_credentials import aws as aws_credentials_source


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
    def __init__(self, config, aws_credentials=None, ec2_client=None):
        self.config = config
        self.rds_client = boto3.client(
            'rds',
            region_name=config.region,
            aws_access_key_id=aws_credentials.access_key if aws_credentials else None,
            aws_secret_access_key=aws_credentials.secret_key if aws_credentials else None
        )
        if ec2_client:
            self.ec2_client = ec2_client
        else:
            self.ec2_client = boto3.client(
                'ec2',
                region_name=config.region,
                aws_access_key_id=aws_credentials.access_key if aws_credentials else None,
                aws_secret_access_key=aws_credentials.secret_key if aws_credentials else None
            )

    def full_flow(self, security_mode='add'):
        """Complete flow for setting up an RDS instance."""
        security_group_id = self.get_or_create_security_group()
        self.setup_security_group(security_group_id, mode=security_mode)
        db_instance_id = self.create_db_instance()
        return db_instance_id

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

    def create_db_instance(self):
        """Create an RDS instance with the given configuration."""
        existing_instance = self.find_db_instance()
        if existing_instance:
            return existing_instance['DBInstanceIdentifier']

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
            response = self.ec2_client.describe_security_groups(Filters=[{'Name': 'group-name', 'Values': [self.config.security_group_name]}])
            if response['SecurityGroups']:
                security_group_id = response['SecurityGroups'][0]['GroupId']
                print(f"Using existing security group: {security_group_id}")
            else:
                sg_response = self.ec2_client.create_security_group(
                    GroupName=self.config.security_group_name,
                    Description='RDS db security group',
                    VpcId=self.config.vpc_id
                )
                security_group_id = sg_response['GroupId']
                print(f"Created security group: {security_group_id}")
                self.setup_security_group(security_group_id, mode='add')
            return security_group_id
        except ClientError as e:
            print(f"Failed to create or retrieve security group: {e}")
            return None

    def setup_security_group(self, security_group_id, permissions=None, mode='add'):
        """Set up the security group rules."""
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


if __name__ == '__main__':
    rds_permissions = [
        {'IpProtocol': 'tcp', 'FromPort': 5432, 'ToPort': 5432, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}  # PostgreSQL
    ]

    rds_config = RDSConfig(
        region='il-central-1',
        db_instance_identifier='postgres-sentiment',
        db_instance_class='db.t3.micro',
        engine='PostgreSQL',
        master_username=None,
        master_user_password=None,
        db_name='mydb',
        vpc_id='vpc-abc123',
        subnet_group_name='default',
        security_group_name='launch-wizard-1',
        permissions=rds_permissions
    )

    rds_manager = RDSManager(rds_config, aws_credentials=aws_credentials_source)
    rds_manager.full_flow(security_mode='add')
