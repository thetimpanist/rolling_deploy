from tests.ec2_mock import MockEc2Helper
from moto import mock_elbv2
import boto3

@mock_elbv2
class MockTargetGroupHelper(object):

    def __init__(self):
        self._client = boto3.client('elbv2')
        self._ec2_mock = MockEc2Helper()

    def setUp(self):
        self.tearDown()
        self._ec2_mock.setUp()

        self._target_group = self._client.create_target_group(
            Name='MyTG', Port=80
        )['TargetGroups'][0]

        self._client.register_targets(
            TargetGroupArn=self._target_group['TargetGroupArn'],
            Targets=[{"Id": instance['InstanceId']} for instance in
                self._ec2_mock.instances()
            ]
        )
        return self._target_group

    def tearDown(self):
        self._ec2_mock.tearDown()
        response = self._client.describe_target_groups()
        for target_group in response['TargetGroups']:
            self._client.delete_target_group(
                TargetGroupArn=target_group['TargetGroupArn']
            )

    def target_group(self):
        return self._target_group
