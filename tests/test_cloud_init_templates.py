#!/usr/bin/env python3
"""Tests for the cloud-init template system."""

import tempfile
import unittest
from pathlib import Path

import yaml

from spot_deployer.core.deployment import DeploymentConfig
from spot_deployer.templates.cloud_init_templates import (
    CloudInitTemplate,
    TemplateInjector,
    TemplateLibrary,
)


class TestCloudInitTemplate(unittest.TestCase):
    """Test CloudInitTemplate functionality."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_path = Path(self.temp_dir.name)

    def tearDown(self):
        """Clean up test environment."""
        self.temp_dir.cleanup()

    def test_default_template(self):
        """Test using the default template."""
        template = CloudInitTemplate()
        rendered = template.render()

        self.assertIn("#cloud-config", rendered)
        self.assertIn("users:", rendered)
        self.assertIn("ubuntu", rendered)
        self.assertIn("/opt/deploy.sh", rendered)

    def test_load_template_from_file(self):
        """Test loading template from file."""
        template_file = self.test_path / "test.yaml"
        template_file.write_text("""#cloud-config
packages:
{{PACKAGES}}
runcmd:
  - echo "Test template"
""")

        template = CloudInitTemplate(template_file)
        rendered = template.render()

        self.assertIn('echo "Test template"', rendered)

    def test_variable_substitution(self):
        """Test variable substitution in templates."""
        template_file = self.test_path / "vars.yaml"
        template_file.write_text("""#cloud-config
write_files:
  - path: {{FILE_PATH}}
    content: |
      {{FILE_CONTENT}}
runcmd:
  - echo "{{MESSAGE}}"
""")

        template = CloudInitTemplate(template_file)
        template.set_variables(
            {
                "FILE_PATH": "/opt/test.txt",
                "FILE_CONTENT": "Hello World",
                "MESSAGE": "Deployment complete",
            }
        )

        rendered = template.render()

        self.assertIn("/opt/test.txt", rendered)
        self.assertIn("Hello World", rendered)
        self.assertIn("Deployment complete", rendered)
        self.assertNotIn("{{", rendered)  # No unsubstituted variables

    def test_deployment_config_variables(self):
        """Test automatic variables from deployment config."""
        template_file = self.test_path / "deploy.yaml"
        template_file.write_text("""#cloud-config
packages:
{{PACKAGES}}

runcmd:
{{SCRIPTS}}

# Services to start:
{{SERVICES}}
""")

        config = DeploymentConfig(
            version=1,
            packages=["nginx", "python3"],
            scripts=[{"command": "/opt/setup.sh", "working_dir": "/opt"}],
            uploads=[],
            services=[{"path": "/etc/systemd/system/app.service"}],
        )

        template = CloudInitTemplate(template_file)
        rendered = template.render(config)

        self.assertIn("- nginx", rendered)
        self.assertIn("- python3", rendered)
        self.assertIn("/opt/setup.sh", rendered)
        self.assertIn("app.service", rendered)

    def test_dollar_brace_syntax(self):
        """Test ${VAR} syntax support."""
        template_file = self.test_path / "dollar.yaml"
        template_file.write_text("""#cloud-config
runcmd:
  - echo "${MESSAGE}"
  - echo "Path: ${PATH}"
""")

        template = CloudInitTemplate(template_file)
        template.set_variables({"MESSAGE": "Hello", "PATH": "/opt/app"})

        rendered = template.render()

        self.assertIn("Hello", rendered)
        self.assertIn("/opt/app", rendered)
        self.assertNotIn("${", rendered)

    def test_add_single_variable(self):
        """Test adding variables one at a time."""
        template = CloudInitTemplate()
        template.add_variable("USER", "testuser")
        template.add_variable("DIR", "/home/testuser")

        # Override template content for testing
        template.template_content = "user: {{USER}}\ndir: {{DIR}}"

        rendered = template.render()

        self.assertIn("user: testuser", rendered)
        self.assertIn("dir: /home/testuser", rendered)

    def test_validate_valid_template(self):
        """Test validation of valid template."""
        template_file = self.test_path / "valid.yaml"
        template_file.write_text("""#cloud-config
packages:
  - nginx
""")

        template = CloudInitTemplate(template_file)
        is_valid, errors = template.validate()

        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    def test_validate_missing_file(self):
        """Test validation with missing template file."""
        template = CloudInitTemplate(self.test_path / "nonexistent.yaml")
        is_valid, errors = template.validate()

        self.assertFalse(is_valid)
        self.assertIn("not found", errors[0])

    def test_validate_unsubstituted_variables(self):
        """Test validation catches unsubstituted variables."""
        template = CloudInitTemplate()
        template.template_content = """#cloud-config
runcmd:
  - echo "{{UNDEFINED_VAR}}"
"""

        is_valid, errors = template.validate()

        self.assertFalse(is_valid)
        self.assertIn("UNDEFINED_VAR", errors[0])

    def test_validate_invalid_yaml(self):
        """Test validation catches invalid YAML."""
        template = CloudInitTemplate()
        template.template_content = """#cloud-config
packages:
  - nginx
  invalid yaml here
