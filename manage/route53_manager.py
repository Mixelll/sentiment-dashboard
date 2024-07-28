import boto3
from botocore.exceptions import ClientError
import uuid
# from aws_credentials import aws as aws_credentials, personal_contact_info as contact_info


class Route53Config:
    def __init__(self, region_name, hosted_zone_id, domain_name, s3_bucket_name):
        self.region_name = region_name
        self.hosted_zone_id = hosted_zone_id
        self.domain_name = domain_name
        self.s3_bucket_name = s3_bucket_name


class Route53DomainsConfig:
    def __init__(self, domain_name, contact_info):
        self.domain_name = domain_name
        self.contact_info = contact_info


class Route53Manager:
    def __init__(self, config, aws_credentials, domain_config=None):
        self.config = config
        self.route53_client = boto3.client(
            'route53',
            aws_access_key_id=aws_credentials.access_key,
            aws_secret_access_key=aws_credentials.secret_key,
            region_name=self.config.region_name
        )
        if domain_config:
            self.route53domains_manager = Route53DomainsManager(domain_config, aws_credentials)

    def full_flow(self, register_domain=True, setup_dns=True):
        if register_domain and hasattr(self, 'route53domains_manager'):
            self.setup_domain()
        if setup_dns:
            self.setup_dns()

    def setup_dns(self):
        print("Configuring DNS settings with Route 53...")
        s3_website_endpoint = f'{self.config.s3_bucket_name}.s3-website-{self.config.region_name}.amazonaws.com'
        domain_name = self.config.domain_name
        record_name = f'www.{domain_name}'

        hosted_zone = self.create_hosted_zone(domain_name)
        if hosted_zone:
            zone_id = hosted_zone['Id']
            print(f"Adding alias record for {record_name} pointing to {s3_website_endpoint}...")
            self.create_alias_record(zone_id, record_name, s3_website_endpoint)
            print(f"Alias record added for {record_name}")

    def setup_domain(self):
        mng = self.route53domains_manager
        mng_name = mng.config.domain_name
        availability = mng.check_domain_availability()
        if availability == 'AVAILABLE':
            print(f"Domain {mng_name} is available for registration.")
            mng.register_domain()
        elif availability == 'UNAVAILABLE':
            print(f"Domain {mng_name} is already registered.")
        else:
            print(f"Domain {mng_name} status: {availability}")

    def list_hosted_zones(self):
        """List all hosted zones."""
        try:
            response = self.route53_client.list_hosted_zones()
            return response.get('HostedZones', [])
        except ClientError as e:
            print(f"Error listing hosted zones: {e.response['Error']['Message']}")
            return None

    def get_hosted_zone_by_name(self, domain_name):
        """Get a hosted zone by domain name."""
        hosted_zones = self.list_hosted_zones()
        for zone in hosted_zones:
            if zone['Name'].rstrip('.') == domain_name.rstrip('.'):
                return zone
        return None

    def create_hosted_zone(self, domain_name):
        """Create a new hosted zone."""
        existing_zone = self.get_hosted_zone_by_name(domain_name)
        if existing_zone:
            print(f"Hosted zone for {domain_name} already exists.")
            return existing_zone

        try:
            response = self.route53_client.create_hosted_zone(
                Name=domain_name,
                CallerReference=str(uuid.uuid4()),
                HostedZoneConfig={
                    'Comment': 'Created by Route53Manager',
                    'PrivateZone': False
                }
            )
            return response['HostedZone']
        except ClientError as e:
            print(f"Error creating hosted zone: {e.response['Error']['Message']}")
            return None

    def delete_hosted_zone(self, zone_id):
        """Delete a hosted zone."""
        try:
            response = self.route53_client.delete_hosted_zone(Id=zone_id)
            print(f"Hosted zone {zone_id} deleted successfully.")
        except ClientError as e:
            print(f"Error deleting hosted zone: {e.response['Error']['Message']}")

    def list_resource_record_sets(self, zone_id):
        """List all resource record sets in a hosted zone."""
        try:
            response = self.route53_client.list_resource_record_sets(HostedZoneId=zone_id)
            return response.get('ResourceRecordSets', [])
        except ClientError as e:
            print(f"Error listing resource record sets: {e.response['Error']['Message']}")
            return None

    def get_record_set(self, zone_id, record_name, record_type):
        """Get a specific record set."""
        record_sets = self.list_resource_record_sets(zone_id)
        for record_set in record_sets:
            if record_set['Name'].rstrip('.') == record_name.rstrip('.') and record_set['Type'] == record_type:
                return record_set
        return None

    def create_record_set(self, zone_id, record_name, record_type, record_value, ttl=300):
        """Create a new resource record set."""
        existing_record = self.get_record_set(zone_id, record_name, record_type)
        if existing_record and existing_record['ResourceRecords'][0]['Value'] == record_value:
            print(f"Record {record_name} of type {record_type} already exists with the same value.")
            return existing_record

        try:
            response = self.route53_client.change_resource_record_sets(
                HostedZoneId=zone_id,
                ChangeBatch={
                    'Changes': [
                        {
                            'Action': 'UPSERT',
                            'ResourceRecordSet': {
                                'Name': record_name,
                                'Type': record_type,
                                'TTL': ttl,
                                'ResourceRecords': [{'Value': record_value}]
                            }
                        }
                    ]
                }
            )
            return response
        except ClientError as e:
            print(f"Error creating resource record set: {e.response['Error']['Message']}")
            return None

    def delete_record_set(self, zone_id, record_name, record_type, record_value):
        """Delete a resource record set."""
        try:
            response = self.route53_client.change_resource_record_sets(
                HostedZoneId=zone_id,
                ChangeBatch={
                    'Changes': [
                        {
                            'Action': 'DELETE',
                            'ResourceRecordSet': {
                                'Name': record_name,
                                'Type': record_type,
                                'ResourceRecords': [{'Value': record_value}]
                            }
                        }
                    ]
                }
            )
            return response
        except ClientError as e:
            print(f"Error deleting resource record set: {e.response['Error']['Message']}")
            return None

    def create_alias_record(self, zone_id, record_name, target_domain_name):
        # aws route53 list-hosted-zones-by-name --dns-name "s3-website-il-central-1.amazonaws.com"
        """Create an alias record pointing to the S3 bucket."""
        hosted_zone_id = self.config.hosted_zone_id
        existing_record = self.get_record_set(zone_id, record_name, 'A')
        if existing_record and existing_record['AliasTarget']['DNSName'] == target_domain_name:
            print(f"Alias record {record_name} already exists with the same target.")
            return existing_record

        try:
            response = self.route53_client.change_resource_record_sets(
                HostedZoneId=zone_id,
                ChangeBatch={
                    'Changes': [
                        {
                            'Action': 'UPSERT',
                            'ResourceRecordSet': {
                                'Name': record_name,
                                'Type': 'A',
                                'AliasTarget': {
                                    'HostedZoneId': hosted_zone_id if hosted_zone_id else zone_id.split('/')[-1],  # Hosted Zone ID for S3 static websites.
                                    'DNSName': target_domain_name,
                                    'EvaluateTargetHealth': False
                                }
                            }
                        }
                    ]
                }
            )
            return response
        except ClientError as e:
            print(f"Error creating alias record: {e.response['Error']['Message']}")
            return None


