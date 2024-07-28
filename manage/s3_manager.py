from aws_credentials import aws as aws_credentials_source
import boto3
import json
import subprocess
from botocore.exceptions import ClientError
import os


class S3Config:
    def __init__(self, region, bucket_name, static_website_hosting=False, website_index_document='index.html',
                 website_error_document='error.html', enable_public_access=False, setup_commands=None, dist_directory=None, bucket_policy=None):
        self.region = region
        self.bucket_name = bucket_name
        self.static_website_hosting = static_website_hosting
        self.website_index_document = website_index_document
        self.website_error_document = website_error_document
        self.enable_public_access = self.initialize_enable_public_access(enable_public_access)
        self.setup_commands = setup_commands or []
        self.dist_directory = dist_directory
        self.bucket_policy = bucket_policy or self.default_bucket_policy()

    @staticmethod
    def initialize_enable_public_access(settings):
        if isinstance(settings, bool):
            return {
                'BlockPublicAcls': not settings,
                'IgnorePublicAcls': not settings,
                'BlockPublicPolicy': not settings,
                'RestrictPublicBuckets': not settings
            }
        return settings

    def default_bucket_policy(self):
        return {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "PublicReadGetObject",
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": "s3:GetObject",
                    "Resource": f"arn:aws:s3:::{self.bucket_name}/*"
                }
            ]
        }


