import boto3
from rolling_deploy.exception import (
    RollingDeployException, 
    AwsConnectionException
)
from rolling_deploy.ec2 import Ec2
from botocore.exceptions import ClientError
from time import sleep
import logging

class ElbException(RollingDeployException):
    """Load Balancer Logic Exception."""

class TargetGroup(object):
    """A class representing an AWS ELB attached target group."""

    HEALTH_HEALTHY = 'healthy'
    HEALTH_UNHEALTHY = 'unhealthy'
    HEALTH_INITIAL = 'initial'
    HEALTH_DRAINING = 'draining'

    WAIT_INTERVAL = 5
    WAIT_LIMIT = 60

    def __init__(self, TargetGroupArn=None):
        self._client = self._get_client()
        self._load_target_group(TargetGroupArn)

    def _load_target_group(self, target_group_arn):
        """Helper method to load the data for the target group into this 
        object.
        """
        try:
            response = self._client.describe_target_groups(
                TargetGroupArns=(target_group_arn,)
            )
            self._tg_data = response['TargetGroups'][0]
        except (ClientError, IndexError) as e:
            raise ElbException("Target group %s Not Found: \n %s" % \
                (target_group_arn, str(e),)
            )

    def _get_target_health(self):
        """Helper method returning raw target health checks."""
        return self._client.describe_target_health(
            TargetGroupArn=self.arn()
            )['TargetHealthDescriptions']

    def arn(self):
        """Get the arn of this target group."""
        return self._tg_data['TargetGroupArn']

    def count(self):
        """Get the number of instances in this target group."""
        targets = self._get_target_health()
        return len(targets)

    def instances(self):
        """Get a list of Ec2 objects representing instances attached to this 
        target group.
        """
        targets = self._get_target_health()
        return [Ec2(InstanceId=instance['Target']['Id']) for instance in targets]

    def healthy_instances(self):
        """Get a list of Ec2 objects represnting instances that are reporting
        a target group health check of healthy.
        """
        targets = self._get_target_health()
        return [Ec2(InstanceId=instance['Target']['Id']) for instance in \
            targets if instance['TargetHealth']['State'] == self.HEALTH_HEALTHY
            ]

    def is_healthy(self, instance):
        """Is the instance reporting healthy in this target group?"""
        return instance.id() in [ec2.id() for ec2 in self.healthy_instances()]

    def wait_healthy(self, instance):
        """Poll instance until it's passes target group health checks."""
        poll = 0
        while not self.is_healthy(instance) and poll < self.WAIT_LIMIT:
            logging.info("Waiting for ec2 %s to report healthy." % \
                (instance.id(),)
            )
            sleep(self.WAIT_INTERVAL)
            poll += 1

        if poll >= self.WAIT_LIMIT:
            raise Ec2Exception("Instance %s took too long to pass health checks." \
                % (instance.id(),)
            )
        return True

    def add_instance(self, instance):
        """Add an instance to the target group."""
        if not instance.id() or instance.state() != Ec2.STATE_RUNNING:
            raise ElbException('Instance %s is not in ready state.' % \
                (instance.id(),)
            )
        try:
            self._client.register_targets(TargetGroupArn=self.arn(), 
                Targets=({"Id": instance.id()},)
            )
        except (ClientError, IndexError) as e:
            raise ElbException('Unable to add instance %s to TargetGroup:\n %s' % \
                (instance.id(), str(e)))

    def remove_instance(self, instance):
        """Remove an instance from the target group."""
        if instance.id() not in [ec2.id() for ec2 in self.instances()]:
            raise ElbException('Unable to remove %s from target group.' % \
                (instance.id(),)
            )

        try:
            self._client.deregister_targets(TargetGroupArn=self.arn(), 
                Targets=({"Id": instance.id()},)
            )
        except (ClientError, IndexError) as e:
            raise ElbException(
                'Unable to remove instance %s from target group:\n %s' % \
                (instance.id(), str(e))
            )

    @staticmethod
    def _get_client():
        """Helper method to get the boto3 elbv2 client."""
        return boto3.client('elbv2')
