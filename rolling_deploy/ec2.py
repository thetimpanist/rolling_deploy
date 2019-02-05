import boto3
from rolling_deploy.exception import (
    RollingDeployException, 
    AwsConnectionException
)
from botocore.exceptions import ClientError

class Ec2Exception(RollingDeployException):
    """Ec2 Logic Exception."""


class Ec2(object):
    """A class representing an AWS ec2 instance."""

    def __init__(self, InstanceId=None):
        self._client = self._get_client()
        self._load_instance(InstanceId)

    def terminate(self):
        """Terminate this instance."""
        try:
            response = self._client.terminate_instances(InstanceIds=(self._id,))
        except ClientError as e:
            raise Ec2Exception(
                "Error attempting to terminate instance %s:\n %s" % \
                (self._id, str(e),)
            )

    @staticmethod
    def _get_client():
        """Helper method to get the boto3 ec2 client."""
        return boto3.client('ec2')

    def _load_instance(self, instance_id):
        """Helper method to load the current data for the passed instance_id 
        into this object.
        """
        try:
            response = self._client.describe_instances(InstanceIds=(instance_id,))
            self._ec2_data = response['Reservations'][0]['Instances'][0]
            self._id = self._ec2_data['InstanceId']
        except (ClientError, IndexError) as e:
            raise Ec2Exception("Instance %s Not Found:\n %s" % \
                (instance_id, str(e),)
                )

    @staticmethod
    def ami_exists(image_id):
        """Helper method to ensure an ami-id exists in aws."""
        client = Ec2._get_client()
        try:
            response = client.describe_images(ImageIds=(image_id,))
            return len(response['Images']) > 0
        except (ClientError, IndexError) as e:
            return False

    @classmethod
    def create_instance(cls, image_id):
        """Factory method to create a new ec2 instance."""
        client = cls._get_client()
        if not cls.ami_exists(image_id):
            raise Ec2Exception('Unable to find requested image')

        try:
            response = client.run_instances(ImageId=image_id, MaxCount=1, 
                MinCount=1
            )
            return cls(response['Instances'][0]['InstanceId'])
        except (ClientError, IndexError) as e:
            raise Ec2Exception(
                "An error occurred when creating ec2 instance.\n %s" % \
                (str(e),)
            )

