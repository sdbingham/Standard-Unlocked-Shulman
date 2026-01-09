from cumulusci.core.source_transforms.transforms import FindReplaceTransform
from cumulusci.tasks.sfdx import CreatePackageVersion as BaseCreatePackageVersion
from tasks.deploy import FindReplaceWithFilename


class CreatePackageVersion(BaseCreatePackageVersion):
    """CreatePackageVersion task that extends find_replace to also handle filenames."""

    def _init_options(self, kwargs):
        super()._init_options(kwargs)
        
        # Replace any find_replace transforms with our filename-aware version
        for i, transform in enumerate(self.transforms):
            if isinstance(transform, FindReplaceTransform):
                self.transforms[i] = FindReplaceWithFilename(transform.options)
