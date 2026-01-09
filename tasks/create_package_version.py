from cumulusci.core.source_transforms.transforms import FindReplaceTransform
from tasks.deploy import FindReplaceWithFilename

# Try to import CreatePackageVersion from common CumulusCI locations
# The import path varies by CumulusCI version, so we try multiple paths
_import_error = None
BaseCreatePackageVersion = None

# Try cumulusci.tasks.sfdx (most common for CumulusCI 3.78+)
try:
    from cumulusci.tasks.sfdx import CreatePackageVersion as BaseCreatePackageVersion
except ImportError as e1:
    _import_error = str(e1)
    # Try cumulusci.tasks.salesforce.package
    try:
        from cumulusci.tasks.salesforce.package import CreatePackageVersion as BaseCreatePackageVersion
    except ImportError as e2:
        # Try cumulusci.tasks.salesforce (direct)
        try:
            from cumulusci.tasks.salesforce import CreatePackageVersion as BaseCreatePackageVersion
        except ImportError as e3:
            # Last resort: use task registry
            try:
                from cumulusci.core.config import UniversalConfig, BaseProjectConfig
                universal_config = UniversalConfig()
                project_config = BaseProjectConfig(universal_config)
                task_config = project_config.get_task('create_package_version')
                BaseCreatePackageVersion = task_config.get_class()
            except Exception as e4:
                raise ImportError(
                    f"Could not import CreatePackageVersion from any known location.\n"
                    f"Tried: cumulusci.tasks.sfdx, cumulusci.tasks.salesforce.package, cumulusci.tasks.salesforce\n"
                    f"Errors: {e1}, {e2}, {e3}, {e4}\n"
                    f"Please check your CumulusCI installation and version."
                ) from e4

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
