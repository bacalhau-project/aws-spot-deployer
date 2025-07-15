#!/usr/bin/env python3
"""Test script to verify logging with instance ID and IP works correctly."""

import logging
import sys
import os

# Add the parent directory to the path so we can import from deploy_spot
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from deploy_spot import ConsoleLogger

# Set up basic logging
logger = logging.getLogger("test_logger")
logger.setLevel(logging.INFO)

# Create console handler
console_handler = ConsoleLogger(None, {})
console_handler.setFormatter(logging.Formatter("%(message)s"))
logger.addHandler(console_handler)

# Store reference
logger.console_handler = console_handler

# Test various message formats
print("Testing logging output:")
print("-" * 50)

# Test 1: Simple message (should add region context)
logger.info("Simple test message")

# Test 2: Message with SUCCESS (should be printed)
logger.info("SUCCESS: Created instance")

# Test 3: Message with instance ID and IP (should be printed as-is)
logger.info("[i-0123456789abcdef0 @ 54.123.45.67] SUCCESS: Created")

# Test 4: Update IP map and test
logger.console_handler.instance_ip_map["i-0987654321fedcba0"] = "10.0.0.1"
logger.info("[us-west-2-1] SUCCESS: Created")

# Test 5: ERROR message
logger.info("[i-0123456789abcdef0 @ 54.123.45.67] ERROR: Failed to start")

print("-" * 50)
print("Test complete")