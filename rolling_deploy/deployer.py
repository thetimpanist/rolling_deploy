import boto3
from rolling_deploy.exception import (
    RollingDeployException,
    AwsConnectionException
)
from rolling_deploy.ec2 import Ec2
from botocore.exceptions import ClientError
from time import sleep
import logging

class DeployerException(RollingDeployException):
    """Deployment Logic Exception."""

class Deployer(object):
    """Class to manage rolling deployments of ec2 instances to a target group."""

    WAIT_TIMEOUT = 30

    def __init__(self, target_group):
        self._target_group = target_group


    def deploy(self, old_ami, new_ami):
        """Replace all instances running the old ami with instances
        running the new ami.
        """
        old_instances = self._get_ami_instances(old_ami)
        logging.info("Replacing %d instances running ami %s with ami %s" %
            (len(old_instances), old_ami, new_ami)
        )
        for instance in old_instances:
            self._roll_in(new_ami)
            self._roll_out(instance)

        self._clean_up(old_instances)

    def _get_ami_instances(self, ami, healthy=False):
        """Get all instances in target group running the an ami."""
        instances = [instance for instance in self._target_group.instances() \
            if instance.ami() == ami
        ]
        if healthy:
            instances = [instance for instance in instances if instance.healthy()]
        return instances

    def _roll_in(self, ami):
        """Add a new instance to the target group with the new ami."""
        new_instance = Ec2.create_instance(ami)
        new_instance.wait_ready()

        self._target_group.add_instance(new_instance)
        self._target_group.wait_healthy(new_instance)

    def _roll_out(self, instance):
        """Remove an instance from the target group."""
        logging.info("Removing instance %s from target group." % \
            (instance.id(),)
        )
        self._target_group.remove_instance(instance)

    def wait_drained(self, instance, wait_interval=10):
        """Wait for instance to be drained from the target_group."""
        poll = 0
        targets = [ec2.id() for ec2 in self._target_group.instances()]
        while instance.id() in targets and poll < self.WAIT_TIMEOUT:
            logging.info("Waiting for instance %s to drain from target group." %
                (instance.id(),)
            )
            targets = [ec2.id() for ec2 in self._target_group.instances()]
            sleep(wait_interval)
            poll += 1

        if poll >= self.WAIT_TIMEOUT:
            raise DeployerException(
                "Instance %s is not draining from the target group." %
                (instance.id(),)
            )
        return True

    def _clean_up(self, instances, wait_interval=5):
        """Terminate any old instances."""
        for instance in instances:
            self.wait_drained(instance, wait_interval)
            logging.info("Terminating instance %s" % (instance.id(),))
            instance.terminate()