class S3Manager:
    def __init__(self, config, aws_credentials=None):
        self.config = config
        self.s3_client = boto3.client(
            's3',
            region_name=config.region,
            aws_access_key_id=aws_credentials.access_key if aws_credentials else None,
            aws_secret_access_key=aws_credentials.secret_key if aws_credentials else None
        )

    def full_flow(self, modify_existing_bucket=False, delete_existing_bucket=False, delete_files=False, sync_files=False,
                  dist_directory=None):
        if delete_existing_bucket:
            self.delete_bucket()
        _, found_bucket = self.create_or_modify_bucket()
        if delete_files:
            self.delete_files()
        if not (found_bucket and not modify_existing_bucket):
            self.modify_bucket()
        dist_directory = dist_directory if dist_directory else self.config.dist_directory
        if sync_files and dist_directory:
            self.sync_directory(dist_directory)

    def create_bucket(self):
        self.create_or_modify_bucket()

    def create_or_modify_bucket(self):
        try:
            self.s3_client.head_bucket(Bucket=self.config.bucket_name)
            print(f"Using existing S3 bucket: {self.config.bucket_name}")
            return True, True
        except ClientError:
            self.s3_client.create_bucket(
                Bucket=self.config.bucket_name,
                CreateBucketConfiguration={'LocationConstraint': self.config.region},
            )
            print(f"S3 bucket {self.config.bucket_name} created successfully in {self.config.region}")
            return True, False

    def modify_bucket(self):
        self.set_bucket_policies_and_access()
        self.execute_setup_commands()

    def execute_setup_commands(self):
        """ Execute additional setup commands provided in the config. """
        for command in self.config.setup_commands:
            print(f"Executing setup command: {command}")
            try:
                if command.startswith("aws "):  # Assuming it's an AWS CLI command
                    subprocess.run(command, check=True, shell=True)
                else:
                    # Assuming it's a boto3 call or some other Python-executable command
                    # This will need custom handling for each type of command
                    eval(command)  # Caution: using eval() is risky unless you trust the source of the commands
            except subprocess.CalledProcessError as e:
                print(f"Failed to execute command: {e}")
            except Exception as e:
                print(f"Error executing command: {e}")

    def delete_bucket(self):
        try:
            self.s3_client.delete_bucket(Bucket=self.config.bucket_name)
            print(f"S3 bucket {self.config.bucket_name} deleted successfully.")
        except ClientError as e:
            print(f"Failed to delete bucket: {e}")

    def delete_files(self):
        try:
            response = self.s3_client.list_objects_v2(Bucket=self.config.bucket_name)
            for item in response.get('Contents', []):
                self.s3_client.delete_object(Bucket=self.config.bucket_name, Key=item['Key'])
            print(f"All files deleted from bucket {self.config.bucket_name}.")
        except ClientError as e:
            print(f"Failed to delete files: {e}")

    def set_bucket_policies_and_access(self):
        if self.config.static_website_hosting:
            self.enable_static_website_hosting()
        if self.config.enable_public_access is not None:
            self.set_public_access(self.config.enable_public_access)
        if self.config.bucket_policy:
            self.set_bucket_policy(self.config.bucket_policy)

    def enable_static_website_hosting(self):
        website_configuration = {
            'IndexDocument': {'Suffix': self.config.website_index_document},
            'ErrorDocument': {'Key': self.config.website_error_document}
        }
        self.s3_client.put_bucket_website(
            Bucket=self.config.bucket_name,
            WebsiteConfiguration=website_configuration
        )
        print(f"Static website hosting enabled for bucket {self.config.bucket_name}")

    def set_public_access(self, access_settings):
        self.s3_client.put_public_access_block(
            Bucket=self.config.bucket_name,
            PublicAccessBlockConfiguration=access_settings
        )
        print(f"Public access settings updated for bucket {self.config.bucket_name}")

    def get_public_access_settings(self):
        """
        Retrieves the public access block settings for the configured S3 bucket.
        """
        try:
            response = self.s3_client.get_public_access_block(Bucket=self.config.bucket_name)
            settings = response['PublicAccessBlockConfiguration']
            print(f"Public access settings for bucket {self.config.bucket_name}: {settings}")
            return settings
        except ClientError as e:
            print(f"Failed to retrieve public access settings: {e}")
            return None

    def set_bucket_policy(self, policy):
        self.s3_client.put_bucket_policy(
            Bucket=self.config.bucket_name,
            Policy=json.dumps(policy)
        )
        print(f"Bucket policy set for {self.config.bucket_name}")

    def set_bucket_acl(self, acl='private'):
        """
        Sets the ACL for the entire bucket.
        :param acl: A predefined ACL like 'private', 'public-read', 'public-read-write', etc.
        """
        try:
            self.s3_client.put_bucket_acl(Bucket=self.config.bucket_name, ACL=acl)
            print(f"ACL '{acl}' set for bucket {self.config.bucket_name}.")
        except ClientError as e:
            print(f"Failed to set bucket ACL: {e}")

    def set_object_acl(self, object_key, acl='private'):
        """
        Sets the ACL for a specific object in the bucket.
        :param object_key: The key (path) of the object within the bucket.
        :param acl: A predefined ACL like 'private', 'public-read', etc.
        """
        try:
            self.s3_client.put_object_acl(Bucket=self.config.bucket_name, Key=object_key, ACL=acl)
            print(f"ACL '{acl}' set for object {object_key} in bucket {self.config.bucket_name}.")
        except ClientError as e:
            print(f"Failed to set object ACL: {e}")

    def sync_directory(self, local_directory, acl='public-read'):
        sync_command = f"aws s3 sync {local_directory} s3://{self.config.bucket_name}"
        try:
            subprocess.run(sync_command, check=True, shell=True)
            print(f"Directory {local_directory} synced successfully with S3 bucket {self.config.bucket_name}")
        except subprocess.CalledProcessError as e:
            print(f"Failed to sync directory: {e}")


if __name__ == '__main__':
    cwd = os.getcwd()
    print("Current working directory: ", cwd)
    project_name = 'sentiment-dashboard'
    dist_path = cwd + fr'\front\{project_name}\dist\{project_name}'
    # Example Usage
    s3_config = S3Config(region='il-central-1', bucket_name='mixel-sentiment-dash', static_website_hosting=True, enable_public_access=True, dist_directory=dist_path)
    s3_manager = S3Manager(s3_config, aws_credentials=aws_credentials_source)
    s3_manager.full_flow(delete_files=True, modify_existing_bucket=True)
    s3_manager.full_flow(sync_files=True)
    s3_manager.get_public_access_settings()
