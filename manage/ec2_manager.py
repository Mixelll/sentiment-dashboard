import boto3
import paramiko
import time
from botocore.exceptions import ClientError
import json
from iam_manager import IAMManager
from aws_credentials import aws as aws_credentials_source, ec2 as ec2_credentials_source
from credentials import github as github_cred


class EC2Config:
    def __init__(self, region, security_group_name, permissions, key_name, instance_type, ami_id, vpc_id, subnet_id, setup_commands=(), git_commands=(), start_service_commands=(),
                 instance_id=None, user='ec2-user', public_dns_name=None, key_path=None):
        self.region = region
        self.security_group_name = security_group_name
        self.permission_rules = permissions
        self.key_name = key_name
        self.instance_type = instance_type
        self.ami_id = ami_id
        self.vpc_id = vpc_id
        self.subnet_id = subnet_id
        self.setup_commands = setup_commands
        self.git_commands = git_commands
        self.start_service_commands = start_service_commands
        self.instance_id = instance_id
        self.user = user
        self.public_dns_name = public_dns_name
        self.key_path = key_path


class EC2Manager:
    def __init__(self, config, aws_credentials=None, iam_manager=None):
        self.config = config
        self.ec2_client = boto3.client(
            'ec2',
            region_name=config.region,
            aws_access_key_id=aws_credentials.access_key if aws_credentials else None,
            aws_secret_access_key=aws_credentials.secret_key if aws_credentials else None
        )
        if aws_credentials:
            self.ssm_client = boto3.client(
                'ssm',
                region_name=config.region,
                aws_access_key_id=aws_credentials.access_key,
                aws_secret_access_key=aws_credentials.secret_key
            )
        else:
            self.ssm_client = boto3.client('ssm', region_name=config.region)
        self.iam_manager = iam_manager if iam_manager else IAMManager(aws_credentials)
        self.instance_id = config.instance_id
        if self.instance_id:
            self.wait_for_instance(self.instance_id, 'running')
            instance_info = self.check_instance_status(self.instance_id)
            self.config.public_dns_name = instance_info.get('PublicDnsName')

    def full_flow(self, setup_security=True, security_mode=None, create_instance=True, setup_iam=True, fallback_to_ssh=True, force_ssh=False, installs=True,
                  clone_git=True, start_service=True):
        sg_id = self.create_or_get_security_group(self.config.security_group_name)
        if setup_security:
            self.setup_security_group(sg_id, mode=security_mode)

        self.instance_id = self.setup_ec2(sg_id, create_instance=create_instance)

        if self.instance_id:
            if setup_iam:
                self.ensure_iam_roles()
                self.attach_iam_role(self.instance_id)
            self.wait_for_instance(self.instance_id, 'running')
            instance_info = self.check_instance_status(self.instance_id)
            self.config.public_dns_name = instance_info.get('PublicDnsName')
            if not force_ssh and not self.is_ssm_agent_online(self.instance_id):
                self.install_and_start_ssm_agent()
            if not force_ssh and self.is_ssm_agent_online(self.instance_id):
                if installs:
                    self.execute_commands(self.config.setup_commands, ssm=True)
                if clone_git:
                    self.clone_git_repository(ssm=True)
            elif fallback_to_ssh or force_ssh:
                if installs:
                    self.execute_commands(self.config.setup_commands)
                if clone_git:
                    self.clone_git_repository(sleep=10)
                if start_service:
                    self.execute_commands(self.config.start_service_commands, sleep=2)

        return self.instance_id

    @staticmethod
    def run_commands_via_ssh(public_dns_name, key_path, commands, sleep=None, chain=False, user='ec2-user'):
        """Executes commands on a remote server via SSH. Can execute commands individually or chain them together."""
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            ssh_client.connect(hostname=public_dns_name, username=user, key_filename=key_path)

            if chain:
                # Combine commands into a single command separated by '&&' to ensure each command must succeed before the next runs
                chained_command = ' && '.join(commands)
                commands = [chained_command]  # Replace the list of commands with the single chained command

            for command in commands:
                print(f"Running command: {command}")
                stdin, stdout, stderr = ssh_client.exec_command(command)
                # Optionally sleep between commands when not chaining
                if sleep and not chain:
                    time.sleep(sleep)
                # Output from commands
                print(stdout.read().decode())
                print(stderr.read().decode())

            ssh_client.close()
        except Exception as e:
            print(f"Failed to run commands via SSH: {e}")

    def run_commands_via_ssh_(self, commands, sleep=None, chain=False):
        return self.run_commands_via_ssh(self.config.public_dns_name, self.config.key_path, commands, sleep, chain, user=self.config.user)

    def create_or_get_security_group(self, security_group_name=None, description=None, vpc_id=None):
        security_group_name = security_group_name if security_group_name else self.config.security_group_name
        description = description if description else f"Security Group for {security_group_name}"
        vpc_id = vpc_id if vpc_id else self.config.vpc_id
        try:
            response = self.ec2_client.describe_security_groups(GroupNames=[security_group_name])
            if response['SecurityGroups']:
                security_group_id = response['SecurityGroups'][0]['GroupId']
                print(f'Using existing Security Group: {security_group_id}')
                return security_group_id
        except ClientError as e:
            if 'InvalidGroup.NotFound' in str(e):
                try:
                    response = self.ec2_client.create_security_group(
                        GroupName=security_group_name,
                        Description=description,
                        VpcId=vpc_id
                    )
                    security_group_id = response['GroupId']
                    print(f'Security Group Created: {security_group_id}')
                    return security_group_id
                except ClientError as e:
                    print(f'Error creating security group: {e}')
                    return None
        except Exception as e:
            print(f'Unexpected error: {e}')
            return None

    def setup_security_group(self, security_group_id, permissions=None, mode='add'):
        if mode is None:
            mode = 'add'
        permissions = permissions if permissions else self.config.permission_rules
        try:
            if mode == 'add':
                self.ec2_client.authorize_security_group_ingress(
                    GroupId=security_group_id,
                    IpPermissions=permissions
                )
            elif mode == 'remove':
                self.ec2_client.revoke_security_group_ingress(
                    GroupId=security_group_id,
                    IpPermissions=permissions
                )
            elif mode == 'replace':
                self.ec2_client.update_security_group_rule_descriptions_ingress(
                    GroupId=security_group_id,
                    IpPermissions=permissions
                )
            print(f'Security group ingress rules {mode}{"ed" if mode == "add" else "d"} successfully.')
        except ClientError as e:
            print(f'Error setting security group ingress rules: {e}')

    def setup_ec2(self, security_group_id, create_instance=True):
        instance_id = self.config.instance_id
        if instance_id:
            instance_info = self.check_instance_status(instance_id)
            if instance_info and instance_info.get('State', {}).get('Name') == 'running':
                print(f"Using existing EC2 instance: {instance_id}")
                self.instance_id = instance_id
                return instance_id
            elif instance_info and instance_info.get('State', {}).get('Name') != 'running':
                print(f"Instance {instance_id} found but not running. Starting instance...")
                self.ec2_client.start_instances(InstanceIds=[instance_id])
                self.wait_for_instance(instance_id, 'running')
                self.instance_id = instance_id
                return instance_id
            else:
                print(f"Instance ID {instance_id} not found or not accessible. Creating a new instance...")
        if create_instance:
            return self.create_ec2_instance_with_userdata(security_group_id)

    def check_instance_status(self, instance_id=None):
        try:
            response = self.ec2_client.describe_instances(InstanceIds=[instance_id if instance_id else self.instance_id])
            if response['Reservations']:
                instance_info = response['Reservations'][0]['Instances'][0]
                return instance_info
            else:
                return None
        except ClientError as e:
            print(f"Error retrieving instance status: {e}")
            return None

    def create_ec2_instance_with_userdata(self, security_group_id):
        user_data_script = """#!/bin/bash
        yum install -y amazon-ssm-agent
        systemctl start amazon-ssm-agent
        systemctl enable amazon-ssm-agent
        """
        try:
            response = self.ec2_client.run_instances(
                ImageId=self.config.ami_id,
                InstanceType=self.config.instance_type,
                KeyName=self.config.key_name,
                SecurityGroupIds=[security_group_id],
                SubnetId=self.config.subnet_id,
                UserData=user_data_script,
                MinCount=1,
                MaxCount=1
            )
            instance_id = response['Instances'][0]['InstanceId']
            self.instance_id = instance_id
            print(f"EC2 instance created with ID: {instance_id}")
            self.wait_for_instance(instance_id, 'running')
            return instance_id
        except ClientError as e:
            print(f"Error launching instance: {e}")
            return None

    def wait_for_instance(self, instance_id, state):
        waiter = self.ec2_client.get_waiter(f'instance_{state}')
        try:
            waiter.wait(InstanceIds=[instance_id])
            print(f"Instance {instance_id} is now {state}.")
        except ClientError as e:
            print(f"Error waiting for instance to be {state}: {e}")

    # def transfer_pg_dump_to_rds(self, local_dump_path, rds_db_url, schema='public', table=None):
    #     """ Transfer the PostgreSQL dump file from local to RDS via the EC2 instance. """
    #     # Step 1: Transfer the dump file to the EC2 instance
    #     self.upload_file_to_ec2(local_dump_path, '/tmp/sentiment_temp.dump')
    #     # Step 2: Restore the dump file to the RDS instance from the EC2 instance
    #     restore_command = f"pg_restore -d {rds_db_url} --schema={schema} {'-t ' + table if table else ''} /tmp/sentiment_temp.dump"
    #     self.run_commands_via_ssh(self.config.public_dns_name, self.config.key_path, [restore_command])

    def upload_file_to_ec2(self, local_path, remote_path):
        """Upload a local file to the EC2 instance and verify the upload."""
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            ssh_client.connect(hostname=self.config.public_dns_name, username=self.config.user, key_filename=self.config.key_path)
            ftp_client = ssh_client.open_sftp()
            ftp_client.put(local_path, remote_path)
            ftp_client.close()

            # Verify the file upload
            stdin, stdout, stderr = ssh_client.exec_command(f'ls -l {remote_path}')
            output = stdout.read().decode()
            error = stderr.read().decode()

            if error:
                print(f"Error verifying file upload: {error}")
            elif remote_path.split('/')[-1] in output:
                print(f"File {local_path} uploaded and verified at {remote_path}.")
            else:
                print(f"File {local_path} upload verification failed at {remote_path}.")

            ssh_client.close()
        except Exception as e:
            print(f"Failed to upload file to EC2: {e}")

    def ensure_iam_roles(self):
        """Ensure the IAM roles and instance profiles exist and are correctly configured."""
        iam_role = 'AmazonSSMManagedInstanceCore'
        profile_name = 'AmazonSSMManagedInstanceCore'
        service_role = 'AWSServiceRoleForAmazonSSM'
        policy_arns = [
            'arn:aws:iam::aws:policy/AmazonSSMReadOnlyAccess',
            'arn:aws:iam::aws:policy/AmazonSSMFullAccess',
            'arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore'
        ]

        # Create or ensure the IAM role exists
        self.iam_manager.create_role(iam_role, ["ec2.amazonaws.com"], policy_arns)

        # Create or ensure the service-linked role exists
        self.iam_manager.create_service_linked_role(service_role, 'Service-linked role for Systems Manager')

        # Create or ensure the instance profile exists and the role is attached
        self.iam_manager.ensure_instance_profile(profile_name, iam_role)

        print("IAM roles and instance profiles have been set up.")

    def attach_iam_role(self, instance_id):
        """Attach IAM role to the instance."""
        profile_name = 'AmazonSSMManagedInstanceCore'
        try:
            response = self.ec2_client.describe_iam_instance_profile_associations(
                Filters=[
                    {
                        'Name': 'instance-id',
                        'Values': [instance_id]
                    },
                ],
            )
            associations = response['IamInstanceProfileAssociations']
            if not associations:
                self.ec2_client.associate_iam_instance_profile(
                    IamInstanceProfile={
                        'Name': profile_name
                    },
                    InstanceId=instance_id
                )
                print(f"IAM instance profile {profile_name} attached to instance {instance_id}.")
            else:
                print(f"IAM instance profile already attached to instance {instance_id}.")
        except ClientError as e:
            print(f"Error attaching IAM instance profile: {e}")

    def install_and_start_ssm_agent(self):
        """Install and start the SSM agent on the instance."""
        commands = [
            "sudo yum install -y amazon-ssm-agent",
            "sudo systemctl start amazon-ssm-agent",
            "sudo systemctl enable amazon-ssm-agent"
        ]
        self.run_commands_via_ssh(self.config.public_dns_name, self.config.key_path, commands, user=self.config.user)

    def is_ssm_agent_online(self, instance_id):
        time.sleep(2)  # Wait a bit for the SSM agent to start
        try:
            response = self.ssm_client.describe_instance_information(
                Filters=[{'Key': 'InstanceIds', 'Values': [instance_id]}]
            )
            instance_info = response['InstanceInformationList']
            if instance_info and instance_info[0]['PingStatus'] == 'Online':
                print(f"SSM agent is online for instance {instance_id}.")
                return True
            else:
                print(f"SSM agent is not online for instance {instance_id}.")
                return False
        except ClientError as e:
            print(f"Error checking SSM agent status: {e}")
            return False

    def execute_single_command(self, instance_id, commands):
        """Execute multiple commands on the instance using SSM."""
        try:
            # Combine the commands into a single command string separated by '&&'
            combined_command = ' && '.join(commands) if isinstance(commands, (list, tuple)) else commands
            print(f"Executing commands on {instance_id}: {combined_command}")
            response = self.ssm_client.send_command(
                InstanceIds=[instance_id],
                DocumentName="AWS-RunShellScript",
                Parameters={'commands': [combined_command]},
                TimeoutSeconds=300
            )
            command_id = response['Command']['CommandId']
            time.sleep(5)  # Wait a bit before checking the command output
            output = self.ssm_client.get_command_invocation(
                CommandId=command_id,
                InstanceId=instance_id
            )
            print(f"Command output: {output['StandardOutputContent']}")
        except ClientError as e:
            print(f"Failed to execute commands {commands}: {e}")

    def execute_commands(self, commands, ssm=False, **kwargs):
        """ Execute additional setup commands provided in the config on the launched EC2 instance. """
        if ssm:
            self.execute_single_command(self.instance_id, commands)
        else:
            self.run_commands_via_ssh(self.config.public_dns_name, self.config.key_path, commands, user=self.config.user, **kwargs)


    def clone_git_repository(self, **kwargs):
        """ Clone the Git repository using the commands provided in the config. """
        if 'ssm' not in kwargs:
            kwargs['ssm'] = False
            kwargs['chain'] = True
        self.execute_commands(self.config.git_commands, **kwargs)

    def reboot_instance(self, instance_id=None):
        instance_id = instance_id if instance_id else self.instance_id
        """ Reboots the specified EC2 instance. """
        try:
            self.ec2_client.reboot_instances(InstanceIds=[instance_id])
            print(f"Instance {instance_id} has been rebooted.")
        except ClientError as e:
            print(f"Failed to reboot instance: {e}")

    def stop_instance(self, instance_id=None):
        instance_id = instance_id if instance_id else self.instance_id
        """ Stops the specified EC2 instance. """
        try:
            self.ec2_client.stop_instances(InstanceIds=[instance_id])
            print(f"Instance {instance_id} has been stopped.")
        except ClientError as e:
            print(f"Failed to stop instance: {e}")

    def start_instance(self, instance_id=None):
        instance_id = instance_id if instance_id else self.instance_id
        """ Starts the specified EC2 instance. """
        try:
            self.ec2_client.start_instances(InstanceIds=[instance_id])
            print(f"Instance {instance_id} has been started.")
        except ClientError as e:
            print(f"Failed to start instance: {e}")

    def terminate_instance(self, instance_id=None):
        instance_id = instance_id if instance_id else self.instance_id
        """ Terminates the specified EC2 instance. """
        try:
            self.ec2_client.terminate_instances(InstanceIds=[instance_id])
            print(f"Instance {instance_id} has been terminated.")
        except ClientError as e:
            print(f"Failed to terminate instance: {e}")


if __name__ == '__main__':
    project_name = 'sentiment-dashboard'

    ec2_setup_commands = [
        "sudo yum update -y",
        # "sudo yum install -y httpd24 php70",
        # "sudo service httpd start",
        "sudo yum install -y python3",
        "sudo yum install -y git"  # Added installation of git
    ]

    git_commands = [
        f"rm -rf {project_name}",  # Remove the existing project directory
        fr"git clone --no-checkout https://{github_cred.username}:{github_cred.token}@github.com/{github_cred.username}/{project_name}.git",
        f"cd {project_name}",
        "git sparse-checkout init --cone",
        "git sparse-checkout set back",
        "git checkout main",
        "pip3 install -r requirements.txt"
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
        key_path=ec2_credentials_source.key_path,
        instance_id=ec2_credentials_source.instance_id  # Provide an existing instance ID if available
    )

    ec2_manager = EC2Manager(ec2_config, aws_credentials=aws_credentials_source)
    instance_id_ = ec2_manager.full_flow(create_instance=False)
