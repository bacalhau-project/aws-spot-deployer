#!/usr/bin/env python3
"""
Status Management Module

This module handles instance status tracking, progress reporting,
and operation logging for the spot instance deployment tool.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class InstanceStatus:
    """Track the status of a single instance."""

    def __init__(self, region: str, instance_id: str = ""):
        self.region = region
        self.instance_id = instance_id
        self.status = "initializing"
        self.public_ip = ""
        self.private_ip = ""
        self.instance_type = ""
        self.start_time = datetime.now()
        self.last_update = datetime.now()
        self.error_message = ""
        self.done = False

    def update(
        self,
        status: Optional[str] = None,
        public_ip: Optional[str] = None,
        private_ip: Optional[str] = None,
        instance_type: Optional[str] = None,
        error_message: Optional[str] = None,
        mark_done: bool = False,
    ):
        """Update instance status."""
        if status:
            self.status = status
        if public_ip:
            self.public_ip = public_ip
        if private_ip:
            self.private_ip = private_ip
        if instance_type:
            self.instance_type = instance_type
        if error_message:
            self.error_message = error_message
        if mark_done:
            self.done = True

        self.last_update = datetime.now()

    def elapsed_time(self) -> int:
        """Get elapsed time in seconds."""
        return int((datetime.now() - self.start_time).total_seconds())

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "region": self.region,
            "instance_id": self.instance_id,
            "status": self.status,
            "public_ip": self.public_ip,
            "private_ip": self.private_ip,
            "instance_type": self.instance_type,
            "start_time": self.start_time.isoformat(),
            "last_update": self.last_update.isoformat(),
            "error_message": self.error_message,
            "done": self.done,
            "elapsed_seconds": self.elapsed_time(),
        }


class StatusManager:
    """Manage status for all instances and operations."""

    def __init__(self):
        self.statuses: Dict[str, InstanceStatus] = {}
        self.global_node_count = 0
        self.operations_logs: List[str] = []
        self.operations_logs_lock = asyncio.Lock()
        self.max_operations_logs = 20

    def add_instance(self, region: str, instance_id: str = "") -> InstanceStatus:
        """Add a new instance to track."""
        key = f"{region}:{instance_id}" if instance_id else region
        status = InstanceStatus(region, instance_id)
        self.statuses[key] = status
        return status

    def get_instance(
        self, region: str, instance_id: str = ""
    ) -> Optional[InstanceStatus]:
        """Get instance status."""
        key = f"{region}:{instance_id}" if instance_id else region
        return self.statuses.get(key)

    def update_instance(
        self,
        region: str,
        instance_id: str = "",
        status: Optional[str] = None,
        public_ip: Optional[str] = None,
        private_ip: Optional[str] = None,
        instance_type: Optional[str] = None,
        error_message: Optional[str] = None,
        mark_done: bool = False,
    ):
        """Update instance status."""
        key = f"{region}:{instance_id}" if instance_id else region

        if key not in self.statuses:
            self.add_instance(region, instance_id)

        self.statuses[key].update(
            status=status,
            public_ip=public_ip,
            private_ip=private_ip,
            instance_type=instance_type,
            error_message=error_message,
            mark_done=mark_done,
        )

    def get_all_statuses(self) -> Dict[str, Dict]:
        """Get all instance statuses as dictionaries."""
        return {key: status.to_dict() for key, status in self.statuses.items()}

    def get_summary(self) -> Dict:
        """Get summary statistics."""
        total = len(self.statuses)
        done = sum(1 for status in self.statuses.values() if status.done)
        running = sum(
            1 for status in self.statuses.values() if status.status == "running"
        )
        failed = sum(1 for status in self.statuses.values() if status.error_message)

        return {
            "total": total,
            "done": done,
            "running": running,
            "failed": failed,
            "pending": total - done - running - failed,
        }

    def log_operation(
        self, message: str, level: str = "info", region: Optional[str] = None
    ):
        """Add an operation log message (synchronous version)."""
        timestamp = datetime.now().strftime("%H:%M:%S")

        # Format the message with color based on level
        if level == "error":
            formatted_message = f"[red]{timestamp} ERROR:[/red] "
        elif level == "warning":
            formatted_message = f"[yellow]{timestamp} WARN:[/yellow] "
        else:
            formatted_message = f"[green]{timestamp} INFO:[/green] "

        # Add region if provided
        if region:
            formatted_message += f"[cyan]{region}:[/cyan] "

        formatted_message += message

        # Add to logs (not thread-safe, but better than nothing)
        self.operations_logs.append(formatted_message)

        # Keep only the most recent logs
        if len(self.operations_logs) > self.max_operations_logs:
            self.operations_logs = self.operations_logs[-self.max_operations_logs :]

        # Also log to standard logger
        if level == "error":
            logger.error(message)
        elif level == "warning":
            logger.warning(message)
        else:
            logger.info(message)

    async def log_operation_async(
        self, message: str, level: str = "info", region: Optional[str] = None
    ):
        """Add an operation log message (async version with proper locking)."""
        timestamp = datetime.now().strftime("%H:%M:%S")

        # Format the message with color based on level
        if level == "error":
            formatted_message = f"[red]{timestamp} ERROR:[/red] "
        elif level == "warning":
            formatted_message = f"[yellow]{timestamp} WARN:[/yellow] "
        else:
            formatted_message = f"[green]{timestamp} INFO:[/green] "

        # Add region if provided
        if region:
            formatted_message += f"[cyan]{region}:[/cyan] "

        formatted_message += message

        # Thread-safe update to operations logs
        async with self.operations_logs_lock:
            self.operations_logs.append(formatted_message)

            # Keep only the most recent logs
            if len(self.operations_logs) > self.max_operations_logs:
                self.operations_logs = self.operations_logs[-self.max_operations_logs :]

        # Also log to standard logger
        if level == "error":
            logger.error(message)
        elif level == "warning":
            logger.warning(message)
        else:
            logger.info(message)

    def get_operations_logs(self) -> List[str]:
        """Get recent operations logs."""
        return self.operations_logs.copy()

    def clear_logs(self):
        """Clear all logs."""
        self.operations_logs.clear()

    def reset(self):
        """Reset all status tracking."""
        self.statuses.clear()
        self.global_node_count = 0
        self.clear_logs()


def format_elapsed_time(seconds: int) -> str:
    """Format elapsed time in human-readable format."""
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes}m {seconds}s"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60
        return f"{hours}h {minutes}m {seconds}s"


# Global status manager instance
status_manager = StatusManager()


# Convenience functions for backward compatibility
def log_operation(message: str, level: str = "info", region: Optional[str] = None):
    """Log operation using global status manager."""
    status_manager.log_operation(message, level, region)


async def log_operation_async(
    message: str, level: str = "info", region: Optional[str] = None
):
    """Log operation async using global status manager."""
    await status_manager.log_operation_async(message, level, region)


def update_all_statuses(status_dict: Dict):
    """Update all statuses (for backward compatibility)."""
    for key, status_data in status_dict.items():
        if ":" in key:
            region, instance_id = key.split(":", 1)
        else:
            region, instance_id = key, ""

        status_manager.update_instance(
            region=region,
            instance_id=instance_id,
            status=status_data.get("status"),
            public_ip=status_data.get("public_ip"),
            private_ip=status_data.get("private_ip"),
            instance_type=status_data.get("instance_type"),
            error_message=status_data.get("error_message"),
            mark_done=status_data.get("done", False),
        )


async def update_all_statuses_async(status_dict: Dict):
    """Update all statuses async (for backward compatibility)."""
    update_all_statuses(status_dict)  # Status updates are already thread-safe
