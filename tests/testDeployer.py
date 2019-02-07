import unittest
from rolling_deploy.deployer import Deployer, DeployerException
from rolling_deploy.target_group import TargetGroup
from rolling_deploy.ec2 import Ec2
from tests.target_group_mock import MockTargetGroupHelper
from tests.ec2_mock import MockEc2Helper
from moto import mock_ec2, mock_elbv2

@mock_ec2
@mock_elbv2
class TargetGroupTest(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        """Init class test objects."""
        self._target_group_mock = MockTargetGroupHelper()
        self._ec2_mock = MockEc2Helper()
        self._new_ami = self._ec2_mock.images()[2]

    def setUp(self):
        self._target_group_mock.setUp()
        self._target_group = TargetGroup(
            self._target_group_mock.target_group()['TargetGroupArn']
        )

    def tearDown(self):
        self._target_group_mock.tearDown()

    def test_get_old_ami_instances(self):
        """Only instances with old ami should be fetched from target group."""
        deployer = Deployer(self._target_group)
        ami = self._ec2_mock.default_image()
        instances = deployer._get_ami_instances(ami)
        self.assertEqual(set((ami,)), \
            set([instance.ami() for instance in instances])
        )

        new_ec2 = Ec2.create_instance(self._new_ami)
        self._target_group.add_instance(new_ec2)
        instances = deployer._get_ami_instances(ami)
        self.assertEqual(set((ami,)), \
            set([instance.ami() for instance in instances])
        )

    def test_roll_in(self):
        """A single instance with the new ami should be added to the target 
        group on roll in.
        """
        deployer = Deployer(self._target_group)
        deployer._roll_in(self._new_ami)

        self.assertEqual(self._target_group.count(),
            self._ec2_mock.INSTANCE_COUNT + 1
        )

        self.assertIn(self._new_ami, [instance.ami() \
            for instance in self._target_group.healthy_instances()
        ])

    def test_roll_out(self):
        """An instance should be removed from the target group on rollout."""
        deployer = Deployer(self._target_group)
        instance = Ec2(self._ec2_mock.instances()[0]['InstanceId'])

        deployer._roll_out(instance)
        self.assertNotIn(instance.id(),
            [ec2.id() for ec2 in self._target_group.healthy_instances()]
        )

        self.assertEqual(self._target_group.count(), \
            self._ec2_mock.INSTANCE_COUNT -1 
        )

    def test_clean_up(self):
        """An instance drained from the target group should be terminated."""
        deployer = Deployer(self._target_group)
        instance = Ec2(self._ec2_mock.instances()[0]['InstanceId'])

        deployer._roll_out(instance)
        deployer._clean_up((instance,), wait_interval=0)

        self.assertIn(instance.state(),
            (Ec2.STATE_SHUTTING_DOWN, Ec2.STATE_TERMINATED,)
        )


    def test_clean_up_healthy_instance_fails(self):
        """Attempting to terminate a healthy instance should throw an 
        exception.
        """
        deployer = Deployer(self._target_group)
        instance = Ec2(self._ec2_mock.instances()[0]['InstanceId'])

        with self.assertRaises(DeployerException):
            deployer._clean_up((instance,), wait_interval=0)



    def test_deploy(self):
        """All old ami instances should be replaced with instances of the new 
        ami.
        """
        deployer = Deployer(self._target_group)
        old_instances = self._target_group.instances()
        deployer.deploy(self._ec2_mock.default_image(), self._new_ami)

        # correct number of healthy instances
        self.assertEqual(len(self._target_group.healthy_instances()),
            self._ec2_mock.INSTANCE_COUNT
        )

        # all healthy instances are running the new ami
        self.assertEqual(set((self._new_ami,)),
            set([ec2.ami() for ec2 in self._target_group.healthy_instances()])
        )

        # all old instances are terminated
        self.assertEqual(set([ec2.state() for ec2 in old_instances]),
            set((Ec2.STATE_TERMINATED,))
        )

        # only 3 instances are left running in the mock
        self.assertEqual(len(self._ec2_mock.instances()), \
            self._ec2_mock.INSTANCE_COUNT
        )
