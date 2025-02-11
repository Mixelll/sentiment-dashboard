import os
from s3_manager import S3Manager, S3Config
from ec2_manager import EC2Manager, EC2Config
from rds_manager import RDSManager, RDSConfig
from route53_manager import Route53Manager, Route53Config, Route53DomainsConfig
from parameter_store_manager import ParameterStoreManager
from aws_credentials import aws as aws_credentials_source, ec2 as ec2_credentials_source, rds as rds_credentials_source, personal_contact_info
from credentials import github as github_cred, local_db as local_db_cred
from project_classes import DataTransferConfig, LocalDumpRestoreConfig


class HybridWebsiteConfig:
    def __init__(self, s3_config, ec2_config, rds_config, route53_config=None, route53domains_config=None):
        self.s3_config = s3_config
        self.ec2_config = ec2_config
        self.rds_config = rds_config
        self.route53_config = route53_config
        self.route53domains_config = route53domains_config


class HybridWebsiteManager:
    def __init__(self, config, aws_credentials=None):
        self.config = config
        self.s3_manager = S3Manager(config.s3_config, aws_credentials)
        self.ec2_manager = EC2Manager(config.ec2_config, aws_credentials)
        self.rds_manager = RDSManager(config.rds_config, aws_credentials, ec2_manager=self.ec2_manager, local_db_credentials=local_db_cred, local_dump_restore_config_versions=local_dump_restore_config)
        self.route53_manager = Route53Manager(config.route53_config, aws_credentials, domain_config=self.config.route53domains_config)
        self.parameter_store_manager = ParameterStoreManager(aws_credentials=aws_credentials, region_name=config.ec2_config.region)

    def full_flow(self, full_flow_defaults=False, s3=True, ec2=True, rds=True, route53=True, parameter_store=True,  s3_full=False, ec2_full=False, rds_full=False, route53_full=False, data_transfer_config=None, **kwargs):
        kfn = lambda name, default=None: kwargs.get(name, default)
        d = full_flow_defaults
        # Setup S3
        if s3:
            s = s3_full
            print("Setting up S3 bucket...")
            self.s3_manager.full_flow(modify_existing_bucket=kfn('modify_existing_bucket', d or s), delete_files=kfn('delete_files', d or s),
                                      sync_files=kfn('sync_files', d or s), delete_existing_bucket=kfn('delete_existing_bucket', False),
                                      dist_directory=dist_path)

        # Setup EC2
        if ec2:
            e = ec2_full
            print("Setting up EC2 instance...")
            instance_id = self.ec2_manager.full_flow(create_instance=kfn('create_instance', d or e), force_ssh=kfn('force_ssh', d or e),
                                                     setup_security=kfn('setup_security', d or e), security_mode=kfn('security_mode'),
                                                     setup_iam=kfn('setup_iam', d or e), installs=kfn('installs', d or e),
                                                     clone_git=kfn('clone_git', d or e), start_service=kfn('start_service', d or e),)
            print(f"EC2 instance setup completed with ID: {instance_id}")

        # Setup RDS
        if rds:
            r = rds_full
            print("Setting up RDS instance...")
            db_instance_id = self.rds_manager.full_flow(create_instance=kfn('create_instance', d or r),
                                                        setup_security=kfn('setup_security', d or r), security_mode=kfn('security_mode'),
                                                        transfer_data=kfn('transfer_data', d or r), transfer_config=data_transfer_config)
            print(f"RDS instance setup completed with ID: {db_instance_id}")

        # Setup Route 53
        if route53:
            r53 = route53_full
            print("Setting up Route 53...")
            self.route53_manager.full_flow(register_domain=kfn('register_domain', d or r53), setup_dns=kfn('register_domain', d or r53))

        if parameter_store:
            # Use Parameter Store to manage environment variables for the service
            parameters_to_update = [
                {'name': '/hybrid/config/db_host', 'value': rds_credentials_source.host, 'description': 'Database host'},
                {'name': '/hybrid/config/db_port', 'value': rds_credentials_source.port, 'description': 'Database port'},
                {'name': '/hybrid/config/db_user', 'value': rds_credentials_source.master_username, 'description': 'Database user'},
                {'name': '/hybrid/config/db_password', 'value': rds_credentials_source.master_user_password, 'description': 'Database password'},
                {'name': '/hybrid/config/db_name', 'value': rds_credentials_source.dbname, 'description': 'Database name'},
            ]
            self.parameter_store_manager.create_or_update_parameters(parameters_to_update)


