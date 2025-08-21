"""Validate command - validates deployment configuration before deployment."""

from pathlib import Path

from ..core.config import SimpleConfig
from ..core.deployment_discovery import DeploymentDiscovery, DeploymentMode
from ..core.state import SimpleStateManager
from ..utils.config_validator import ConfigValidator
from ..utils.display import console, rich_error, rich_print, rich_success, rich_warning
from ..utils.file_uploader import FileUploader


def cmd_validate(config: SimpleConfig, state: SimpleStateManager) -> None:
    """Validate deployment configuration and structure."""
    console.print("[bold]🔍 Validating Deployment Configuration[/bold]\n")

    errors = []
    warnings = []

    # 1. Check deployment discovery
    console.print("Checking deployment structure...")
    discovery = DeploymentDiscovery()
    discovery_result = discovery.discover()

    if discovery_result.mode == DeploymentMode.NONE:
        errors.append("No deployment structure found (.spot/ or deployment/ directory)")
        rich_error("❌ No deployment structure found")
        rich_print("\n[yellow]Run 'spot generate' to create the required structure.[/yellow]")
        return

    if discovery_result.mode == DeploymentMode.PORTABLE:
        rich_success("✅ Found portable deployment (.spot directory)")
    elif discovery_result.mode == DeploymentMode.CONVENTION:
        rich_success("✅ Found convention-based deployment (deployment/ directory)")

    # Check for validation errors from discovery
    if discovery_result.validation_errors:
        for error in discovery_result.validation_errors:
            errors.append(error)
            rich_error(f"  • {error}")

    deployment_config = discovery_result.deployment_config
    if not deployment_config:
        errors.append("Failed to load deployment configuration")
        rich_error("❌ Failed to load deployment configuration")
        return

    # 2. Validate AWS configuration
    console.print("\nValidating AWS configuration...")
    validator = ConfigValidator()
    config_path = config.config_file
    is_valid, validation_errors = validator.validate_config_file(config_path)

    if is_valid:
        rich_success("✅ AWS configuration is valid")
    else:
        errors.extend(validation_errors)
        for error in validation_errors:
            rich_error(f"  • {error}")

    # 3. Validate deployment configuration
    console.print("\nValidating deployment manifest...")
    is_valid, validation_errors = deployment_config.validate()

    if is_valid:
        rich_success("✅ Deployment manifest is valid")
    else:
        errors.extend(validation_errors)
        for error in validation_errors:
            rich_error(f"  • {error}")

    # 4. Check referenced files exist
    console.print("\nChecking referenced files...")
    missing_files = []

    # Check scripts
    for script in deployment_config.scripts:
        script_path = deployment_config.spot_dir / script.get("path", "")
        if script_path and not script_path.exists():
            missing_files.append(f"Script: {script_path}")

    # Check services
    for service in deployment_config.services:
        service_file = service.get("file", "")
        if service_file:
            service_path = deployment_config.spot_dir / service_file
            if not service_path.exists():
                missing_files.append(f"Service: {service_path}")

    # Check uploads
    for upload in deployment_config.uploads:
        source = upload.get("source", "")
        if source:
            source_path = deployment_config.spot_dir / source
            if not source_path.exists():
                missing_files.append(f"Upload: {source_path}")

    if missing_files:
        errors.extend(missing_files)
        rich_error("❌ Missing files:")
        for file in missing_files:
            rich_error(f"  • {file}")
    else:
        rich_success("✅ All referenced files exist")

    # 5. Validate tarball source if specified
    if hasattr(deployment_config, "tarball_source") and deployment_config.tarball_source:
        console.print("\nValidating tarball source...")
        source_path = Path(deployment_config.tarball_source)

        if not source_path.exists():
            errors.append(f"Tarball source not found: {source_path}")
            rich_error(f"❌ Tarball source not found: {source_path}")
        elif not source_path.is_dir():
            errors.append(f"Tarball source must be a directory: {source_path}")
            rich_error(f"❌ Tarball source must be a directory: {source_path}")
        else:
            rich_success(f"✅ Tarball source is valid: {source_path}")

    # 6. Check file upload configuration
    if deployment_config.uploads:
        console.print("\nValidating file uploads...")
        uploader = FileUploader(deployment_config, deployment_config.spot_dir)
        is_valid, upload_errors = uploader.validate_uploads()

        if is_valid:
            # Estimate upload size
            total_size = uploader.estimate_upload_size()
            size_mb = total_size / (1024 * 1024)
            rich_success(f"✅ File uploads valid ({size_mb:.1f} MB)")
        else:
            errors.extend(upload_errors)
            for error in upload_errors:
                rich_error(f"  • {error}")

    # 7. Check for recommended files
    console.print("\nChecking recommended files...")
    recommended = {
        deployment_config.spot_dir / "scripts" / "setup.sh": "Main setup script",
        deployment_config.spot_dir / "README.md": "Documentation",
    }

    for file_path, description in recommended.items():
        if not file_path.exists():
            warnings.append(f"Recommended: {description} ({file_path})")
            rich_warning(f"⚠️  Missing {description}")

    # 8. Summary
    console.print("\n" + "=" * 50)
    console.print("[bold]Validation Summary[/bold]\n")

    if not errors and not warnings:
        rich_success("✅ All validation checks passed!")
        rich_print("\n[green]Your deployment is ready. Run 'spot create' to deploy.[/green]")
    elif not errors:
        rich_success(f"✅ Validation passed with {len(warnings)} warning(s)")
        rich_print("\n[yellow]Warnings:[/yellow]")
        for warning in warnings:
            rich_print(f"  • {warning}")
        rich_print("\n[green]Your deployment should work. Run 'spot create' to deploy.[/green]")
    else:
        rich_error(f"❌ Validation failed with {len(errors)} error(s)")
        if warnings:
            rich_warning(f"   Plus {len(warnings)} warning(s)")

        rich_print("\n[red]Errors must be fixed before deployment:[/red]")
        for error in errors[:10]:  # Show first 10 errors
            rich_print(f"  • {error}")
        if len(errors) > 10:
            rich_print(f"  ... and {len(errors) - 10} more errors")

        if warnings:
            rich_print("\n[yellow]Warnings:[/yellow]")
            for warning in warnings[:5]:  # Show first 5 warnings
                rich_print(f"  • {warning}")
            if len(warnings) > 5:
                rich_print(f"  ... and {len(warnings) - 5} more warnings")

        rich_print("\n[red]Fix the errors above and run 'spot validate' again.[/red]")
