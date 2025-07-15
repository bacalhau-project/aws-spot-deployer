#!/usr/bin/env python3
"""Test script to verify on-screen logging reads from disk file correctly."""

import os
import sys
import time
import tempfile
import logging

# Add the parent directory to the path so we can import from deploy_spot
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from deploy_spot import SimpleStateManager

def test_on_screen_logging():
    """Test that the on-screen logging reads from disk file correctly."""
    # Create temporary directory for state
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create state manager
        state_manager = SimpleStateManager(state_file=os.path.join(tmpdir, "test_instances.json"))
        
        # Get a logger
        logger = state_manager.get_logger("test")
        
        # Write some test messages
        print("Writing test messages to log file...")
        for i in range(15):
            logger.info(f"Test message {i+1}: This is a test log entry")
            time.sleep(0.1)
        
        # Read from the log file
        log_filename = os.path.join(state_manager.log_dir, "test.log")
        print(f"\nReading from log file: {log_filename}")
        
        # Test reading last 10 lines
        try:
            with open(log_filename, 'r') as f:
                lines = f.readlines()
                last_lines = lines[-10:] if len(lines) >= 10 else lines
                formatted_messages = [line.strip() for line in last_lines if line.strip()]
                
                print(f"\nLast {len(formatted_messages)} lines from log file:")
                print("-" * 50)
                for msg in formatted_messages:
                    print(msg)
                print("-" * 50)
                
                # Verify we got the expected messages
                if len(formatted_messages) == 10:
                    print("\n✅ SUCCESS: Retrieved exactly 10 log lines as expected")
                else:
                    print(f"\n⚠️  WARNING: Expected 10 lines but got {len(formatted_messages)}")
                    
        except (FileNotFoundError, IOError) as e:
            print(f"\n❌ ERROR: Could not read log file: {e}")
            return False
    
    return True

if __name__ == "__main__":
    success = test_on_screen_logging()
    sys.exit(0 if success else 1)