if __name__ == '__main__':
    project_name = 'sentiment-dashboard'
    my_region = 'il-central-1'
    instance_type = 't3.micro'
    security_group_name = 'rds_security_group'
    vpc_id = 'vpc-09ee6ff76373d150f'
    domain_name = 'michaelleitsin.com'
    s3_bucket_name = domain_name
    cwd = os.getcwd()
    cwd = '\\'.join(cwd.split('\\')[:-1]) if cwd.split('\\')[-1] == 'manage' else cwd  # If the current working directory is 'manage', go one level up
    dist_path = cwd + fr'\front\{project_name}\dist\{project_name}\browser'

    ec2_user = 'ec2-user'
    bash_bin_path = '/usr/bin/bash'
    back_path_linux = '/home/ec2-user/sentiment-dashboard/back'
    service_name = 'sentiment_db'
    service_file_path = f'/etc/systemd/system/{service_name}.service'

    # Define S3 Config
    s3_config = S3Config(
        region=my_region,
        bucket_name=s3_bucket_name,
        static_website_hosting=True,
        enable_public_access=True,
        setup_commands=[
            # Add any additional setup commands here
        ],
        dist_directory=dist_path,
    )

    # source ~/.bashrc &&
    service_content = f"""
        [Unit]
        Description={service_name}
    
        [Service]
        ExecStart={bash_bin_path} -c 'exec sudo waitress-serve --host=0.0.0.0 --port=80 app:app'
        WorkingDirectory={back_path_linux}
        Restart=always
        User={ec2_user}
        Environment=PYTHONUNBUFFERED=1

    
        [Install]
        WantedBy=multi-user.target
        """

    # Environment=DB_HOST={rds_credentials_source.host}
    # Environment=DB_PORT={rds_credentials_source.port}
    # Environment=DB_USER={rds_credentials_source.master_username}
    # Environment=DB_PASSWORD={rds_credentials_source.master_user_password}
    # Environment=DB_NAME={rds_credentials_source.dbname}

    # Define EC2 Config
    ec2_setup_commands = [
        # "sudo yum update -y",
        # "sudo dnf update -y",
        # # "sudo yum install -y httpd24 php70",
        # # "sudo service httpd start",
        # "sudo yum install -y python3",
        # "sudo yum install -y git",  # Added installation of git
        # "sudo yum install -y nc",
        # "sudo dnf install postgresql15.x86_64 postgresql15-server -y",
        # "sudo postgresql-setup initdb",
        # "sudo service postgresql start",
        # "sudo systemctl enable postgresql",
        # "sudo pip3 install boto3",
        # fr"echo 'export DB_HOST={rds_credentials_source.host}' >> ~/.bashrc",
        # fr"echo 'export DB_PORT={rds_credentials_source.port}' >> ~/.bashrc",
        # fr"echo 'export DB_USER={rds_credentials_source.master_username}' >> ~/.bashrc",
        # fr"echo 'export DB_PASSWORD={rds_credentials_source.master_user_password}' >> ~/.bashrc",
        # fr"echo 'export DB_NAME={rds_credentials_source.dbname}' >> ~/.bashrc",
        # "source ~/.bashrc",
        f'echo "{service_content.strip()}" | sudo tee {service_file_path} > /dev/null',
        # 'sudo systemctl daemon-reload',
    ]

    start_service_commands = [
        'sudo systemctl daemon-reload',
        'sudo systemctl restart sentiment_db',
        'sudo systemctl enable sentiment_db'
    ]

    git_commands = [
        f"sudo rm -rf {project_name}",  # Remove the existing project directory
        fr"git clone --no-checkout https://{github_cred.username}:{github_cred.token}@github.com/{github_cred.username}/{project_name}.git",
        f"cd {project_name}",
        "git sparse-checkout init --cone",
        "git sparse-checkout set back",
        "git checkout main",
        "cd back",
        # "pip3 install -r requirements.txt"
    ]

    ec2_permissions = [
        {'IpProtocol': 'tcp', 'FromPort': 80, 'ToPort': 80, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
        {'IpProtocol': 'tcp', 'FromPort': 22, 'ToPort': 22, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}
    ]

    ec2_config = EC2Config(
        region=my_region,
        security_group_name=security_group_name,
        permissions=ec2_permissions,
        key_name=None,
        instance_type=instance_type,
        ami_id=None,
        vpc_id=vpc_id,
        subnet_id=None,
        setup_commands=ec2_setup_commands,
        git_commands=git_commands,
        start_service_commands=start_service_commands,
        user=ec2_user,
        key_path=ec2_credentials_source.key_path,
        instance_id=ec2_credentials_source.instance_id  # Provide an existing instance ID if available
    )

    # Define RDS Config
    rds_permissions = [
        {'IpProtocol': 'tcp', 'FromPort': 5432, 'ToPort': 5432, 'IpRanges': [{'CidrIp': '172.31.0.0/16'}]}  # PostgreSQL - vpc CidrIp block
    ]

    rds_config = RDSConfig(
        region=my_region,
        db_instance_identifier=rds_credentials_source.db_identifier,
        db_instance_class=instance_type,
        engine=rds_credentials_source.engine,
        master_username=rds_credentials_source.master_username,
        master_user_password=rds_credentials_source.master_user_password,
        db_name=None,
        vpc_id=vpc_id,
        subnet_group_name='default',
        security_group_name=security_group_name,
        permissions=rds_permissions
    )

    data_transfer_config_ = DataTransferConfig(
        source_table='all_news',
        source_schema='news_data',
        columns=['title', 'url', 'time_published', 'authors', 'summary', 'banner_image', 'source', 'category_within_source', 'topics', 'overall_sentiment_score',
                 'overall_sentiment_label', 'ticker_sentiment'],
        temp_table_name='all_news',
        temp_schema='public',  # Optional, Better use 'public'
    )

    # Assuming the local databases have the same connection details
    local_dump_restore_config = LocalDumpRestoreConfig(
        source_port=5432,
        target_port=5433,
        pg_path=r"C:\Program Files\PostgreSQL\16\bin",
        output_pg_path=r"C:\Program Files\PostgreSQL\15\bin"
    )

    route53_config = Route53Config(
        region_name=my_region,
        hosted_zone_id="Z09640613K4A3MN55U7GU",
        domain_name=domain_name,
        s3_bucket_name=s3_bucket_name
    )

    route53_domains_config = Route53DomainsConfig(
        domain_name=domain_name,
        contact_info=personal_contact_info
    )

    # Create Hybrid Website Config
    hybrid_config = HybridWebsiteConfig(s3_config, ec2_config, rds_config, route53_config, route53_domains_config)

    # Initialize and run Hybrid Website Manager
    hybrid_manager = HybridWebsiteManager(hybrid_config, aws_credentials=aws_credentials_source)
    hybrid_manager.full_flow(s3=True, s3_full=False, delete_files=True, sync_files=True, modify_existing_bucket=False, delete_existing_bucket=False,
                             ec2=False, ec2_full=False, force_ssh=True, installs=False, clone_git=False, start_service=True, setup_iam=False,
                             rds=False, rds_full=False, transfer_data=True, data_transfer_config=data_transfer_config_,
                             route53=False, route53_full=False,
                             parameter_store=False,
                             setup_security=False, security_mode=None)
