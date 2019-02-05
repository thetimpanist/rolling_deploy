import unittest
import boto3
from rolling_deploy.ec2 import Ec2, Ec2Exception
from moto import mock_ec2


@mock_ec2
class Ec2Test(unittest.TestCase):
    """Ec2 Object Tests."""

    INSTANCE_ID_LENGTH = 19
    INSTANCE_COUNT = 3

    @classmethod
    @mock_ec2
    def setUpClass(self):
        """Init class objects."""
        self._client = boto3.client('ec2')

    def setUp(self):
        """Start test with default 3 instances created."""
        self.tearDown()
        self._client.run_instances(ImageId=self._images()[2],
            MinCount=self.INSTANCE_COUNT, MaxCount=self.INSTANCE_COUNT
            )

    def tearDown(self):
        """Clean all instances from mock after testing."""
        ids = [instance['InstanceId'] for instance in self._instances()]
        if ids:
            self._client.terminate_instances(InstanceIds=ids)

    def _images(self):
        """Get a list of ami images in the mock."""
        response = self._client.describe_images()
        return [image['ImageId'] for image in response['Images']]

    def _instances(self):
        """Get a list of currently live instances."""
        response = self._client.describe_instances()
        return [instance for reservation in response['Reservations'] \
            for instance in reservation['Instances'] \
            if instance['State']['Name'] in ('pending', 'running')
            ]

    def test_load_instance(self):
        """Instantiating an Ec2 object with an instance id should return an
        object containing that instance's data.
        """
        instances = self._instances()
        instance = Ec2(InstanceId=instances[0]['InstanceId'])
        self.assertEqual(instance._ec2_data, instances[0])
        self.assertEqual(instance._id, instances[0]['InstanceId'])

    def test_load_instance_bad_id(self):
        """Instantiating an Ec2 object with a non-existant id should cause an 
        error.
        """
        with self.assertRaises(Ec2Exception):
            Ec2(InstanceId='badid')

    def test_ami_exists(self):
        """AMI existance tests should return correct boolean values."""
        images = self._images()
        self.assertTrue(Ec2.ami_exists(images[0]))
        self.assertFalse(Ec2.ami_exists('ami-phonyid'))

    def test_create_instance(self):
        """Creating an instance should work."""
        images = self._images()

        # new instance should have an id
        instance = Ec2.create_instance(images[0])
        self.assertEqual(len(instance._id), self.INSTANCE_ID_LENGTH)

        # there should only be one new instance
        self.assertEqual(len(self._instances()), self.INSTANCE_COUNT + 1)

    def test_create_instance_bad_ami(self):
        """Creating an instance with an improper ami id should fail."""
        with self.assertRaises(Ec2Exception):
            instance = Ec2.create_instance('ami-phonyid')

    def test_terminate_instance(self):
        """Terminating an instance should work remove it from the live 
        instances.
        """
        instances = self._instances()
        instance = Ec2(InstanceId=instances[0]['InstanceId'])
        instance.terminate()
        self.assertEqual(len(self._instances()), self.INSTANCE_COUNT - 1)

    def test_double_termination_failure(self):
        """Attempting to terminate the same instance instance twice should 
        fail.
        """
        instance_id = self._instances()[0]['InstanceId']
        instance = Ec2(InstanceId=instance_id)
        instance.terminate()
        with self.assertRaises(Ec2Exception):
            instance.terminate()

        instance = Ec2(InstanceId=instance_id)
        with self.assertRaises(Ec2Exception):
            instance.terminate()
