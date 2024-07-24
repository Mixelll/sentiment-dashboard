import json
from aws_credentials import aws as aws_credentials, rds as rds_credentials
from config import AWSConfig, S3Config, EC2Config, RDSConfig
import json

# Load credentials and configurations from a JSON file or other secure storage
with open('credentials.json', 'r') as f:
    creds = json.load(f)


s3_credentials = S3Credentials(
    bucket_name=creds['s3']['bucket_name']
)

ec2_credentials = EC2Credentials(
    key_name=creds['ec2']['key_name']
)

rds_credentials = RDSCredentials(
    master_username=creds['rds']['master_username'],
    master_user_password=creds['rds']['master_user_password']
)

region = creds['config']['region']
vpc_id = creds['config']['vpc_id']
subnet_id = creds['config']['subnet_id']
subnet_group_name = creds['config']['subnet_group_name']

# Define security group rules
ec2_sg_rules = [
    {'IpProtocol': 'tcp', 'FromPort': 22, 'ToPort': 22, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},  # SSH
    {'IpProtocol': 'tcp', 'FromPort': 80, 'ToPort': 80, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},  # HTTP
    {'IpProtocol': 'tcp', 'FromPort': 443, 'ToPort': 443, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},  # HTTPS
]

rds_sg_rules = [
    {'IpProtocol': 'tcp', 'FromPort': 5432, 'ToPort': 5432, 'UserIdGroupPairs': [{'GroupId': None}]},  # PostgreSQL
]

# Define configurations
s3_config = S3Config(
    region=region,
    vpc_id=vpc_id,
    subnet_id=subnet_id,
    subnet_group_name=subnet_group_name,
    bucket_name=creds['s3']['bucket_name'],
    static_website_hosting=creds['s3']['static_website_hosting'],
    block_public_access=creds['s3']['block_public_access'],
    website_index_document=creds['s3']['website_index_document'],
    website_error_document=creds['s3']['website_error_document']
)

ec2_config = EC2Config(
    region=region,
    vpc_id=vpc_id,
    subnet_id=subnet_id,
    subnet_group_name=subnet_group_name,
    security_group_name=creds['ec2']['security_group_name'],
    key_name=creds['ec2']['key_name'],
    instance_type=creds['ec2']['instance_type'],
    ami_id=creds['ec2']['ami_id'],
    angular_app_name=creds['ec2']['angular_app_name']
)

rds_config = RDSConfig(
    region=region,
    vpc_id=vpc_id,
    subnet_id=subnet_id,
    subnet_group_name=subnet_group_name,
    security_group_name=creds['rds']['security_group_name'],
    db_instance_identifier=creds['rds']['db_instance_identifier'],
    db_instance_class=creds['rds']['db_instance_class'],
    engine='postgres',
    master_username=creds['rds']['master_username'],
    master_user_password=creds['rds']['master_user_password'],
    db_name=creds['rds']['db_name']
)

aws_setup = AWSSetup(s3_config, ec2_config, rds_config, ec2_sg_rules, rds_sg_rules, aws_credentials=aws_credentials)

# Setup S3, EC2, and RDS
aws_setup.setup_s3()
instance_id = aws_setup.setup_ec2()
aws_setup.setup_rds()
