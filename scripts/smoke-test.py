#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Quick smoke test to catch import errors and basic issues."""

import sys
from typing import List, Tuple


def test_imports() -> List[Tuple[str, str]]:
    """Test all critical imports."""
    errors = []

    # Test main entry point
    try:
        import spot_deployer.main

        if not hasattr(spot_deployer.main, "main"):
            errors.append(("main", "Missing main function"))
    except ImportError as e:
        errors.append(("main", str(e)))

    # Test all commands
    commands = [
        "create",
        "destroy",
        "list",
        "setup",
        "help",
        "readme",
        "version",
        "validate",
        "nuke",
    ]
    for cmd in commands:
        try:
            module = __import__(f"spot_deployer.commands.{cmd}", fromlist=[f"cmd_{cmd}"])
            if not hasattr(module, f"cmd_{cmd}"):
                errors.append((cmd, f"Missing cmd_{cmd} function"))
        except ImportError as e:
            errors.append((cmd, str(e)))

    # Test generate command separately (uses 'main' instead of 'cmd_generate')
    try:
        module = __import__("spot_deployer.commands.generate", fromlist=["main"])
        if not hasattr(module, "main"):
            errors.append(("generate", "Missing main function"))
    except ImportError as e:
        errors.append(("generate", str(e)))

    # Test core modules
    core_modules = [
        ("config", ["SimpleConfig"]),
        ("state", ["SimpleStateManager"]),
        ("constants", ["DEFAULT_CONFIG_FILE", "DEFAULT_STATE_FILE"]),
        ("deployment", ["DeploymentConfig"]),
        ("deployment_discovery", ["DeploymentDiscovery", "DeploymentMode"]),
        ("convention_scanner", ["ConventionScanner"]),
    ]

    for core_module, attrs in core_modules:
        try:
            module = __import__(f"spot_deployer.core.{core_module}", fromlist=attrs)
            for attr in attrs:
                if not hasattr(module, attr):
                    errors.append((f"core.{core_module}", f"Missing {attr}"))
        except ImportError as e:
            errors.append((f"core.{core_module}", str(e)))

    # Test utilities
    utils = [
        ("aws_manager", ["AWSResourceManager"]),
        ("ssh_manager", ["SSHManager"]),
        ("ui_manager", ["UIManager"]),
        ("portable_cloud_init", ["PortableCloudInitGenerator"]),
        ("config_validator", ["ConfigValidator"]),
        ("display", ["rich_print", "rich_error", "rich_success"]),
        ("tables", ["create_instance_table", "add_instance_row"]),
        ("logging", ["setup_logger", "ConsoleLogger"]),
        ("tarball_handler", ["TarballHandler"]),
        ("shutdown_handler", ["ShutdownHandler"]),
        ("file_uploader", ["FileUploader"]),
        ("service_installer", ["ServiceInstaller"]),
    ]

    for util_module, functions in utils:
        try:
            module = __import__(f"spot_deployer.utils.{util_module}", fromlist=functions)
            for func in functions:
                if not hasattr(module, func):
                    errors.append((f"utils.{util_module}", f"Missing {func}"))
        except ImportError as e:
            errors.append((f"utils.{util_module}", str(e)))

    # Test templates
    template_modules = [
        ("cloud_init_templates", ["CloudInitTemplate"]),
    ]

    for template_module, attrs in template_modules:
        try:
            module = __import__(f"spot_deployer.templates.{template_module}", fromlist=attrs)
            for attr in attrs:
                if not hasattr(module, attr):
                    errors.append((f"templates.{template_module}", f"Missing {attr}"))
        except ImportError as e:
            errors.append((f"templates.{template_module}", str(e)))

    return errors


def test_deployment_discovery():
    """Test deployment discovery functionality."""
    try:
        from spot_deployer.core.deployment_discovery import DeploymentDiscovery

        dd = DeploymentDiscovery()
        result = dd.discover()

        # Just check that it returns something and has the expected attributes
        if not hasattr(result, "mode"):
            return "DeploymentDiscoveryResult missing 'mode' attribute"
        if not hasattr(result, "deployment_config"):
            return "DeploymentDiscoveryResult missing 'deployment_config' attribute"

        return None
    except Exception as e:
        return str(e)


def test_config_validator():
    """Test config validator functionality."""
    try:
        import os
        import tempfile

        from spot_deployer.utils.config_validator import ConfigValidator

        # Create a temporary empty config file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("# Empty config\n")
            temp_path = f.name

        try:
            validator = ConfigValidator()
            is_valid, config = validator.validate_config_file(temp_path)

            # Empty config should not be valid
            if is_valid:
                return "ConfigValidator should report errors for empty config"

            return None
        finally:
            os.unlink(temp_path)
    except Exception as e:
        return str(e)


def main():
    """Run smoke tests."""
    # Check if running in quiet mode (for pre-commit)
    quiet = "--quiet" in sys.argv

    if not quiet:
        print("🔍 Running smoke tests...")

    # Test imports
    import_errors = test_imports()
    if import_errors:
        print("\n❌ Import errors found:")
        for module, error in import_errors:
            print(f"  - {module}: {error}")
        sys.exit(1)
    elif not quiet:
        print("✅ All imports successful")

    # Test deployment discovery
    dd_error = test_deployment_discovery()
    if dd_error:
        print(f"\n❌ Deployment discovery error: {dd_error}")
        sys.exit(1)
    elif not quiet:
        print("✅ Deployment discovery working")

    # Test config validator
    cv_error = test_config_validator()
    if cv_error:
        print(f"\n❌ Config validator error: {cv_error}")
        sys.exit(1)
    elif not quiet:
        print("✅ Config validator working")

    # Test that help command is callable
    if not quiet:
        try:
            from spot_deployer.commands.help import cmd_help

            # This should work without any setup
            cmd_help()
            print("✅ Help command callable")
        except Exception as e:
            print(f"❌ Help command failed: {e}")
            sys.exit(1)

    if not quiet:
        print("\n✨ All smoke tests passed!")


if __name__ == "__main__":
    main()
