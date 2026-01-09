import importlib
from cumulusci.core.source_transforms.transforms import FindReplaceTransform
from tasks.deploy import FindReplaceWithFilename

# Dynamically import CreatePackageVersion using CumulusCI's task registry
# This avoids hardcoding import paths which vary by version
from cumulusci.core.config import UniversalConfig, BaseProjectConfig

try:
    # Get the default task class from CumulusCI's registry
    universal_config = UniversalConfig()
    project_config = BaseProjectConfig(universal_config)
    task_config = project_config.get_task('create_package_version')
    BaseCreatePackageVersion = task_config.get_class()
except Exception as e:
    # Fallback: try direct imports if registry fails
    import_error = str(e)
    for module_path in [
        'cumulusci.tasks.sfdx',
        'cumulusci.tasks.salesforce.package', 
        'cumulusci.tasks.salesforce'
    ]:
        try:
            module = importlib.import_module(module_path)
            BaseCreatePackageVersion = getattr(module, 'CreatePackageVersion', None)
            if BaseCreatePackageVersion:
                break
        except (ImportError, AttributeError):
            continue
    else:
        raise ImportError(
            f"Could not import CreatePackageVersion. "
            f"Registry error: {import_error}. "
            f"Tried modules: cumulusci.tasks.sfdx, cumulusci.tasks.salesforce.package, cumulusci.tasks.salesforce"
        ) from e

if BaseCreatePackageVersion is None:
    raise ImportError("Failed to import CreatePackageVersion base class")


class CreatePackageVersion(BaseCreatePackageVersion):
    """CreatePackageVersion task that extends find_replace to also handle filenames."""

    def _init_options(self, kwargs):
        super()._init_options(kwargs)
        
        # Replace any find_replace transforms with our filename-aware version
        for i, transform in enumerate(self.transforms):
            if isinstance(transform, FindReplaceTransform):
                self.transforms[i] = FindReplaceWithFilename(transform.options)
