import boto3
from botocore.exceptions import ClientError


class ParameterStoreManager:
    def __init__(self, aws_credentials=None, region_name=None):
        if aws_credentials:
            self.ssm_client = boto3.client(
                'ssm',
                region_name=region_name,
                aws_access_key_id=aws_credentials.access_key,
                aws_secret_access_key=aws_credentials.secret_key
            )
        else:
            self.ssm_client = boto3.client('ssm', region_name=region_name)

    def create_or_update_parameter(self, name, value, description='', type='String', overwrite=False):
        """Creates or updates a parameter in AWS Parameter Store, with optional overwriting."""
        try:
            # Ensure the value is always a string
            value = str(value)
            # Check if the parameter exists and respect the overwrite flag
            if not overwrite:
                self.ssm_client.get_parameter(Name=name)
                print(f"Parameter {name} already exists. Overwrite not allowed.")
                return
            self.ssm_client.put_parameter(
                Name=name,
                Value=value,
                Type=type,
                Description=description,
                Overwrite=True
            )
            print(f"Parameter {name} created or updated successfully.")
        except self.ssm_client.exceptions.ParameterNotFound:
            self.ssm_client.put_parameter(
                Name=name,
                Value=value,
                Type=type,
                Description=description,
                Overwrite=False
            )
            print(f"Parameter {name} created successfully.")
        except ClientError as e:
            print(f"Error creating or updating parameter {name}: {e}")

    def get_parameter(self, name):
        """Retrieves a parameter from AWS Parameter Store."""
        try:
            response = self.ssm_client.get_parameter(Name=name, WithDecryption=True)
            return response['Parameter']['Value']
        except ClientError as e:
            print(f"Error retrieving parameter {name}: {e}")
            return None

    def create_or_update_parameters(self, parameters):
        """Bulk creates or updates parameters in AWS Parameter Store."""
        for param in parameters:
            self.create_or_update_parameter(
                name=param['name'],
                value=param['value'],
                description=param.get('description', ''),
                type=param.get('type', 'String'),
                overwrite=param.get('overwrite', False)
            )


# Example usage
if __name__ == '__main__':
    manager = ParameterStoreManager()
    parameters_to_update = [
        {'name': 'DB_HOST', 'value': 'example.com', 'description': 'Database host', 'overwrite': True},
        {'name': 'DB_USER', 'value': 'admin', 'overwrite': True}
    ]
    manager.create_or_update_parameters(parameters_to_update)
