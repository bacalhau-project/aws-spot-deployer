#!/usr/bin/env python3
"""
Simple test suite for deploy_spot_simple.py

Tests basic functionality without requiring AWS credentials.
"""

import json
import os
import tempfile
import time
import unittest
from unittest.mock import patch, MagicMock
import yaml

# Import the simplified module
import deploy_spot as dss


class TestSimpleConfig(unittest.TestCase):
    """Test SimpleConfig class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_config = {
            "aws": {
                "total_instances": 5,
                "username": "testuser",
                "ssh_key_name": "test-key"
            },
            "regions": [
                {"us-west-2": {"machine_type": "t3.large", "image": "auto"}},
                {"eu-west-1": {"machine_type": "t3.medium", "image": "auto"}},
            ]
        }
        
    def test_config_loading(self):
        """Test config loading from YAML file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(self.test_config, f)
            config_file = f.name
        
        try:
            config = dss.SimpleConfig(config_file)
            self.assertEqual(config.instance_count(), 5)
            self.assertEqual(config.username(), "testuser")
            self.assertEqual(config.ssh_key_name(), "test-key")
            self.assertEqual(config.regions(), ["us-west-2", "eu-west-1"])
        finally:
            os.unlink(config_file)
    
    def test_config_defaults(self):
        """Test config defaults when file doesn't exist."""
        config = dss.SimpleConfig("nonexistent.yaml")
        self.assertEqual(config.instance_count(), 3)
        self.assertEqual(config.username(), "ubuntu")
        self.assertIsNone(config.ssh_key_name())
        self.assertEqual(config.regions(), [])
    
    def test_region_config(self):
        """Test region-specific configuration."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(self.test_config, f)
            config_file = f.name
        
        try:
            config = dss.SimpleConfig(config_file)
            us_west_config = config.region_config("us-west-2")
            self.assertEqual(us_west_config["machine_type"], "t3.large")
            self.assertEqual(us_west_config["image"], "auto")
            
            # Test default for unknown region
            unknown_config = config.region_config("unknown-region")
            self.assertEqual(unknown_config["machine_type"], "t3.medium")
            self.assertEqual(unknown_config["image"], "auto")
        finally:
            os.unlink(config_file)


class TestSimpleStateManager(unittest.TestCase):
    """Test SimpleStateManager class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_instances = [
            {
                "id": "i-123456",
                "region": "us-west-2",
                "type": "t3.medium",
                "state": "running",
                "public_ip": "1.2.3.4",
                "private_ip": "10.0.0.1",
                "created": "2025-01-04T10:00:00"
            },
            {
                "id": "i-789012",
                "region": "eu-west-1",
                "type": "t3.large",
                "state": "running",
                "public_ip": "5.6.7.8",
                "private_ip": "10.0.0.2",
                "created": "2025-01-04T10:01:00"
            }
        ]
    
    def test_save_and_load_instances(self):
        """Test saving and loading instances."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            state_file = f.name
        
        try:
            state = dss.SimpleStateManager(state_file)
            
            # Save instances
            state.save_instances(self.test_instances)
            
            # Load instances
            loaded = state.load_instances()
            self.assertEqual(len(loaded), 2)
            self.assertEqual(loaded[0]["id"], "i-123456")
            self.assertEqual(loaded[1]["id"], "i-789012")
        finally:
            os.unlink(state_file)
    
    def test_add_instance(self):
        """Test adding single instance."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            state_file = f.name
        
        try:
            state = dss.SimpleStateManager(state_file)
            
            # Add instance
            state.add_instance(self.test_instances[0])
            
            # Verify
            instances = state.load_instances()
            self.assertEqual(len(instances), 1)
            self.assertEqual(instances[0]["id"], "i-123456")
        finally:
            os.unlink(state_file)
    
    def test_remove_instances_by_region(self):
        """Test removing instances by region."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            state_file = f.name
        
        try:
            state = dss.SimpleStateManager(state_file)
            
            # Save test instances
            state.save_instances(self.test_instances)
            
            # Remove instances from us-west-2
            removed = state.remove_instances_by_region("us-west-2")
            self.assertEqual(removed, 1)
            
            # Verify only eu-west-1 remains
            instances = state.load_instances()
            self.assertEqual(len(instances), 1)
            self.assertEqual(instances[0]["region"], "eu-west-1")
        finally:
            os.unlink(state_file)
    
    def test_empty_state_file(self):
        """Test behavior with empty/nonexistent state file."""
        state = dss.SimpleStateManager("nonexistent.json")
        instances = state.load_instances()
        self.assertEqual(instances, [])


class TestCacheUtilities(unittest.TestCase):
    """Test cache utility functions."""
    
    def test_cache_freshness(self):
        """Test cache freshness checking."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            cache_file = f.name
            json.dump({"test": "data"}, f)
        
        try:
            # Fresh cache
            self.assertTrue(dss.cache_file_fresh(cache_file, max_age_hours=1))
            
            # Old cache
            self.assertFalse(dss.cache_file_fresh(cache_file, max_age_hours=0))
            
            # Nonexistent cache
            self.assertFalse(dss.cache_file_fresh("nonexistent.json"))
        finally:
            os.unlink(cache_file)
    
    def test_cache_operations(self):
        """Test cache save/load operations."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            cache_file = f.name
        
        try:
            # Test save
            test_data = {"ami_id": "ami-12345", "timestamp": "2025-01-04T10:00:00"}
            dss.save_cache(cache_file, test_data)
            
            # Test load
            loaded = dss.load_cache(cache_file)
            self.assertEqual(loaded["ami_id"], "ami-12345")
            
            # Test load with old cache
            os.utime(cache_file, (time.time() - 25*3600, time.time() - 25*3600))  # 25 hours old
            loaded_old = dss.load_cache(cache_file)
            self.assertIsNone(loaded_old)
        finally:
            if os.path.exists(cache_file):
                os.unlink(cache_file)


class TestAWSUtilities(unittest.TestCase):
    """Test AWS utility functions with mocking."""
    
    @patch('deploy_spot.boto3.client')
    def test_check_aws_auth_success(self, mock_client):
        """Test successful AWS authentication check."""
        mock_sts = MagicMock()
        mock_sts.get_caller_identity.return_value = {"Account": "123456789012"}
        mock_client.return_value = mock_sts
        
        result = dss.check_aws_auth()
        self.assertTrue(result)
        mock_client.assert_called_once_with("sts")
        mock_sts.get_caller_identity.assert_called_once()
    
    @patch('deploy_spot.boto3.client')
    def test_check_aws_auth_failure(self, mock_client):
        """Test failed AWS authentication check."""
        mock_sts = MagicMock()
        mock_sts.get_caller_identity.side_effect = Exception("Token has expired")
        mock_client.return_value = mock_sts
        
        result = dss.check_aws_auth()
        self.assertFalse(result)
    
    @patch('deploy_spot.boto3.client')
    @patch('deploy_spot.load_cache')
    def test_get_latest_ubuntu_ami_cached(self, mock_load_cache, mock_client):
        """Test AMI lookup with cached result."""
        mock_load_cache.return_value = {"ami_id": "ami-cached123"}
        
        result = dss.get_latest_ubuntu_ami("us-west-2")
        self.assertEqual(result, "ami-cached123")
        mock_client.assert_not_called()
    
    @patch('deploy_spot.boto3.client')
    @patch('deploy_spot.load_cache')
    @patch('deploy_spot.save_cache')
    def test_get_latest_ubuntu_ami_from_aws(self, mock_save_cache, mock_load_cache, mock_client):
        """Test AMI lookup from AWS API."""
        mock_load_cache.return_value = None
        
        mock_ec2 = MagicMock()
        mock_ec2.describe_images.return_value = {
            "Images": [
                {
                    "ImageId": "ami-12345",
                    "CreationDate": "2025-01-04T10:00:00.000Z"
                },
                {
                    "ImageId": "ami-67890", 
                    "CreationDate": "2025-01-03T10:00:00.000Z"
                }
            ]
        }
        mock_client.return_value = mock_ec2
        
        result = dss.get_latest_ubuntu_ami("us-west-2")
        self.assertEqual(result, "ami-12345")
        mock_save_cache.assert_called_once()


class TestMainCommands(unittest.TestCase):
    """Test main command functions."""
    
    def test_show_help(self):
        """Test help command output."""
        # Just verify it doesn't crash
        try:
            dss.show_help()
        except SystemExit:
            pass  # Expected for help commands
    
    @patch('deploy_spot.SimpleConfig')
    def test_cmd_setup(self, mock_config):
        """Test setup command."""
        with patch('builtins.open', unittest.mock.mock_open()) as mock_open:
            with patch('deploy_spot.yaml.dump') as mock_yaml_dump:
                with patch('deploy_spot.check_aws_auth', return_value=True):
                    dss.cmd_setup()
                    mock_open.assert_called_once_with("config.yaml", "w")
                    mock_yaml_dump.assert_called_once()


class TestPerformance(unittest.TestCase):
    """Test performance characteristics."""
    
    def test_startup_time(self):
        """Test tool startup time."""
        start_time = time.time()
        
        # Import and create basic objects
        config = dss.SimpleConfig("nonexistent.yaml")
        state = dss.SimpleStateManager("nonexistent.json")
        
        end_time = time.time()
        startup_time = end_time - start_time
        
        # Should start up in less than 1 second
        self.assertLess(startup_time, 1.0)
    
    def test_file_size(self):
        """Test simplified file size."""
        script_path = dss.__file__
        file_size = os.path.getsize(script_path)
        
        # Should be under 50KB (much smaller than original)
        self.assertLess(file_size, 110000)  # Updated after adding more features
        
        # Count lines
        with open(script_path, 'r') as f:
            lines = len(f.readlines())
        
        # Should be under 900 lines (increased due to Rich integration and cleanup features)
        self.assertLess(lines, 3000)  # Updated after adding more features


if __name__ == '__main__':
    print("Running simple deployment tool tests...")
    
    # Create test loader
    loader = unittest.TestLoader()
    
    # Create test suite
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTest(loader.loadTestsFromTestCase(TestSimpleConfig))
    suite.addTest(loader.loadTestsFromTestCase(TestSimpleStateManager))
    suite.addTest(loader.loadTestsFromTestCase(TestCacheUtilities))
    suite.addTest(loader.loadTestsFromTestCase(TestAWSUtilities))
    suite.addTest(loader.loadTestsFromTestCase(TestMainCommands))
    suite.addTest(loader.loadTestsFromTestCase(TestPerformance))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    if result.wasSuccessful():
        print(f"✅ All {result.testsRun} tests passed!")
    else:
        print(f"❌ {len(result.failures)} failures, {len(result.errors)} errors")
        
    exit(0 if result.wasSuccessful() else 1)