class Route53DomainsManager:
    def __init__(self, config, aws_credentials):
        self.config = config
        self.route53domains_client = boto3.client(
            'route53domains',
            aws_access_key_id=aws_credentials.access_key,
            aws_secret_access_key=aws_credentials.secret_key,
            region_name='us-east-1'
        )

    def check_domain_availability(self):
        try:
            response = self.route53domains_client.check_domain_availability(
                DomainName=self.config.domain_name
            )
            return response['Availability']
        except ClientError as e:
            print(f"Error checking domain availability: {e}")
            return None

    def register_domain(self):
        """Initiates a request to register a domain. Can take several hours to complete"""
        contact_info = self.config.contact_info
        try:
            response = self.route53domains_client.register_domain(
                DomainName=self.config.domain_name,
                DurationInYears=1,
                AdminContact=contact_info,
                RegistrantContact=contact_info,
                TechContact=contact_info,
                AutoRenew=True,
                PrivacyProtectAdminContact=True,
                PrivacyProtectRegistrantContact=True,
                PrivacyProtectTechContact=True
            )
            print(f"Domain {self.config.domain_name} registration initiated. Response: {response}")
        except ClientError as e:
            print(f"Error registering domain: {e}")


# Example usage:
if __name__ == '__main__':
    region = 'us-east-1'
    domain = 'yourdomain.com'
    s3_bucket_name = 'your-s3-bucket'


    # Set up Route53 configuration
    route53_config = Route53Config(region, domain, s3_bucket_name)
    route53_manager = Route53Manager(route53_config, aws_credentials)
    route53_manager.setup_dns()

    # Set up Route53Domains configuration
    route53_domains_config = Route53DomainsConfig(region, domain)
    route53_domains_manager = Route53DomainsManager(route53_domains_config, aws_credentials)

