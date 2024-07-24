import boto3
import json
import subprocess
from botocore.exceptions import ClientError


class AWSConfig:
    def __init__(self, region, vpc_id, subnet_id, subnet_group_name):
        self.region = region
        self.vpc_id = vpc_id
        self.subnet_id = subnet_id
        self.subnet_group_name = subnet_group_name


class S3Config(AWSConfig):
    def __init__(self, region, vpc_id, subnet_id, subnet_group_name, bucket_name, static_website_hosting, block_public_access, website_index_document,
                 website_error_document):
        super().__init__(region, vpc_id, subnet_id, subnet_group_name)
        self.bucket_name = bucket_name
        self.static_website_hosting = static_website_hosting
        self.block_public_access = block_public_access
        self.website_index_document = website_index_document
        self.website_error_document = website_error_document


class EC2Config(AWSConfig):
    def __init__(self, region, vpc_id, subnet_id, subnet_group_name, security_group_name, key_name, instance_type, ami_id, ec2_setup_commands):
        super().__init__(region, vpc_id, subnet_id, subnet_group_name)
        self.security_group_name = security_group_name
        self.key_name = key_name
        self.instance_type = instance_type
        self.ami_id = ami_id
        self.ec2_setup_commands = ec2_setup_commands


class RDSConfig(AWSConfig):
    def __init__(self, region, vpc_id, subnet_id, subnet_group_name, security_group_name, db_instance_identifier, db_instance_class, engine, master_username,
                 master_user_password, db_name):
        super().__init__(region, vpc_id, subnet_id, subnet_group_name)
        self.security_group_name = security_group_name
        self.db_instance_identifier = db_instance_identifier
        self.db_instance_class = db_instance_class
        self.engine = engine
        self.master_username = master_username
        self.master_user_password = master_user_password
        self.db_name = db_name


