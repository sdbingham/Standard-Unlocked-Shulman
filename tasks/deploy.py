import io
import zipfile

from cumulusci.core.source_transforms.transforms import FindReplaceTransform
from cumulusci.tasks.salesforce.Deploy import Deploy as BaseDeployTask
from cumulusci.core.dependencies.utils import TaskContext


class FindReplaceWithFilename(FindReplaceTransform):
    """Extends the standard find_replace transform to also handle filenames."""

    def process(self, zf: zipfile.ZipFile, context: TaskContext) -> zipfile.ZipFile:
        # First do the normal find_replace on file contents
        zf = super().process(zf, context)

        # Then handle filenames
        zip_dest = zipfile.ZipFile(io.BytesIO(), "w", zipfile.ZIP_DEFLATED)
        for name in zf.namelist():
            content = zf.read(name)
            new_name = name

            # Apply each pattern to the filename
            for pattern in self.options.patterns:
                find = pattern.find
                if find and find in new_name:
                    replace = pattern.get_replace_string(context)
                    new_name = new_name.replace(find, replace)

            zip_dest.writestr(new_name, content)

        return zip_dest


# Patch CumulusCI's transform loading to automatically use filename-aware transforms
# This makes find_replace transforms work for filenames in all tasks (including create_package_version)
def _patch_transform_loading():
    """Patch transform instantiation to use filename-aware transforms for find_replace."""
    try:
        # Patch BaseTask to replace find_replace transforms with filename-aware version
        from cumulusci.core.tasks import BaseTask
        
        # Store original _init_options if not already stored
        if not hasattr(BaseTask, '_original_init_options_patched'):
            BaseTask._original_init_options_patched = BaseTask._init_options
        
        original_init_options = BaseTask._original_init_options_patched
        
        def patched_init_options(self, kwargs):
            """Patched _init_options that replaces find_replace transforms."""
            # Call original first
            original_init_options(self, kwargs)
            # After transforms are loaded, replace find_replace with filename-aware version
            if hasattr(self, 'transforms') and self.transforms:
                for i, transform in enumerate(self.transforms):
                    if isinstance(transform, FindReplaceTransform):
                        # Replace with filename-aware version, preserving options
                        self.transforms[i] = FindReplaceWithFilename(transform.options)
                        # Log for debugging (will show in GitHub Actions logs)
                        if hasattr(self, 'logger'):
                            self.logger.info(f"Replaced find_replace transform with filename-aware version in {self.__class__.__name__}")
        
        # Patch BaseTask._init_options
        BaseTask._init_options = patched_init_options
        
        # Also try patching the transform registry directly
        try:
            from cumulusci.core.source_transforms.transforms import TransformRegistry
            # Patch the registry's transform creation method
            if hasattr(TransformRegistry, 'get_transform'):
                original_get_transform = TransformRegistry.get_transform
                def patched_get_transform(self, transform_name, options):
                    transform = original_get_transform(self, transform_name, options)
                    if transform_name == 'find_replace' and isinstance(transform, FindReplaceTransform):
                        return FindReplaceWithFilename(options)
                    return transform
                TransformRegistry.get_transform = patched_get_transform
        except Exception:
            pass
        
    except Exception as e:
        # If patching fails, the Deploy class will still work
        # Silently fail - we'll rely on the Deploy class override instead
        pass

# Patch on module import - this ensures all tasks get filename-aware transforms
# This must run before any tasks are instantiated
_patch_transform_loading()


class Deploy(BaseDeployTask):
    """Deploy task that extends find_replace to also handle filenames."""

    def _init_options(self, kwargs):
        super()._init_options(kwargs)
        
        # Replace any find_replace transforms with our filename-aware version
        for i, transform in enumerate(self.transforms):
            if isinstance(transform, FindReplaceTransform):
                self.transforms[i] = FindReplaceWithFilename(transform.options) 