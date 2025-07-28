#!/usr/bin/env uv run
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
    commands = ["create", "destroy", "list", "setup", "help", "readme"]
    for cmd in commands:
        try:
            module = __import__(f"spot_deployer.commands.{cmd}", fromlist=[f"cmd_{cmd}"])
            if not hasattr(module, f"cmd_{cmd}"):
                errors.append((cmd, f"Missing cmd_{cmd} function"))
        except ImportError as e:
            errors.append((cmd, str(e)))

    # Test critical utilities
    utils = [
        ("aws", ["check_aws_auth"]),
        ("tables", ["create_instance_table", "add_instance_row", "add_destroy_row"]),
        ("display", ["console", "rich_print", "rich_error", "rich_success"]),
        ("logging", ["setup_logger", "ConsoleLogger"]),
        ("ssh", ["wait_for_ssh_only", "transfer_files_scp"]),
        ("cloud_init", ["generate_minimal_cloud_init"]),
    ]

    for util_module, functions in utils:
        try:
            module = __import__(f"spot_deployer.utils.{util_module}", fromlist=functions)
            for func in functions:
                if not hasattr(module, func):
                    errors.append((f"utils.{util_module}", f"Missing {func} function"))
        except ImportError as e:
            errors.append((f"utils.{util_module}", str(e)))

    # Test core modules
    core_modules = [
        ("config", ["SimpleConfig"]),
        ("state", ["SimpleStateManager"]),
        ("constants", ["DEFAULT_CONFIG_FILE", "ColumnWidths"]),
    ]

    for core_module, attrs in core_modules:
        try:
            module = __import__(f"spot_deployer.core.{core_module}", fromlist=attrs)
            for attr in attrs:
                if not hasattr(module, attr):
                    errors.append((f"core.{core_module}", f"Missing {attr}"))
        except ImportError as e:
            errors.append((f"core.{core_module}", str(e)))

    return errors


def test_table_consistency():
    """Test that table functions are consistent."""
    from spot_deployer.utils.tables import create_instance_table

    # Create a table and check it has the expected columns
    table = create_instance_table("Test Table")
    expected_columns = ["Region", "Instance ID", "Status", "Type", "Public IP", "Created"]

    actual_columns = [col.header for col in table.columns]

    if actual_columns != expected_columns:
        return f"Table columns mismatch: expected {expected_columns}, got {actual_columns}"

    return None


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

    # Test table consistency
    table_error = test_table_consistency()
    if table_error:
        print(f"\n❌ Table consistency error: {table_error}")
        sys.exit(1)
    elif not quiet:
        print("✅ Table structure consistent")

    # Test that commands are callable (skip help output in quiet mode)
    if quiet:
        # Just verify the import works
        try:
            from spot_deployer.commands import cmd_help
        except Exception as e:
            print(f"❌ Help command import failed: {e}")
            sys.exit(1)
    else:
        try:
            from spot_deployer.commands import cmd_help

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