class AWSSetup:
    def __init__(self, s3_config, ec2_config, rds_config, ec2_sg_rules, rds_sg_rules, aws_credentials=None):
        self.s3_config = s3_config
        self.ec2_config = ec2_config
        self.rds_config = rds_config
        self.ec2_sg_rules = ec2_sg_rules
        self.rds_sg_rules = rds_sg_rules

        if aws_credentials:
            self.s3_client = boto3.client(
                's3',
                region_name=s3_config.region,
                aws_access_key_id=aws_credentials.access_key,
                aws_secret_access_key=aws_credentials.secret_key
            )
            self.ec2_client = boto3.client(
                'ec2',
                region_name=ec2_config.region,
                aws_access_key_id=aws_credentials.access_key,
                aws_secret_access_key=aws_credentials.secret_key
            )
            self.rds_client = boto3.client(
                'rds',
                region_name=rds_config.region,
                aws_access_key_id=aws_credentials.access_key,
                aws_secret_access_key=aws_credentials.secret_key
            )
        else:
            self.s3_client = boto3.client('s3', region_name=s3_config.region)
            self.ec2_client = boto3.client('ec2', region_name=ec2_config.region)
            self.rds_client = boto3.client('rds', region_name=rds_config.region)

    def setup_s3(self):
        try:
            self.s3_client.head_bucket(Bucket=self.s3_config.bucket_name)
            print(f"Using existing S3 bucket: {self.s3_config.bucket_name}")
        except ClientError:
            self.s3_client.create_bucket(
                Bucket=self.s3_config.bucket_name,
                CreateBucketConfiguration={'LocationConstraint': self.s3_config.region},
            )
            print(f"S3 bucket {self.s3_config.bucket_name} created successfully in {self.s3_config.region}")

            if self.s3_config.static_website_hosting:
                self.s3_client.put_bucket_website(
                    Bucket=self.s3_config.bucket_name,
                    WebsiteConfiguration={
                        'IndexDocument': {'Suffix': self.s3_config.website_index_document},
                        'ErrorDocument': {'Key': self.s3_config.website_error_document}
                    }
                )
                print(f"Static website hosting enabled for bucket {self.s3_config.bucket_name}")

            if self.s3_config.block_public_access:
                self.s3_client.put_public_access_block(
                    Bucket=self.s3_config.bucket_name,
                    PublicAccessBlockConfiguration={
                        'BlockPublicAcls': True,
                        'IgnorePublicAcls': True,
                        'BlockPublicPolicy': True,
                        'RestrictPublicBuckets': True
                    }
                )
                print(f"Public access blocked for bucket {self.s3_config.bucket_name}")

            bucket_policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Sid": "PublicReadGetObject",
                        "Effect": "Allow",
                        "Principal": "*",
                        "Action": "s3:GetObject",
                        "Resource": f"arn:aws:s3:::{self.s3_config.bucket_name}/*"
                    }
                ]
            }

            self.s3_client.put_bucket_policy(
                Bucket=self.s3_config.bucket_name,
                Policy=json.dumps(bucket_policy)
            )
            print(f"Bucket policy set for {self.s3_config.bucket_name}")

    def setup_security_group(self, security_group_name, description):
        try:
            response = self.ec2_client.describe_security_groups(GroupNames=[security_group_name])
            security_group_id = response['SecurityGroups'][0]['GroupId']
            print(f"Using existing Security Group: {security_group_name} with ID: {security_group_id}")
        except ClientError as e:
            if 'InvalidGroup.NotFound' in str(e):
                response = self.ec2_client.create_security_group(
                    GroupName=security_group_name,
                    Description=description,
                    VpcId=self.ec2_config.vpc_id
                )
                security_group_id = response['GroupId']
                print(f"Security Group {security_group_name} created with ID: {security_group_id}")
            else:
                raise
        return security_group_id

    def add_security_group_rules(self, security_group_id, ip_permissions, mode='add'):
        if mode == 'add':
            self.ec2_client.authorize_security_group_ingress(
                GroupId=security_group_id,
                IpPermissions=ip_permissions
            )
        elif mode == 'remove':
            self.ec2_client.revoke_security_group_ingress(
                GroupId=security_group_id,
                IpPermissions=ip_permissions
            )
        elif mode == 'replace':
            self.ec2_client.update_security_group_rule_descriptions_ingress(
                GroupId=security_group_id,
                IpPermissions=ip_permissions
            )
        print(f"Rules {mode}d to Security Group {security_group_id}")

    def setup_ec2(self, instance_id=None):
        ec2_sg_id = self.setup_security_group(self.ec2_config.security_group_name, 'EC2 Security Group')
        self.add_security_group_rules(ec2_sg_id, self.ec2_sg_rules, mode='add')

        if instance_id:
            try:
                self.ec2_client.describe_instances(InstanceIds=[instance_id])
                print(f"Using existing EC2 instance: {instance_id}")
            except ClientError as e:
                if 'InvalidInstanceID.NotFound' in str(e):
                    print(f"Instance ID {instance_id} not found. Creating a new instance...")
                    instance_id = self.create_ec2_instance(ec2_sg_id)
        else:
            instance_id = self.create_ec2_instance(ec2_sg_id)
        return instance_id

    def create_ec2_instance(self, ec2_sg_id):
        response = self.ec2_client.run_instances(
            ImageId=self.ec2_config.ami_id,
            InstanceType=self.ec2_config.instance_type,
            KeyName=self.ec2_config.key_name,
            SecurityGroupIds=[ec2_sg_id],
            SubnetId=self.ec2_config.subnet_id,
            MinCount=1,
            MaxCount=1
        )
        instance_id = response['Instances'][0]['InstanceId']
        print(f"EC2 instance created with ID: {instance_id}")
        return instance_id

    def setup_rds(self):
        rds_sg_id = self.setup_security_group(self.rds_config.security_group_name, 'RDS Security Group')
        self.add_security_group_rules(rds_sg_id, self.rds_sg_rules, mode='add')

        try:
            self.rds_client.describe_db_instances(DBInstanceIdentifier=self.rds_config.db_instance_identifier)
            print(f"Using existing RDS instance: {self.rds_config.db_instance_identifier}")
        except ClientError as e:
            if 'DBInstanceNotFound' in str(e):
                self.rds_client.create_db_instance(
                    DBInstanceIdentifier=self.rds_config.db_instance_identifier,
                    DBInstanceClass=self.rds_config.db_instance_class,
                    Engine=self.rds_config.engine,
                    MasterUsername=self.rds_config.master_username,
                    MasterUserPassword=self.rds_config.master_user_password,
                    DBName=self.rds_config.db_name,
                    VpcSecurityGroupIds=[rds_sg_id],
                    DBSubnetGroupName=self.rds_config.subnet_group_name,
                    AllocatedStorage=20,
                    BackupRetentionPeriod=7,
                    MultiAZ=False,
                    EngineVersion='13.3',  # Example for PostgreSQL
                    PubliclyAccessible=False
                )
                print(f"RDS instance {self.rds_config.db_instance_identifier} created")
