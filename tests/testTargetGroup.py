import unittest
import boto3
from rolling_deploy.target_group import TargetGroup, ElbException
from rolling_deploy.ec2 import Ec2
from moto import mock_elbv2, mock_ec2
from tests.ec2_mock import MockEc2Helper
from tests.target_group_mock import MockTargetGroupHelper

@mock_elbv2
class TargetGroupTest(unittest.TestCase):
    """Target Group Object Tests."""

    @classmethod
    @mock_elbv2
    def setUpClass(self):
        """Init class objects."""
        self._client = boto3.client('elbv2')
        self._target_group_mock = MockTargetGroupHelper()
        self._ec2_mock = MockEc2Helper()

    def setUp(self):
        """Start test with default elb and single target group."""
        self._target_group = self._target_group_mock.setUp()

    def tearDown(self):
        self._target_group_mock.tearDown()

    def test_load_target_group(self):
        """Target Group should load with api pulled data."""
        target_group = TargetGroup(
            TargetGroupArn=self._target_group['TargetGroupArn']
        )

        self.assertEqual(target_group._tg_data['TargetGroupArn'],
            self._target_group['TargetGroupArn']
        )
        self.assertEqual(target_group._tg_data['TargetGroupName'],
            self._target_group['TargetGroupName']
        )

    def test_load_target_group_fails_with_bad_arn(self):
        """Target Group should fail when bad arn is passed."""
        with self.assertRaises(ElbException):
            TargetGroup('naughtyarn')

    def test_instance_count(self):
        """Target Group should have 3 instances registered."""
        target_group = TargetGroup(self._target_group['TargetGroupArn'])
        self.assertEqual(target_group.count(), self._ec2_mock.INSTANCE_COUNT)

    def test_instance_retrievable(self):
        """Target group should return the instances currently registered."""
        target_group = TargetGroup(self._target_group['TargetGroupArn'])
        mock_instances = [instance['InstanceId'] for instance in \
            self._ec2_mock.instances()]

        tg_instances = [instance.id() for instance in target_group.instances()]

        self.assertEqual(set(tg_instances), set(mock_instances))

    def test_add_instance(self):
        """Registering an instance should add it to the target group."""
        ami_id = self._ec2_mock.images()[0]
        instance = Ec2.create_instance(ami_id)

        target_group = TargetGroup(self._target_group['TargetGroupArn'])
        target_group.add_instance(instance)

        self.assertEqual(target_group.count(), self._ec2_mock.INSTANCE_COUNT + 1)
        self.assertIn(instance.id(), 
            [ec2.id() for ec2 in target_group.instances()]
        )

    def test_add_terminated_instance_failure(self):
        """Adding a non-ready instance should fail."""
        ami_id = self._ec2_mock.default_image()
        instance = Ec2.create_instance(ami_id)
        instance.terminate()
        target_group = TargetGroup(self._target_group['TargetGroupArn'])

        with self.assertRaises(ElbException):
            target_group.add_instance(instance)

    def test_remove_instance(self):
        """Removing an instance should remove it from the target group."""
        target_group = TargetGroup(self._target_group['TargetGroupArn'])
        instances = target_group.instances()

        target_group.remove_instance(instances[0])
        self.assertEqual(len(target_group.instances()),
            self._ec2_mock.INSTANCE_COUNT - 1
        )

        self.assertNotIn(instances[0].id(), [ec2.id() for ec2 in
            target_group.instances()]
        )

    def test_remove_non_grouped_instance_should_fail(self):
        """Removing an instance not in the target group should fail."""
        ami_id = self._ec2_mock.default_image()
        instance = Ec2.create_instance(ami_id)
        target_group = TargetGroup(self._target_group['TargetGroupArn'])

        with self.assertRaises(ElbException):
            target_group.remove_instance(instance)

    def test_healthy_instance_check(self):
        """All instances should report back as healthy."""
        target_group = TargetGroup(self._target_group['TargetGroupArn'])

        instance_ids = [ec2.id() for ec2 in target_group.instances()]
        healthy_ids = [ec2.id() for ec2 in target_group.healthy_instances()]

        self.assertEqual(set(instance_ids), set(healthy_ids))
    # TODO test unhealthy instances? how with mock?

    def test_is_healthy(self):
        """Test that an instance that should be healthy reports as healthy."""
        target_group = TargetGroup(self._target_group['TargetGroupArn'])
        self.assertTrue(target_group.is_healthy(target_group.instances()[0]))

    def test_is_unhealthy(self):
        """Test that an instance that is not in the group doesn't report as
        healthy.
        """
        target_group = TargetGroup(self._target_group['TargetGroupArn'])
        ami_id = self._ec2_mock.default_image()
        instance = Ec2.create_instance(ami_id)

        self.assertFalse(target_group.is_healthy(instance))

    def test_wait_healthy(self):
        """Health check should return true when target registers as healthy."""
        target_group = TargetGroup(self._target_group['TargetGroupArn'])
        ami_id = self._ec2_mock.default_image()
        instance = Ec2.create_instance(ami_id)
        target_group.add_instance(instance)

        self.assertTrue(target_group.wait_healthy(instance))

