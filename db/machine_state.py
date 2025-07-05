#!/usr/bin/env python3
"""
Machine State Database Module

This module handles SQLite database operations for tracking
instance state and deployment information.
"""

import asyncio
import logging
import sqlite3
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import aiosqlite

logger = logging.getLogger(__name__)


class MachineStateManager:
    """Manage machine state in SQLite database."""
    
    def __init__(self, db_path: str = "machines.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize the database schema."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create machines table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS machines (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        instance_id TEXT UNIQUE NOT NULL,
                        region TEXT NOT NULL,
                        instance_type TEXT,
                        public_ip TEXT,
                        private_ip TEXT,
                        status TEXT DEFAULT 'pending',
                        launch_time TEXT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        spot_request_id TEXT,
                        vpc_id TEXT,
                        subnet_id TEXT,
                        security_group_id TEXT,
                        ami_id TEXT,
                        error_message TEXT
                    )
                """)
                
                # Create deployment_runs table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS deployment_runs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        run_id TEXT UNIQUE NOT NULL,
                        started_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        ended_at TEXT,
                        status TEXT DEFAULT 'running',
                        total_instances INTEGER DEFAULT 0,
                        successful_instances INTEGER DEFAULT 0,
                        failed_instances INTEGER DEFAULT 0,
                        config_snapshot TEXT
                    )
                """)
                
                # Create indexes for better performance
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_machines_region ON machines(region)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_machines_status ON machines(status)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_machines_instance_id ON machines(instance_id)")
                
                conn.commit()
                logger.debug("Database initialized successfully")
                
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise
    
    @asynccontextmanager
    async def get_connection(self):
        """Get async database connection."""
        conn = await aiosqlite.connect(self.db_path)
        try:
            yield conn
        finally:
            await conn.close()
    
    async def add_machine(
        self,
        instance_id: str,
        region: str,
        instance_type: str = "",
        public_ip: str = "",
        private_ip: str = "",
        status: str = "pending",
        launch_time: Optional[str] = None,
        spot_request_id: str = "",
        vpc_id: str = "",
        subnet_id: str = "",
        security_group_id: str = "",
        ami_id: str = ""
    ) -> bool:
        """Add a new machine to the database."""
        try:
            async with self.get_connection() as conn:
                await conn.execute("""
                    INSERT OR REPLACE INTO machines (
                        instance_id, region, instance_type, public_ip, private_ip,
                        status, launch_time, spot_request_id, vpc_id, subnet_id,
                        security_group_id, ami_id, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    instance_id, region, instance_type, public_ip, private_ip,
                    status, launch_time or datetime.now().isoformat(),
                    spot_request_id, vpc_id, subnet_id, security_group_id, ami_id,
                    datetime.now().isoformat()
                ))
                await conn.commit()
                logger.debug(f"Added machine {instance_id} to database")
                return True
        except Exception as e:
            logger.error(f"Error adding machine {instance_id}: {e}")
            return False
    
    async def update_machine(
        self,
        instance_id: str,
        **kwargs
    ) -> bool:
        """Update machine information."""
        if not kwargs:
            return True
        
        # Add updated_at timestamp
        kwargs["updated_at"] = datetime.now().isoformat()
        
        # Build dynamic update query
        set_clause = ", ".join([f"{key} = ?" for key in kwargs.keys()])
        values = list(kwargs.values())
        values.append(instance_id)
        
        try:
            async with self.get_connection() as conn:
                await conn.execute(
                    f"UPDATE machines SET {set_clause} WHERE instance_id = ?",
                    values
                )
                await conn.commit()
                logger.debug(f"Updated machine {instance_id}")
                return True
        except Exception as e:
            logger.error(f"Error updating machine {instance_id}: {e}")
            return False
    
    async def get_machine(self, instance_id: str) -> Optional[Dict]:
        """Get machine information by instance ID."""
        try:
            async with self.get_connection() as conn:
                async with conn.execute(
                    "SELECT * FROM machines WHERE instance_id = ?",
                    (instance_id,)
                ) as cursor:
                    row = await cursor.fetchone()
                    if row:
                        columns = [description[0] for description in cursor.description]
                        return dict(zip(columns, row))
                    return None
        except Exception as e:
            logger.error(f"Error getting machine {instance_id}: {e}")
            return None
    
    async def get_machines_by_region(self, region: str) -> List[Dict]:
        """Get all machines in a specific region."""
        try:
            async with self.get_connection() as conn:
                async with conn.execute(
                    "SELECT * FROM machines WHERE region = ? ORDER BY created_at",
                    (region,)
                ) as cursor:
                    rows = await cursor.fetchall()
                    columns = [description[0] for description in cursor.description]
                    return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            logger.error(f"Error getting machines for region {region}: {e}")
            return []
    
    async def get_all_machines(self) -> List[Dict]:
        """Get all machines."""
        try:
            async with self.get_connection() as conn:
                async with conn.execute(
                    "SELECT * FROM machines ORDER BY region, created_at"
                ) as cursor:
                    rows = await cursor.fetchall()
                    columns = [description[0] for description in cursor.description]
                    return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            logger.error(f"Error getting all machines: {e}")
            return []
    
    async def get_machines_by_status(self, status: str) -> List[Dict]:
        """Get machines by status."""
        try:
            async with self.get_connection() as conn:
                async with conn.execute(
                    "SELECT * FROM machines WHERE status = ? ORDER BY region, created_at",
                    (status,)
                ) as cursor:
                    rows = await cursor.fetchall()
                    columns = [description[0] for description in cursor.description]
                    return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            logger.error(f"Error getting machines with status {status}: {e}")
            return []
    
    async def delete_machine(self, instance_id: str) -> bool:
        """Delete machine from database."""
        try:
            async with self.get_connection() as conn:
                await conn.execute(
                    "DELETE FROM machines WHERE instance_id = ?",
                    (instance_id,)
                )
                await conn.commit()
                logger.debug(f"Deleted machine {instance_id}")
                return True
        except Exception as e:
            logger.error(f"Error deleting machine {instance_id}: {e}")
            return False
    
    async def delete_machines_by_region(self, region: str) -> int:
        """Delete all machines in a region."""
        try:
            async with self.get_connection() as conn:
                cursor = await conn.execute(
                    "DELETE FROM machines WHERE region = ?",
                    (region,)
                )
                await conn.commit()
                deleted_count = cursor.rowcount
                logger.debug(f"Deleted {deleted_count} machines from region {region}")
                return deleted_count
        except Exception as e:
            logger.error(f"Error deleting machines from region {region}: {e}")
            return 0
    
    async def get_machine_count(self) -> Dict[str, int]:
        """Get machine count statistics."""
        try:
            async with self.get_connection() as conn:
                # Total count
                async with conn.execute("SELECT COUNT(*) FROM machines") as cursor:
                    total = (await cursor.fetchone())[0]
                
                # Count by status
                async with conn.execute(
                    "SELECT status, COUNT(*) FROM machines GROUP BY status"
                ) as cursor:
                    status_counts = dict(await cursor.fetchall())
                
                # Count by region
                async with conn.execute(
                    "SELECT region, COUNT(*) FROM machines GROUP BY region"
                ) as cursor:
                    region_counts = dict(await cursor.fetchall())
                
                return {
                    "total": total,
                    "by_status": status_counts,
                    "by_region": region_counts
                }
        except Exception as e:
            logger.error(f"Error getting machine counts: {e}")
            return {"total": 0, "by_status": {}, "by_region": {}}
    
    async def start_deployment_run(self, run_id: str, config_snapshot: str = "") -> bool:
        """Start a new deployment run."""
        try:
            async with self.get_connection() as conn:
                await conn.execute("""
                    INSERT INTO deployment_runs (run_id, config_snapshot)
                    VALUES (?, ?)
                """, (run_id, config_snapshot))
                await conn.commit()
                logger.debug(f"Started deployment run {run_id}")
                return True
        except Exception as e:
            logger.error(f"Error starting deployment run {run_id}: {e}")
            return False
    
    async def end_deployment_run(
        self,
        run_id: str,
        status: str = "completed",
        total_instances: int = 0,
        successful_instances: int = 0,
        failed_instances: int = 0
    ) -> bool:
        """End a deployment run."""
        try:
            async with self.get_connection() as conn:
                await conn.execute("""
                    UPDATE deployment_runs 
                    SET ended_at = ?, status = ?, total_instances = ?,
                        successful_instances = ?, failed_instances = ?
                    WHERE run_id = ?
                """, (
                    datetime.now().isoformat(), status, total_instances,
                    successful_instances, failed_instances, run_id
                ))
                await conn.commit()
                logger.debug(f"Ended deployment run {run_id}")
                return True
        except Exception as e:
            logger.error(f"Error ending deployment run {run_id}: {e}")
            return False
    
    async def get_deployment_runs(self, limit: int = 10) -> List[Dict]:
        """Get recent deployment runs."""
        try:
            async with self.get_connection() as conn:
                async with conn.execute(
                    "SELECT * FROM deployment_runs ORDER BY started_at DESC LIMIT ?",
                    (limit,)
                ) as cursor:
                    rows = await cursor.fetchall()
                    columns = [description[0] for description in cursor.description]
                    return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            logger.error(f"Error getting deployment runs: {e}")
            return []
    
    def print_database_contents(self):
        """Print database contents for debugging (synchronous)."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                print("\n=== MACHINES TABLE ===")
                cursor.execute("SELECT * FROM machines ORDER BY region, created_at")
                rows = cursor.fetchall()
                
                if rows:
                    # Print header
                    cursor.execute("PRAGMA table_info(machines)")
                    columns = [column[1] for column in cursor.fetchall()]
                    print(" | ".join(f"{col:<15}" for col in columns))
                    print("-" * (17 * len(columns)))
                    
                    # Print rows
                    for row in rows:
                        print(" | ".join(f"{str(val):<15}" for val in row))
                else:
                    print("No machines found")
                
                print(f"\nTotal machines: {len(rows)}")
                
                print("\n=== DEPLOYMENT RUNS TABLE ===")
                cursor.execute("SELECT * FROM deployment_runs ORDER BY started_at DESC")
                runs = cursor.fetchall()
                
                if runs:
                    cursor.execute("PRAGMA table_info(deployment_runs)")
                    columns = [column[1] for column in cursor.fetchall()]
                    print(" | ".join(f"{col:<20}" for col in columns))
                    print("-" * (22 * len(columns)))
                    
                    for run in runs:
                        print(" | ".join(f"{str(val):<20}" for val in run))
                else:
                    print("No deployment runs found")
                
                print(f"\nTotal deployment runs: {len(runs)}")
                
        except Exception as e:
            logger.error(f"Error printing database contents: {e}")
            print(f"Error accessing database: {e}")


# Global machine state manager instance
machine_state_manager = MachineStateManager()


# Convenience functions for backward compatibility
async def add_machine_to_db(instance_id: str, region: str, **kwargs):
    """Add machine to database (backward compatibility)."""
    return await machine_state_manager.add_machine(instance_id, region, **kwargs)


async def update_machine_in_db(instance_id: str, **kwargs):
    """Update machine in database (backward compatibility)."""
    return await machine_state_manager.update_machine(instance_id, **kwargs)


async def get_machine_from_db(instance_id: str):
    """Get machine from database (backward compatibility)."""
    return await machine_state_manager.get_machine(instance_id)


async def get_all_machines_from_db():
    """Get all machines from database (backward compatibility)."""
    return await machine_state_manager.get_all_machines()


def print_database():
    """Print database contents (backward compatibility)."""
    machine_state_manager.print_database_contents()