from s3_manager import S3Manager, S3Config
from ec2_manager import EC2Manager, EC2Config
from rds_manager import RDSManager, RDSConfig
from aws_credentials import aws as aws_credentials_source
import os


class HybridWebsiteConfig:
    def __init__(self, s3_config, ec2_config, rds_config):
        self.s3_config = s3_config
        self.ec2_config = ec2_config
        self.rds_config = rds_config


class HybridWebsiteManager:
    def __init__(self, config, aws_credentials=None):
        self.config = config
        self.s3_manager = S3Manager(config.s3_config, aws_credentials)
        self.ec2_manager = EC2Manager(config.ec2_config, aws_credentials)
        self.rds_manager = RDSManager(config.rds_config, aws_credentials, ec2_client=self.ec2_manager.ec2_client)

    def full_flow(self):
        # Setup S3
        print("Setting up S3 bucket...")
        cwd = os.getcwd()
        project_name = 'sentiment-dashboard'
        dist_path = cwd + fr'\front\{project_name}\dist\{project_name}'
        self.s3_manager.full_flow(delete_files=True, modify_existing_bucket=True, sync_files=True, dist_directory=dist_path)

        # Setup EC2
        print("Setting up EC2 instance...")
        instance_id = self.ec2_manager.full_flow(create_instance=False, clone_git=False)
        print(f"EC2 instance setup completed with ID: {instance_id}")

        # Setup RDS
        print("Setting up RDS instance...")
        db_instance_id = self.rds_manager.full_flow(create_instance=False)
        print(f"RDS instance setup completed with ID: {db_instance_id}")


if __name__ == '__main__':
    # Define S3 Config
    s3_config = S3Config(
        region='us-west-2',
        bucket_name='mixel-sentiment-dash',
        static_website_hosting=True,
        enable_public_access=True,
        setup_commands=[
            # Add any additional setup commands here
        ]
    )

    # Define EC2 Config
    ec2_setup_commands = [
        "sudo yum update -y",
        # "sudo yum install -y httpd24 php70",
        # "sudo service httpd start",
        "sudo yum install -y python3",
        "sudo yum install -y git"  # Added installation of git
    ]

    git_commands = [
        f"rm -rf {project_name}",  # Remove the existing project directory
        fr"git clone --no-checkout https://{github_username}:{github_token}@github.com/{github_username}/{project_name}.git",
        f"cd {project_name}",
        "git sparse-checkout init --cone",
        "git sparse-checkout set back",
        "git checkout main"
    ]

    ec2_permissions = [
        {'IpProtocol': 'tcp', 'FromPort': 80, 'ToPort': 80, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
        {'IpProtocol': 'tcp', 'FromPort': 22, 'ToPort': 22, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}
    ]

    ec2_config = EC2Config(
        region='il-central-1',
        security_group_name='launch-wizard-1',
        permissions=ec2_permissions,
        key_name=None,
        instance_type='t3.micro',
        ami_id=None,
        vpc_id=None,
        subnet_id=None,
        setup_commands=ec2_setup_commands,
        git_commands=git_commands,
        key_path=ec2_key_path,
        instance_id=ec2_instance_id  # Provide an existing instance ID if available
    )

    # Define RDS Config
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

    # Create Hybrid Website Config
    hybrid_config = HybridWebsiteConfig(s3_config, ec2_config, rds_config)

    # Initialize and run Hybrid Website Manager
    hybrid_manager = HybridWebsiteManager(hybrid_config, aws_credentials=aws_credentials_source)
    hybrid_manager.full_flow()
