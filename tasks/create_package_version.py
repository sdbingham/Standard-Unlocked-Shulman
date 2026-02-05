import io
import os
import shutil
import zipfile
import tempfile
from pathlib import Path

from cumulusci.core.source_transforms.transforms import FindReplaceTransform
from cumulusci.core.dependencies.utils import TaskContext

# Import the base class - CumulusCI uses CreatePackageVersion as the base class
from cumulusci.tasks.create_package_version import CreatePackageVersion as BaseCreatePackageVersion


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


class CreatePackageVersion(BaseCreatePackageVersion):
    """Create package version task that extends find_replace to also handle filenames."""

    def _init_options(self, kwargs):
        super()._init_options(kwargs)
        
        # CreatePackageVersion doesn't support transforms like Deploy does
        # We need to apply transforms manually during the packaging process
        # Store transform config for later use
        self._transforms_config = self.options.get('transforms', [])
        if self._transforms_config:
            self.logger.info(f"[TRANSFORM] Transforms configured: {len(self._transforms_config)} transform(s)")
        else:
            self.logger.warning("[TRANSFORM] No transforms found in options")
        
    def _run_task(self):
        """Override _run_task to apply transforms during packaging."""
        # Apply transforms to a temporary copy of source files before packaging
        if self._transforms_config:
            self.logger.info("[TRANSFORM] Applying transforms to source files before packaging...")
            temp_source_dir = None
            original_force_app = Path("force-app")
            backup_force_app = Path("force-app.backup")
            
            # Step 1: Apply transforms to temp directory (catch transform errors here)
            try:
                temp_source_dir = self._apply_transforms_to_temp_source()
                if not temp_source_dir:
                    self.logger.warning("[TRANSFORM] Failed to create transformed source, continuing without transforms")
                    return super()._run_task()
            except Exception as e:
                # Transform application failed - log and continue without transforms
                self.logger.error(f"[TRANSFORM] Error applying transforms: {e}")
                import traceback
                self.logger.error(traceback.format_exc())
                self.logger.warning("[TRANSFORM] Continuing without transforms")
                return super()._run_task()
            
            # Step 2: Swap force-app with transformed version
            try:
                if backup_force_app.exists():
                    shutil.rmtree(backup_force_app)
                original_force_app.rename(backup_force_app)
                shutil.copytree(temp_source_dir / "force-app", original_force_app)
            except Exception as e:
                # File swap failed - clean up and continue without transforms
                self.logger.error(f"[TRANSFORM] Error swapping files: {e}")
                if temp_source_dir and temp_source_dir.exists():
                    shutil.rmtree(temp_source_dir)
                self.logger.warning("[TRANSFORM] Continuing without transforms")
                return super()._run_task()
            
            # Step 3: Call parent task (let Salesforce API errors propagate normally)
            try:
                result = super()._run_task()
                
                # Success - clean up and return
                if temp_source_dir and temp_source_dir.exists():
                    shutil.rmtree(temp_source_dir)
                self.logger.info("[TRANSFORM] Transforms applied successfully")
                return result
            finally:
                # Always restore original files, even if parent task fails
                if backup_force_app.exists():
                    if original_force_app.exists():
                        shutil.rmtree(original_force_app)
                    backup_force_app.rename(original_force_app)
                if temp_source_dir and temp_source_dir.exists():
                    shutil.rmtree(temp_source_dir)
        
        # Call parent to do the actual packaging (no transforms)
        return super()._run_task()
    
    def _apply_transforms_to_temp_source(self):
        """Apply transforms to a temporary copy of source files."""
        
        # Get the source directory (force-app)
        source_dir = Path("force-app")
        if not source_dir.exists():
            self.logger.warning("[TRANSFORM] Source directory not found, skipping transforms")
            return None
        
        # Create temporary directory
        temp_dir = Path(tempfile.mkdtemp())
        temp_source = temp_dir / "force-app"
        
        # Copy source files to temp directory
        shutil.copytree(source_dir, temp_source)
        
        # Create context for transforms
        context = self
        
        # Process each transform
        for transform_config in self._transforms_config:
            if transform_config.get('transform') == 'find_replace':
                transform = FindReplaceWithFilename(
                    self._create_transform_options(transform_config.get('options', {}))
                )
                # Apply to all metadata files in temp directory
                self._apply_transform_to_directory(temp_source, transform, context)
        
        return temp_dir
    
    def _apply_transform_to_directory(self, directory, transform, context):
        """Apply transform to all files in a directory, including renaming files."""
        # Create a temporary zip with all files
        temp_zip = io.BytesIO()
        with zipfile.ZipFile(temp_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file_path in directory.rglob('*'):
                if file_path.is_file():
                    rel_path = file_path.relative_to(directory)
                    zf.writestr(str(rel_path), file_path.read_bytes())
        
        # Apply transform
        temp_zip.seek(0)
        with zipfile.ZipFile(temp_zip, 'r') as zf_in:
            zf_transformed = transform.process(zf_in, context)
            
            # Write transformed files back
            for name in zf_transformed.namelist():
                new_path = directory / name
                new_path.parent.mkdir(parents=True, exist_ok=True)
                new_path.write_bytes(zf_transformed.read(name))
                
                # If filename changed, remove old file
                # Find old name by checking if a file with the original token name exists
                old_name = name.replace(
                    self.project_config.project__package__name,
                    "__PROJECT_NAME__"
                ).replace(
                    self.project_config.project__package__name_managed.replace(" ", ""),
                    "__PROJECT_LABEL__"
                )
                if old_name != name:
                    old_path = directory / old_name
                    if old_path.exists() and old_path != new_path:
                        old_path.unlink()
    
    def _apply_transforms_to_mdapi_dir(self, mdapi_dir):
        """Apply transforms to files in MDAPI directory, including filenames."""
        from pathlib import Path
        
        # Create a zip from the MDAPI directory
        temp_zip = io.BytesIO()
        with zipfile.ZipFile(temp_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
            mdapi_path = Path(mdapi_dir)
            for file_path in mdapi_path.rglob('*'):
                if file_path.is_file():
                    rel_path = file_path.relative_to(mdapi_path)
                    zf.writestr(str(rel_path), file_path.read_bytes())
        
        # Apply transforms
        temp_zip.seek(0)
        with zipfile.ZipFile(temp_zip, 'r') as zf_in:
            # Use self as context since it has project_config and org_config
            context = self
            
            zf_transformed = zf_in
            for transform_config in self._transforms_config:
                if transform_config.get('transform') == 'find_replace':
                    transform = FindReplaceWithFilename(
                        self._create_transform_options(transform_config.get('options', {}))
                    )
                    zf_transformed = transform.process(zf_transformed, context)
            
            # Write transformed files back to MDAPI directory
            mdapi_path = Path(mdapi_dir)
            for name in zf_transformed.namelist():
                new_path = mdapi_path / name
                new_path.parent.mkdir(parents=True, exist_ok=True)
                new_path.write_bytes(zf_transformed.read(name))
                
                # Remove old file if name changed
                # Find old name by reversing the transform
                old_name = name
                for transform_config in self._transforms_config:
                    if transform_config.get('transform') == 'find_replace':
                        for pattern in transform_config.get('options', {}).get('patterns', []):
                            find = pattern.get('find')
                            replace = pattern.get('replace')
                            if replace and find:
                                # Try to reverse the replacement
                                if isinstance(replace, str) and replace.startswith('$project_config.'):
                                    # Get actual value
                                    attr = replace.replace('$project_config.', '')
                                    parts = attr.split('__')
                                    value = self.project_config
                                    for part in parts:
                                        if hasattr(value, part):
                                            value = getattr(value, part)
                                        elif isinstance(value, dict) and part in value:
                                            value = value[part]
                                        else:
                                            value = None
                                            break
                                    if value and str(value) in old_name:
                                        old_name = old_name.replace(str(value), find)
                
                if old_name != name:
                    old_path = mdapi_path / old_name
                    if old_path.exists() and old_path != new_path:
                        old_path.unlink()
    
    def _create_transform_options(self, options):
        """Create transform options object from config."""
        from cumulusci.core.source_transforms.transforms import FindReplaceTransformOptions, FindReplaceSpec
        
        # Create FindReplaceSpec objects from patterns
        patterns = []
        for pattern in options.get('patterns', []):
            patterns.append(FindReplaceSpec(
                find=pattern.get('find'),
                replace=pattern.get('replace')
            ))
        
        # Create options with patterns
        return FindReplaceTransformOptions(patterns=patterns)
