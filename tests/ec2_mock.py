import boto3
from moto import mock_ec2

@mock_ec2
class MockEc2Helper(object):
    INSTANCE_COUNT = 3

    def __init__(self):
       self._client = boto3.client('ec2')

    def images(self):
        """Get a list of ami images in the mock."""
        response = self._client.describe_images()
        return [image['ImageId'] for image in response['Images']]

    def default_image(self):
        """Return the default ami used to create mocked instances."""
        return self.images()[0]

    def instances(self):
        """Get a list of currently live instances."""
        response = self._client.describe_instances()
        return [instance for reservation in response['Reservations'] \
            for instance in reservation['Instances'] \
            if instance['State']['Name'] in ('pending', 'running')
            ]

    def tearDown(self):
        """Clean all instances from the mock."""
        ids = [instance['InstanceId'] for instance in self.instances()]
        if ids:
            self._client.terminate_instances(InstanceIds=ids)

    def setUp(self):
        """Start test with default INSTANCE_COUNT instances created."""
        self.tearDown()
        self._client.run_instances(ImageId=self.default_image(),
            MinCount=self.INSTANCE_COUNT, MaxCount=self.INSTANCE_COUNT
            )
