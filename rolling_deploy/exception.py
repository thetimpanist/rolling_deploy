class RollingDeployException(Exception):
    """Global Exception for this appliction."""

class AwsConnectionException(RollingDeployException):
    """Error communicating with AWS."""
