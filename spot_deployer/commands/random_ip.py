"""Random IP command - returns a random instance IP for SSH access."""

import random
import sys

from ..core.state import SimpleStateManager


def cmd_random_ip(state: SimpleStateManager) -> None:
    """Output a random IP address from running instances."""

    # Load instances from local state
    instances = state.load_instances()

    if not instances:
        print("", file=sys.stderr)  # Empty output
        sys.exit(1)

    # Filter instances with valid IPs
    instances_with_ip = [
        i for i in instances if i.get("public_ip") and i.get("public_ip") != "pending"
    ]

    if not instances_with_ip:
        print("", file=sys.stderr)  # Empty output
        sys.exit(1)

    # Select and output a random IP
    selected = random.choice(instances_with_ip)
    print(selected["public_ip"])  # Just output the IP, nothing else
