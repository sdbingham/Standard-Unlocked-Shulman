# Import the base class - CumulusCI uses Deploy as the base class
from cumulusci.tasks.salesforce.Deploy import Deploy as BaseDeployTask


class Deploy(BaseDeployTask):
    """
    Deploy task.
    
    Note: This task no longer applies transforms. Tokens should be replaced
    permanently using setup_new_project.py before deployment.
    
    To set up a new project:
    1. Run: python setup_new_project.py
    2. This will permanently replace all __PROJECT_NAME__ and __PROJECT_LABEL__ tokens
    3. After that, deployment will work normally without transforms
    """ 