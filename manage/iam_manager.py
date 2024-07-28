import boto3
import json
from botocore.exceptions import ClientError


class IAMManager:
    def __init__(self, aws_credentials=None):
        self.iam_client = boto3.client(
            'iam',
            aws_access_key_id=aws_credentials.access_key if aws_credentials else None,
            aws_secret_access_key=aws_credentials.secret_key if aws_credentials else None
        )

    def create_role(self, role_name, service_principals, policy_arns, description=""):
        """Create an IAM role with specified policies or update existing role with new policies."""
        assume_role_policy_document = {
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Principal": {"Service": service_principals},
                "Action": "sts:AssumeRole"
            }]
        }
        try:
            role = self.iam_client.get_role(RoleName=role_name)
            print(f"IAM role {role_name} already exists.")
            existing_policies = self.list_attached_role_policies(role_name)
        except self.iam_client.exceptions.NoSuchEntityException:
            role = self.iam_client.create_role(
                RoleName=role_name,
                AssumeRolePolicyDocument=json.dumps(assume_role_policy_document),
                Description=description
            )
            print(f"IAM role {role_name} created.")
            existing_policies = []

        # Attach policies if they are not already attached
        for policy_arn in policy_arns:
            if policy_arn not in existing_policies:
                self.attach_policy_to_role(role_name, policy_arn)
            else:
                print(f"Policy {policy_arn} ALREADY attached to role {role_name}.")

    def list_attached_role_policies(self, role_name):
        """Return a list of policy ARNs attached to a role."""
        paginator = self.iam_client.get_paginator('list_attached_role_policies')
        policy_arns = []
        for page in paginator.paginate(RoleName=role_name):
            for policy in page['AttachedPolicies']:
                policy_arns.append(policy['PolicyArn'])
        return policy_arns

    def attach_policy_to_role(self, role_name, policy_arn):
        """Attach a single policy to an IAM role."""
        try:
            self.iam_client.attach_role_policy(RoleName=role_name, PolicyArn=policy_arn)
            print(f"Policy {policy_arn} attached to role {role_name}.")
        except ClientError as e:
            print(f"Error attaching policy {policy_arn} to role {role_name}: {e}")

    def create_service_linked_role(self, service_name, description=""):
        """Create a service-linked role if it doesn't exist."""
        try:
            self.iam_client.get_role(RoleName=service_name)
            print(f"Service-linked role {service_name} already exists.")
        except self.iam_client.exceptions.NoSuchEntityException:
            self.iam_client.create_service_linked_role(AWSServiceName=service_name, Description=description)
            print(f"Service-linked role {service_name} created.")

    def ensure_instance_profile(self, profile_name, role_name):
        """Ensure instance profile exists and is attached to the specified role."""
        try:
            profile = self.iam_client.get_instance_profile(InstanceProfileName=profile_name)
            print(f"Instance profile {profile_name} already exists.")
            if role_name not in [role['RoleName'] for role in profile['InstanceProfile']['Roles']]:
                self.iam_client.add_role_to_instance_profile(InstanceProfileName=profile_name, RoleName=role_name)
                print(f"Role {role_name} added to instance profile {profile_name}.")
        except self.iam_client.exceptions.NoSuchEntityException:
            self.iam_client.create_instance_profile(InstanceProfileName=profile_name)
            self.iam_client.add_role_to_instance_profile(InstanceProfileName=profile_name, RoleName=role_name)
            print(f"Instance profile {profile_name} created and role {role_name} added.")

# Example usage
if __name__ == '__main__':
    iam_manager = IAMManager(region='us-east-1')
    iam_manager.create_role(
        role_name="ExampleRole",
        service_principals=["ec2.amazonaws.com", "lambda.amazonaws.com"],
        policy_arns=["arn:aws:iam::aws:policy/AdministratorAccess"],
        description="Example role for EC2 and Lambda."
    )
    iam_manager.create_service_linked_role(service_name="lambda.amazonaws.com", description="Service-linked role for AWS Lambda.")
    iam_manager.ensure_instance_profile(profile_name="ExampleProfile", role_name="ExampleRole")