"""

        is_valid, errors = template.validate()

        self.assertFalse(is_valid)
        self.assertIn("not valid YAML", errors[0])

    def test_empty_deployment_config(self):
        """Test rendering with empty deployment config."""
        template = CloudInitTemplate()
        config = DeploymentConfig(version=1, packages=[], scripts=[], uploads=[], services=[])

        rendered = template.render(config)

        self.assertIn("#cloud-config", rendered)
        # Should still have structure even with empty config
        self.assertIn("users:", rendered)


class TestTemplateLibrary(unittest.TestCase):
    """Test TemplateLibrary functionality."""

    def test_list_templates(self):
        """Test listing available templates."""
        templates = TemplateLibrary.list_templates()

        # Should include our created templates
        self.assertIn("minimal", templates)
        self.assertIn("docker", templates)

    def test_get_template(self):
        """Test getting a template by name."""
        template = TemplateLibrary.get_template("minimal")

        self.assertIsInstance(template, CloudInitTemplate)
        self.assertTrue(template.template_path.exists())

        rendered = template.render()
        self.assertIn("Minimal deployment complete", rendered)

    def test_get_nonexistent_template(self):
        """Test getting a non-existent template."""
        with self.assertRaises(FileNotFoundError) as ctx:
            TemplateLibrary.get_template("nonexistent")

        self.assertIn("not found", str(ctx.exception))
        self.assertIn("Available templates", str(ctx.exception))

    def test_get_template_path(self):
        """Test getting template file path."""
        path = TemplateLibrary.get_template_path("minimal")

        self.assertTrue(path.exists())
        self.assertEqual(path.name, "minimal.yaml")


class TestTemplateInjector(unittest.TestCase):
    """Test TemplateInjector functionality."""

    def setUp(self):
        """Set up test environment."""
        self.base_template = """#cloud-config
packages:
  - git

runcmd:
  - echo "Base template"
"""

    def test_inject_packages(self):
        """Test injecting packages."""
        injector = TemplateInjector(self.base_template)
        injector.add_packages(["nginx", "python3"])

        result = injector.inject()

        # Should have both base and injected packages
        self.assertIn("git", result)
        self.assertIn("nginx", result)
        self.assertIn("python3", result)

    def test_inject_files(self):
        """Test injecting files."""
        injector = TemplateInjector(self.base_template)
        injector.add_file("/opt/test.txt", "Test content", "0644")

        result = injector.inject()

        self.assertIn("write_files:", result)
        self.assertIn("/opt/test.txt", result)
        self.assertIn("Test content", result)
        self.assertIn("0644", result)

    def test_inject_commands(self):
        """Test injecting commands."""
        injector = TemplateInjector(self.base_template)
        injector.add_command("mkdir -p /opt/app")
        injector.add_command("echo 'Injected'")

        result = injector.inject()

        # Should have both base and injected commands
        self.assertIn("Base template", result)
        self.assertIn("mkdir -p /opt/app", result)
        self.assertIn("echo 'Injected'", result)

    def test_inject_bootcmd(self):
        """Test injecting bootcmd commands."""
        injector = TemplateInjector(self.base_template)
        injector.add_command("modprobe vfio-pci", section="bootcmd")

        result = injector.inject()

        self.assertIn("bootcmd:", result)
        self.assertIn("modprobe vfio-pci", result)

    def test_inject_invalid_section(self):
        """Test injecting to invalid section raises error."""
        injector = TemplateInjector(self.base_template)

        with self.assertRaises(ValueError):
            injector.add_command("test", section="invalid")

    def test_inject_multiple_items(self):
        """Test injecting multiple items of different types."""
        injector = TemplateInjector(self.base_template)

        injector.add_packages(["docker", "curl"])
        injector.add_file("/etc/app.conf", "key=value", "0600")
        injector.add_command("systemctl start docker")

        result = injector.inject()

        self.assertIn("docker", result)
        self.assertIn("curl", result)
        self.assertIn("/etc/app.conf", result)
        self.assertIn("key=value", result)
        self.assertIn("systemctl start docker", result)

    def test_inject_preserves_yaml_structure(self):
        """Test that injection preserves valid YAML structure."""
        injector = TemplateInjector(self.base_template)

        injector.add_packages(["test"])
        injector.add_file("/test", "content", "0644")
        injector.add_command("test command")

        result = injector.inject()

        # Should be valid YAML
        parsed = yaml.safe_load(result)
        self.assertIsInstance(parsed, dict)
        self.assertIn("packages", parsed)
        self.assertIn("write_files", parsed)
        self.assertIn("runcmd", parsed)

    def test_inject_invalid_base_template(self):
        """Test injecting into invalid YAML returns original."""
        invalid_base = "not valid yaml {{ broken"

        injector = TemplateInjector(invalid_base)
        injector.add_packages(["test"])

        result = injector.inject()

        # Should return original when base is invalid
        self.assertEqual(result, invalid_base)

    def test_empty_injections(self):
        """Test injecting nothing doesn't modify template."""
        injector = TemplateInjector(self.base_template)

        result = injector.inject()

        # Should be effectively the same
        base_parsed = yaml.safe_load(self.base_template)
        result_parsed = yaml.safe_load(result)

        self.assertEqual(base_parsed, result_parsed)


if __name__ == "__main__":
    unittest.main()
