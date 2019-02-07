import unittest
import boto3
from rolling_deploy.ec2 import Ec2, Ec2Exception
from tests.ec2_mock import MockEc2Helper
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
        self._ec2_mock = MockEc2Helper()

    def setUp(self):
        """Start test with default 3 instances created."""
        self.tearDown()
        self._ec2_mock.setUp()

    def tearDown(self):
        """Clean all instances from mock after testing."""
        self._ec2_mock.tearDown()

    def test_load_instance(self):
        """Instantiating an Ec2 object with an instance id should return an
        object containing that instance's data.
        """
        instances = self._ec2_mock.instances()
        instance = Ec2(InstanceId=instances[0]['InstanceId'])
        self.assertEqual(instance._ec2_data, instances[0])
        self.assertEqual(instance.id(), instances[0]['InstanceId'])

    def test_load_instance_bad_id(self):
        """Instantiating an Ec2 object with a non-existant id should cause an 
        error.
        """
        with self.assertRaises(Ec2Exception):
            Ec2(InstanceId='badid')

    def test_ami_exists(self):
        """AMI existance tests should return correct boolean values."""
        images = self._ec2_mock.images()
        self.assertTrue(Ec2.ami_exists(images[0]))
        self.assertFalse(Ec2.ami_exists('ami-phonyid'))

    def test_create_instance(self):
        """Creating an instance should work."""
        images = self._ec2_mock.images()

        # new instance should have an id
        instance = Ec2.create_instance(images[0])
        self.assertEqual(len(instance.id()), self.INSTANCE_ID_LENGTH)

        # there should only be one new instance
        self.assertEqual(len(self._ec2_mock.instances()), self.INSTANCE_COUNT + 1)

    def test_create_instance_bad_ami(self):
        """Creating an instance with an improper ami id should fail."""
        with self.assertRaises(Ec2Exception):
            instance = Ec2.create_instance('ami-phonyid')

    def test_terminate_instance(self):
        """Terminating an instance should work remove it from the live 
        instances.
        """
        instances = self._ec2_mock.instances()
        instance = Ec2(InstanceId=instances[0]['InstanceId'])
        instance.terminate()
        self.assertEqual(len(self._ec2_mock.instances()), self.INSTANCE_COUNT - 1)

    def test_double_termination_failure(self):
        """Attempting to terminate the same instance instance twice should 
        fail.
        """
        instance_id = self._ec2_mock.instances()[0]['InstanceId']
        instance = Ec2(InstanceId=instance_id)
        instance.terminate()
        with self.assertRaises(Ec2Exception):
            instance.terminate()

        instance = Ec2(InstanceId=instance_id)
        with self.assertRaises(Ec2Exception):
            instance.terminate()

    def test_state_returns_current_state(self):
        """Getting the state of an instance should return it's state."""
        instance_id = self._ec2_mock.instances()[0]['InstanceId']
        instance = Ec2(InstanceId=instance_id)

        self.assertEqual(instance.state(), Ec2.STATE_RUNNING)

        instance.terminate()
        self.assertIn(instance.state(),
            (Ec2.STATE_SHUTTING_DOWN, Ec2.STATE_TERMINATED)
        )

    def test_ami_returns_ami_id(self):
        """Getting the ami of an instance should return it's ami id."""
        instance_id = self._ec2_mock.instances()[0]['InstanceId']
        instance = Ec2(InstanceId=instance_id)

        self.assertEqual(instance.ami(), self._ec2_mock.default_image())


    def test_wait_ready(self):
        """Class should poll instance until it times out or becomes ready."""
        ec2 = Ec2.create_instance(self._ec2_mock.default_image())
        self.assertTrue(ec2.wait_ready())
        # TODO test wait timeout????

