#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "boto3",
#     "botocore",
#     "rich",
#     "aiosqlite",
#     "aiofiles",
#     "pyyaml",
# ]
# ///

# Check for verbose flag early (need sys first)
import sys
import time
_verbose = "-v" in sys.argv or "--verbose" in sys.argv
_start_time = time.time()

# Add debugging prints BEFORE any imports (only if verbose)
if _verbose:
    print("🚀 Python code starting...")

"""
AWS Spot Instance Deployment Tool for Bacalhau Clusters

This is a complete, self-contained deployment tool for AWS spot instances.
It includes all functionality needed to deploy and manage Bacalhau clusters.

Usage:
    ./deploy_spot.py setup         # Setup environment
    ./deploy_spot.py verify        # Verify configuration
    ./deploy_spot.py validate      # Run validation tests
    ./deploy_spot.py create        # Deploy spot instances
    ./deploy_spot.py list          # List running instances
    ./deploy_spot.py status        # Check status
    ./deploy_spot.py destroy       # Terminate instances
    ./deploy_spot.py cleanup       # Full cleanup

Optional arguments:
    --config PATH    Use custom configuration file (default: config.yaml)
    --help          Show this help message
"""

if _verbose:
    print("⚡ Loading basic imports...")
import argparse
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
if _verbose:
    print(f"✅ Basic imports loaded in {time.time() - _start_time:.3f}s")

# Lazy imports - only import heavy dependencies when needed
_imports_loaded = False

def _ensure_imports():
    """Lazy load heavy dependencies only when needed."""
    global _imports_loaded
    if _imports_loaded:
        return
    
    if _verbose:
        print("🔄 Loading heavy dependencies...")
    _import_start = time.time()
    
    global asyncio, base64, csv, gzip, io, json, logging, shutil, sqlite3, tarfile, uuid
    global ThreadPoolExecutor, as_completed, asynccontextmanager, datetime, timezone
    global aiosqlite, boto3, botocore, yaml, Console, Table, Panel, Progress, TextColumn, BarColumn
    
    if _verbose:
        print("  📦 Loading standard library modules...")
    import asyncio
    import base64
    import csv
    import gzip
    import io
    import json
    import logging
    import shutil
    import sqlite3
    import tarfile
    import uuid
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from contextlib import asynccontextmanager
    from datetime import datetime, timezone
    
    if _verbose:
        print(f"  ✅ Standard library loaded in {time.time() - _import_start:.3f}s")
    
    _heavy_start = time.time()
    if _verbose:
        print("  📦 Loading heavy dependencies (boto3, rich, etc.)...")
    import aiosqlite
    import boto3
    import botocore
    import yaml
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.progress import Progress, TextColumn, BarColumn
    
    if _verbose:
        print(f"  ✅ Heavy dependencies loaded in {time.time() - _heavy_start:.3f}s")
    
    _imports_loaded = True
    
    # Setup logging after imports are loaded
    _setup_logging()
    if _verbose:
        print(f"🎯 Total import time: {time.time() - _import_start:.3f}s")

# =============================================================================
# CONSTANTS AND CONFIGURATION
# =============================================================================

# Tag to filter instances by
FILTER_TAG_NAME = "ManagedBy"
FILTER_TAG_VALUE = "SpotInstanceScript"

# Lightweight console for basic output (will be replaced with rich Console when needed)
console = None

def _get_console():
    """Get console instance, creating rich Console if needed."""
    global console
    if console is None:
        _ensure_imports()
        console = Console()
    return console

# Instance requirements and families
MIN_VCPU = 2
MIN_MEMORY_GIB = 4
PREFERRED_INSTANCE_FAMILIES = ["t3", "t2", "t3a", "t4g", "m5", "m5a", "m6g", "m6i", "a1"]

# Instance type vCPU corrections
INSTANCE_TYPE_VCPU_CORRECTION = {
    "t2.nano": 1, "t2.micro": 1, "t2.small": 1, "t2.medium": 2, "t2.large": 2,
    "t2.xlarge": 4, "t2.2xlarge": 8, "t3.nano": 1, "t3.micro": 1, "t3.small": 1,
    "t3.medium": 2, "t3.large": 2, "t3.xlarge": 4, "t3.2xlarge": 8,
    "t3a.nano": 1, "t3a.micro": 1, "t3a.small": 1, "t3a.medium": 2, "t3a.large": 2,
    "t3a.xlarge": 4, "t3a.2xlarge": 8, "t4g.nano": 1, "t4g.micro": 1, "t4g.small": 1,
    "t4g.medium": 2, "t4g.large": 2, "t4g.xlarge": 4, "t4g.2xlarge": 8,
}

# AWS Data Cache Configuration
CACHE_DIR = ".aws_cache"
CACHE_CONFIG = {
    "regions": {"ttl_hours": 720, "file": ".aws_regions.json"},           # 30 days
    "instance_types": {"ttl_hours": 168, "file": ".aws_instance_types.json"},  # 7 days
    "spot_pricing": {"ttl_hours": 24, "file": ".aws_spot_pricing.json"}, # 1 day
    "amis": {"ttl_hours": 168, "file": ".aws_amis.json"},               # 7 days
}

# =============================================================================
# LOGGING SETUP (LAZY)
# =============================================================================

# Logger will be initialized when needed
logger = None

def _setup_logging():
    """Setup logging when heavy imports are loaded."""
    global logger
    if logger is not None:
        return
    
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    
    # Disable noisy boto3/botocore logging
    logging.getLogger("boto3").setLevel(logging.WARNING)
    logging.getLogger("botocore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    
    # Clear existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Setup file logging
    try:
        open("debug_deploy_spot.log", "w").close()
        file_handler = logging.FileHandler("debug_deploy_spot.log")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s")
        )
        logger.addHandler(file_handler)
        logger.debug("Logging initialized")
    except Exception as e:
        with open("debug_deploy_spot.log", "a") as f:
            f.write(f"Failed to set up file logging: {e}\n")

# =============================================================================
# CONFIGURATION CLASS
# =============================================================================

class Config(dict):
    """Configuration management class that extends dict."""
    
    def __init__(self, file_path: str):
        super().__init__()
        self.file_path = file_path
        self._load_yaml()
        logger.debug("Config initialization completed")

    def _load_yaml(self):
        """Load configuration from YAML file."""
        logger.debug(f"Loading YAML from {self.file_path}")
        try:
            with open(self.file_path, "r") as file:
                config_data = yaml.safe_load(file)
                logger.debug(f"Loaded config data: {config_data}")
                self.update(config_data)
        except Exception as e:
            logger.error(f"Error loading config file {self.file_path}: {str(e)}", exc_info=True)
            raise

    def get_regions(self) -> List[str]:
        """Get list of regions from configuration."""
        logger.debug("Getting regions from config")
        regions = [list(region.keys())[0] for region in self.get("regions", [])]
        logger.debug(f"Found regions: {regions}")
        return regions

    def get_total_instances(self) -> int:
        """Get total number of instances from configuration."""
        logger.debug("Getting total instances from config")
        total = self.get("max_instances", self.get("aws", {}).get("total_instances", 3))
        logger.debug(f"Total instances: {total}")
        return total

    def get_region_config(self, region_name: str) -> Optional[Dict]:
        """Get configuration for a specific region."""
        logger.debug(f"Getting config for region: {region_name}")
        for region in self.get("regions", []):
            if region_name in region:
                config = region[region_name]
                logger.debug(f"Found config for {region_name}: {config}")
                return config
        logger.warning(f"No config found for region: {region_name}")
        return None

    def get_orchestrators(self) -> List[str]:
        """Get Bacalhau orchestrators from configuration."""
        return self.get("orchestrators", self.get("bacalhau", {}).get("orchestrators", []))

    def get_token(self) -> str:
        """Get Bacalhau token from configuration."""
        return self.get("token", self.get("bacalhau", {}).get("token", ""))

    def get_tls(self) -> bool:
        """Get TLS setting from configuration."""
        return self.get("tls", self.get("bacalhau", {}).get("tls", False))

    def get_public_ssh_key_path(self) -> str:
        """Get public SSH key path from configuration."""
        path = self.get("public_ssh_key_path", self.get("aws", {}).get("public_ssh_key_path", ""))
        return os.path.expanduser(path) if path else ""

    def get_private_ssh_key_path(self) -> str:
        """Get private SSH key path from configuration."""
        path = self.get("private_ssh_key_path", self.get("aws", {}).get("private_ssh_key_path", ""))
        return os.path.expanduser(path) if path else ""

    def get_username(self) -> str:
        """Get username from configuration."""
        return self.get("username", self.get("aws", {}).get("username", "bacalhau-runner"))

# =============================================================================
# AWS DATA CACHE MANAGEMENT
# =============================================================================

class AWSDataCache:
    """Manage local caching of AWS data to reduce API calls and enable offline operation."""
    
    def __init__(self, cache_dir: str = CACHE_DIR):
        self.cache_dir = Path(cache_dir)
        self.metadata_file = self.cache_dir / ".aws_cache_metadata.json"
        self._ensure_cache_dir()
    
    def _ensure_cache_dir(self):
        """Ensure cache directory exists."""
        self.cache_dir.mkdir(exist_ok=True)
        
        # Create .gitignore in cache directory
        gitignore_path = self.cache_dir / ".gitignore"
        if not gitignore_path.exists():
            with open(gitignore_path, "w") as f:
                f.write("# AWS cache files - not version controlled\n*\n")
    
    def _get_cache_file_path(self, cache_type: str) -> Path:
        """Get the file path for a specific cache type."""
        config = CACHE_CONFIG.get(cache_type)
        if not config:
            raise ValueError(f"Unknown cache type: {cache_type}")
        return self.cache_dir / config["file"]
    
    def _is_cache_fresh(self, cache_type: str) -> bool:
        """Check if cache file exists and is within TTL."""
        try:
            cache_file = self._get_cache_file_path(cache_type)
            if not cache_file.exists():
                return False
            
            # Check metadata for timestamp
            metadata = self._load_metadata()
            if cache_type not in metadata.get("cache_timestamps", {}):
                return False
            
            cached_time = datetime.fromisoformat(metadata["cache_timestamps"][cache_type])
            max_age_hours = CACHE_CONFIG[cache_type]["ttl_hours"]
            age_hours = (datetime.now() - cached_time).total_seconds() / 3600
            
            return age_hours < max_age_hours
        except Exception as e:
            logger.debug(f"Cache freshness check failed for {cache_type}: {e}")
            return False
    
    def _load_metadata(self) -> Dict[str, Any]:
        """Load cache metadata."""
        try:
            if self.metadata_file.exists():
                with open(self.metadata_file, "r") as f:
                    return json.load(f)
        except Exception as e:
            logger.debug(f"Error loading cache metadata: {e}")
        return {"cache_timestamps": {}, "cache_stats": {}}
    
    def _save_metadata(self, metadata: Dict[str, Any]):
        """Save cache metadata."""
        try:
            with open(self.metadata_file, "w") as f:
                json.dump(metadata, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving cache metadata: {e}")
    
    def _save_cache_data(self, cache_type: str, data: Dict[str, Any]):
        """Save data to cache file with compression."""
        try:
            cache_file = self._get_cache_file_path(cache_type)
            
            # Write to temporary file first (atomic operation)
            temp_file = cache_file.with_suffix(cache_file.suffix + ".tmp")
            
            # Compress large files
            if len(json.dumps(data)) > 100000:  # 100KB threshold
                with gzip.open(temp_file.with_suffix(".gz"), "wt", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, default=str)
                temp_file = temp_file.with_suffix(".gz")
                cache_file = cache_file.with_suffix(".json.gz")
            else:
                with open(temp_file, "w") as f:
                    json.dump(data, f, indent=2, default=str)
            
            # Atomic rename
            temp_file.rename(cache_file)
            
            # Update metadata
            metadata = self._load_metadata()
            metadata["cache_timestamps"][cache_type] = datetime.now().isoformat()
            metadata["cache_stats"][cache_type] = {
                "size_bytes": cache_file.stat().st_size,
                "record_count": len(data) if isinstance(data, dict) else 1,
                "last_updated": datetime.now().isoformat()
            }
            self._save_metadata(metadata)
            
            logger.debug(f"Cached {cache_type} data to {cache_file}")
            
        except Exception as e:
            logger.error(f"Error saving cache data for {cache_type}: {e}")
    
    def _load_cache_data(self, cache_type: str) -> Optional[Dict[str, Any]]:
        """Load data from cache file."""
        try:
            cache_file = self._get_cache_file_path(cache_type)
            
            # Try compressed version first
            compressed_file = cache_file.with_suffix(".json.gz")
            if compressed_file.exists():
                with gzip.open(compressed_file, "rt", encoding="utf-8") as f:
                    return json.load(f)
            
            # Try uncompressed version
            if cache_file.exists():
                with open(cache_file, "r") as f:
                    return json.load(f)
            
            return None
            
        except Exception as e:
            logger.error(f"Error loading cache data for {cache_type}: {e}")
            return None
    
    def get_cached_regions(self) -> Optional[List[str]]:
        """Get cached AWS regions list."""
        if self._is_cache_fresh("regions"):
            data = self._load_cache_data("regions")
            return data.get("regions", []) if data else None
        return None
    
    def cache_regions(self, regions: List[str]):
        """Cache AWS regions list."""
        data = {
            "regions": regions,
            "timestamp": datetime.now().isoformat(),
            "source": "describe_regions"
        }
        self._save_cache_data("regions", data)
    
    def get_cached_instance_types(self, region: str = None) -> Optional[Dict[str, Any]]:
        """Get cached instance types data."""
        if self._is_cache_fresh("instance_types"):
            data = self._load_cache_data("instance_types")
            if data and region:
                return data.get("regions", {}).get(region)
            return data
        return None
    
    def cache_instance_types(self, region_data: Dict[str, Any]):
        """Cache instance types data."""
        existing_data = self._load_cache_data("instance_types") or {"regions": {}}
        existing_data["regions"].update(region_data)
        existing_data["timestamp"] = datetime.now().isoformat()
        existing_data["source"] = "describe_instance_types"
        self._save_cache_data("instance_types", existing_data)
    
    def get_cached_spot_pricing(self, region: str = None) -> Optional[Dict[str, Any]]:
        """Get cached spot pricing data."""
        if self._is_cache_fresh("spot_pricing"):
            data = self._load_cache_data("spot_pricing")
            if data and region:
                return data.get("regions", {}).get(region)
            return data
        return None
    
    def cache_spot_pricing(self, region_data: Dict[str, Any]):
        """Cache spot pricing data."""
        existing_data = self._load_cache_data("spot_pricing") or {"regions": {}}
        existing_data["regions"].update(region_data)
        existing_data["timestamp"] = datetime.now().isoformat()
        existing_data["source"] = "describe_spot_price_history"
        self._save_cache_data("spot_pricing", existing_data)
    
    def get_cached_amis(self, region: str = None) -> Optional[Dict[str, Any]]:
        """Get cached AMI data."""
        if self._is_cache_fresh("amis"):
            data = self._load_cache_data("amis")
            if data and region:
                return data.get("regions", {}).get(region)
            return data
        return None
    
    def cache_amis(self, region_data: Dict[str, Any]):
        """Cache AMI data."""
        existing_data = self._load_cache_data("amis") or {"regions": {}}
        existing_data["regions"].update(region_data)
        existing_data["timestamp"] = datetime.now().isoformat()
        existing_data["source"] = "describe_images"
        self._save_cache_data("amis", existing_data)
    
    def ensure_cache_fresh(self, force_refresh: bool = False) -> bool:
        """Ensure cache is fresh, refresh if needed."""
        try:
            needs_refresh = force_refresh
            
            for cache_type in CACHE_CONFIG.keys():
                if not self._is_cache_fresh(cache_type):
                    needs_refresh = True
                    break
            
            if needs_refresh:
                _get_console().print("[yellow]Refreshing AWS data cache...[/yellow]")
                self.refresh_cache()
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking cache freshness: {e}")
            return False
    
    def refresh_cache(self):
        """Refresh all cache data by calling AWS APIs."""
        try:
            _get_console().print("1. Caching AWS regions...")
            regions = get_all_aws_regions()
            self.cache_regions(regions)
            
            _get_console().print("2. Caching instance types and spot pricing...")
            
            # Use ThreadPoolExecutor for parallel API calls
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = []
                
                # Sample a subset of regions for comprehensive data
                sample_regions = regions[:15] if len(regions) > 15 else regions
                
                for region in sample_regions:
                    futures.append(executor.submit(self._fetch_region_data, region))
                
                for future in as_completed(futures):
                    try:
                        future.result()
                    except Exception as e:
                        logger.error(f"Error fetching region data: {e}")
            
            _get_console().print(f"[green]✓[/green] Cache refreshed with data from {len(sample_regions)} regions")
            
        except Exception as e:
            logger.error(f"Error refreshing cache: {e}")
            _get_console().print(f"[red]Error refreshing cache: {e}[/red]")
    
    def _fetch_region_data(self, region: str):
        """Fetch comprehensive data for a single region."""
        try:
            ec2_client = boto3.client("ec2", region_name=region)
            
            # Fetch instance types
            instance_types_response = ec2_client.describe_instance_types()
            instance_types_data = {
                region: {
                    "instance_types": instance_types_response["InstanceTypes"],
                    "timestamp": datetime.now().isoformat()
                }
            }
            self.cache_instance_types(instance_types_data)
            
            # Fetch spot pricing for common instance types
            common_types = ["t3.micro", "t3.small", "t3.medium", "t3.large", "t3.xlarge"]
            spot_pricing_data = {region: {"pricing": {}, "timestamp": datetime.now().isoformat()}}
            
            for instance_type in common_types:
                try:
                    spot_response = ec2_client.describe_spot_price_history(
                        InstanceTypes=[instance_type],
                        ProductDescriptions=["Linux/UNIX"],
                        MaxResults=1,
                    )
                    if spot_response.get("SpotPriceHistory"):
                        price = float(spot_response["SpotPriceHistory"][0]["SpotPrice"])
                        spot_pricing_data[region]["pricing"][instance_type] = {
                            "price": price,
                            "timestamp": spot_response["SpotPriceHistory"][0]["Timestamp"].isoformat()
                        }
                except Exception:
                    continue
            
            self.cache_spot_pricing(spot_pricing_data)
            
            # Fetch AMIs
            ami_data = {region: {"amis": {}, "timestamp": datetime.now().isoformat()}}
            
            for arch in ["x86_64", "arm64"]:
                ami_info = get_latest_ubuntu_ami(region, arch)
                if ami_info:
                    ami_data[region]["amis"][arch] = ami_info
            
            self.cache_amis(ami_data)
            
            logger.debug(f"Successfully fetched data for region {region}")
            
        except Exception as e:
            logger.error(f"Error fetching data for region {region}: {e}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        metadata = self._load_metadata()
        stats = metadata.get("cache_stats", {})
        
        for cache_type in CACHE_CONFIG.keys():
            fresh = self._is_cache_fresh(cache_type)
            if cache_type in stats:
                stats[cache_type]["is_fresh"] = fresh
            else:
                stats[cache_type] = {"is_fresh": fresh, "size_bytes": 0, "record_count": 0}
        
        return stats

# =============================================================================
# DATABASE MANAGEMENT
# =============================================================================

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
                        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.commit()
                logger.debug("Database initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise
    
    async def add_machine(self, instance_id: str, region: str, **kwargs) -> bool:
        """Add a machine to the database."""
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                await conn.execute("""
                    INSERT OR REPLACE INTO machines (
                        instance_id, region, instance_type, public_ip, private_ip,
                        status, launch_time, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    instance_id, region, 
                    kwargs.get('instance_type', ''),
                    kwargs.get('public_ip', ''),
                    kwargs.get('private_ip', ''),
                    kwargs.get('status', 'pending'),
                    kwargs.get('launch_time', datetime.now().isoformat()),
                    datetime.now().isoformat()
                ))
                await conn.commit()
                logger.debug(f"Added machine {instance_id} to database")
                return True
        except Exception as e:
            logger.error(f"Error adding machine {instance_id}: {e}")
            return False
    
    async def get_all_machines(self) -> List[Dict]:
        """Get all machines from database."""
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                async with conn.execute("SELECT * FROM machines ORDER BY region, created_at") as cursor:
                    rows = await cursor.fetchall()
                    columns = [description[0] for description in cursor.description]
                    return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            logger.error(f"Error getting all machines: {e}")
            return []
    
    async def delete_machines_by_region(self, region: str) -> int:
        """Delete all machines in a region."""
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                cursor = await conn.execute("DELETE FROM machines WHERE region = ?", (region,))
                await conn.commit()
                deleted_count = cursor.rowcount
                logger.debug(f"Deleted {deleted_count} machines from region {region}")
                return deleted_count
        except Exception as e:
            logger.error(f"Error deleting machines from region {region}: {e}")
            return 0

# =============================================================================
# AWS UTILITIES
# =============================================================================

def get_ec2_client(region: str):
    """Get EC2 client for specified region."""
    return boto3.client("ec2", region_name=region)

def get_all_aws_regions() -> List[str]:
    """Get a list of all AWS regions."""
    ec2 = boto3.client("ec2", region_name="us-east-1")
    regions = [region["RegionName"] for region in ec2.describe_regions()["Regions"]]
    return regions

def check_region_spot_availability(region: str) -> Dict[str, Any]:
    """Check if a region has spot instances available that meet requirements."""
    try:
        ec2_client = boto3.client("ec2", region_name=region)
        response = ec2_client.describe_instance_types()
        instance_types = response["InstanceTypes"]
        
        suitable_instances = []
        for instance in instance_types:
            instance_type = instance.get("InstanceType", "")
            reported_vcpus = instance.get("VCpuInfo", {}).get("DefaultVCpus", 0)
            vcpus = INSTANCE_TYPE_VCPU_CORRECTION.get(instance_type, reported_vcpus)
            memory_gib = instance.get("MemoryInfo", {}).get("SizeInMiB", 0) / 1024
            
            if vcpus >= MIN_VCPU and memory_gib >= MIN_MEMORY_GIB:
                size_score = vcpus * 10 + memory_gib
                is_preferred = any(instance_type.startswith(family) for family in PREFERRED_INSTANCE_FAMILIES)
                
                suitable_instances.append({
                    "instance_type": instance_type,
                    "vcpus": vcpus,
                    "memory_gib": memory_gib,
                    "size_score": size_score,
                    "is_preferred": is_preferred,
                })
        
        if not suitable_instances:
            return {"region": region, "available": False}
        
        suitable_instances.sort(key=lambda x: (0 if x["is_preferred"] else 1, x["size_score"]))
        
        available_instances = []
        for instance_info in suitable_instances[:10]:
            instance_type = instance_info["instance_type"]
            try:
                spot_response = ec2_client.describe_spot_price_history(
                    InstanceTypes=[instance_type],
                    ProductDescriptions=["Linux/UNIX"],
                    MaxResults=1,
                )
                
                if spot_response.get("SpotPriceHistory"):
                    spot_price = float(spot_response["SpotPriceHistory"][0]["SpotPrice"])
                    available_instances.append({
                        "instance_type": instance_type,
                        "vcpus": instance_info["vcpus"],
                        "memory_gib": round(instance_info["memory_gib"], 1),
                        "spot_price": spot_price,
                    })
            except Exception:
                continue
        
        if available_instances:
            available_instances.sort(key=lambda x: x["spot_price"])
            return {
                "region": region,
                "available": True,
                "instances": available_instances,
                "cheapest_instance": available_instances[0],
            }
        else:
            return {"region": region, "available": False}
    
    except Exception as e:
        return {"region": region, "available": False, "error": str(e)}

def get_latest_ubuntu_ami(region: str, architecture: str = "x86_64") -> Optional[Dict[str, Any]]:
    """Get the latest Ubuntu 22.04 LTS AMI ID in a region."""
    try:
        if architecture == "arm64":
            name_pattern = "ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-arm64-server-*"
        else:
            name_pattern = "ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"
        
        client = boto3.client("ec2", region_name=region)
        response = client.describe_images(
            Owners=["099720109477"],
            Filters=[
                {"Name": "name", "Values": [name_pattern]},
                {"Name": "architecture", "Values": [architecture]},
                {"Name": "root-device-type", "Values": ["ebs"]},
                {"Name": "virtualization-type", "Values": ["hvm"]},
            ],
            MaxResults=1000,
        )
        
        images = sorted(response["Images"], key=lambda x: x["CreationDate"], reverse=True)
        if not images:
            return None
        
        return {
            "image_id": images[0]["ImageId"],
            "architecture": architecture,
            "name": images[0]["Name"],
            "creation_date": images[0]["CreationDate"],
        }
    except Exception as e:
        _get_console().print(f"Error getting AMI for region {region}, architecture {architecture}: {str(e)}")
        return None

# =============================================================================
# AWS INSTANCE MANAGEMENT
# =============================================================================

async def create_spot_instances(config: Config, db: MachineStateManager) -> int:
    """Create spot instances across all configured regions."""
    regions = config.get_regions()
    total_instances = config.get_total_instances()
    instances_per_region = max(1, total_instances // len(regions))
    
    _get_console().print(f"Creating {total_instances} instances across {len(regions)} regions...")
    
    created_count = 0
    for region in regions:
        try:
            ec2 = get_ec2_client(region)
            
            # Get region configuration
            region_config = config.get_region_config(region)
            if not region_config:
                _get_console().print(f"[red]No configuration found for region {region}[/red]")
                continue
            
            instance_type = region_config.get("machine_type", "t3.medium")
            
            # Get AMI
            ami_value = region_config.get("image", "auto")
            if ami_value == "auto":
                ami_info = get_latest_ubuntu_ami(region)
                if not ami_info:
                    _get_console().print(f"[red]No AMI found for region {region}[/red]")
                    continue
                ami_id = ami_info["image_id"]
            else:
                ami_id = ami_value
            
            # Create simple user data script
            user_data = f"""#!/bin/bash
apt-get update
apt-get install -y docker.io
systemctl enable docker
systemctl start docker
usermod -aG docker {config.get_username()}
"""
            
            # Request spot instances
            try:
                response = ec2.request_spot_instances(
                    InstanceCount=instances_per_region,
                    LaunchSpecification={
                        "ImageId": ami_id,
                        "InstanceType": instance_type,
                        "UserData": base64.b64encode(user_data.encode()).decode(),
                        "TagSpecifications": [{
                            "ResourceType": "instance",
                            "Tags": [
                                {"Key": FILTER_TAG_NAME, "Value": FILTER_TAG_VALUE},
                                {"Key": "Name", "Value": f"SpotInstance-{region}"},
                                {"Key": "Region", "Value": region},
                            ]
                        }],
                    },
                    Type="one-time"
                )
                
                spot_request_ids = [req["SpotInstanceRequestId"] for req in response["SpotInstanceRequests"]]
                _get_console().print(f"[green]Created {len(spot_request_ids)} spot requests in {region}[/green]")
                
                # Wait briefly for fulfillment
                await asyncio.sleep(10)
                
                # Check for fulfilled requests
                spot_response = ec2.describe_spot_instance_requests(SpotInstanceRequestIds=spot_request_ids)
                
                for req in spot_response["SpotInstanceRequests"]:
                    if req["State"] == "active" and "InstanceId" in req:
                        instance_id = req["InstanceId"]
                        
                        # Add to database
                        await db.add_machine(
                            instance_id=instance_id,
                            region=region,
                            instance_type=instance_type,
                            status="pending"
                        )
                        
                        created_count += 1
                        _get_console().print(f"[green]Instance {instance_id} created in {region}[/green]")
                
            except Exception as e:
                _get_console().print(f"[red]Error creating instances in {region}: {str(e)}[/red]")
                
        except Exception as e:
            _get_console().print(f"[red]Error processing region {region}: {str(e)}[/red]")
    
    return created_count

async def list_instances(db: MachineStateManager):
    """List all managed instances."""
    machines = await db.get_all_machines()
    
    if not machines:
        _get_console().print("[yellow]No instances found in database[/yellow]")
        return
    
    # Create table
    table = Table(title="Managed Spot Instances")
    table.add_column("Region", style="cyan")
    table.add_column("Instance ID", style="magenta")
    table.add_column("Type", style="green")
    table.add_column("Status", style="yellow")
    table.add_column("Public IP", style="blue")
    table.add_column("Created", style="white")
    
    # Check live status for each region
    regions = set(machine["region"] for machine in machines)
    live_status = {}
    
    for region in regions:
        try:
            ec2 = get_ec2_client(region)
            response = ec2.describe_instances(
                Filters=[
                    {"Name": f"tag:{FILTER_TAG_NAME}", "Values": [FILTER_TAG_VALUE]},
                ]
            )
            
            for reservation in response["Reservations"]:
                for instance in reservation["Instances"]:
                    live_status[instance["InstanceId"]] = {
                        "state": instance["State"]["Name"],
                        "public_ip": instance.get("PublicIpAddress", ""),
                        "private_ip": instance.get("PrivateIpAddress", "")
                    }
        except Exception as e:
            _get_console().print(f"[red]Error checking region {region}: {str(e)}[/red]")
    
    # Add rows to table
    for machine in machines:
        instance_id = machine["instance_id"]
        live_info = live_status.get(instance_id, {})
        
        status = live_info.get("state", machine["status"])
        if status == "running":
            status_display = "[green]running[/green]"
        elif status == "pending":
            status_display = "[yellow]pending[/yellow]"
        elif status in ["terminated", "stopped"]:
            status_display = "[red]terminated[/red]"
        else:
            status_display = status
        
        created_time = machine.get("created_at", "").split("T")[0] if machine.get("created_at") else ""
        
        table.add_row(
            machine["region"],
            instance_id[:12] + "..." if len(instance_id) > 12 else instance_id,
            machine.get("instance_type", ""),
            status_display,
            live_info.get("public_ip", machine.get("public_ip", "")),
            created_time
        )
    
    _get_console().print(table)
    _get_console().print(f"\n[bold]Total instances: {len(machines)}[/bold]")

async def destroy_instances(db: MachineStateManager) -> int:
    """Terminate all managed instances."""
    machines = await db.get_all_machines()
    
    if not machines:
        _get_console().print("[yellow]No instances to destroy[/yellow]")
        return 0
    
    regions = set(machine["region"] for machine in machines)
    terminated_count = 0
    
    for region in regions:
        try:
            ec2 = get_ec2_client(region)
            
            # Find instances in this region
            response = ec2.describe_instances(
                Filters=[
                    {"Name": f"tag:{FILTER_TAG_NAME}", "Values": [FILTER_TAG_VALUE]},
                    {"Name": "instance-state-name", "Values": ["running", "pending"]},
                ]
            )
            
            instance_ids = []
            for reservation in response["Reservations"]:
                for instance in reservation["Instances"]:
                    instance_ids.append(instance["InstanceId"])
            
            if instance_ids:
                ec2.terminate_instances(InstanceIds=instance_ids)
                terminated_count += len(instance_ids)
                _get_console().print(f"[green]Terminated {len(instance_ids)} instances in {region}[/green]")
            
            # Remove from database
            deleted_count = await db.delete_machines_by_region(region)
            _get_console().print(f"[blue]Removed {deleted_count} records from database for {region}[/blue]")
            
        except Exception as e:
            _get_console().print(f"[red]Error terminating instances in {region}: {str(e)}[/red]")
    
    return terminated_count

# =============================================================================
# ENVIRONMENT VALIDATION AND SETUP
# =============================================================================

def validate_environment() -> List[str]:
    """Validate that all required tools and configurations are available."""
    issues = []
    
    # Check AWS CLI
    if not shutil.which("aws"):
        issues.append("AWS CLI not found. Install from: https://aws.amazon.com/cli/")
    
    # Check AWS credentials
    try:
        session = boto3.Session()
        credentials = session.get_credentials()
        if not credentials:
            issues.append("AWS credentials not configured. Run: aws configure")
        else:
            # Test credentials
            sts = session.client('sts')
            sts.get_caller_identity()
    except Exception:
        issues.append("AWS credentials not configured. Run: aws configure")
    
    # Check config file exists
    if not os.path.exists("config.yaml"):
        issues.append("config.yaml not found. Create from config.yaml_example")
    
    return issues

def check_ssh_keys(config: Config) -> List[str]:
    """Check SSH key availability."""
    issues = []
    
    public_key_path = config.get_public_ssh_key_path()
    private_key_path = config.get_private_ssh_key_path()
    
    if not public_key_path or not os.path.exists(public_key_path):
        issues.append(f"Public SSH key not found at: {public_key_path}")
    
    if not private_key_path or not os.path.exists(private_key_path):
        issues.append(f"Private SSH key not found at: {private_key_path}")
    
    return issues

def setup_environment():
    """Setup the complete environment (regions, AMIs, config)."""
    _get_console().print("[bold green]Setting up environment...[/bold green]")
    
    # Initialize cache and refresh it during setup
    cache = AWSDataCache()
    _get_console().print("1. Refreshing AWS data cache...")
    cache.refresh_cache()
    
    # Find available regions using cached data where possible
    _get_console().print("2. Finding available AWS regions...")
    all_regions = cache.get_cached_regions() or get_all_aws_regions()
    results = []
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_region = {
            executor.submit(check_region_spot_availability, region): region
            for region in all_regions
        }
        
        for future in as_completed(future_to_region):
            region_result = future.result()
            results.append(region_result)
    
    available_regions = [r for r in results if r.get("available", False)]
    available_regions.sort(key=lambda x: x["cheapest_instance"]["spot_price"])
    
    region_names = [r["region"] for r in available_regions]
    
    # Save available regions data
    output_data = {
        "available_regions": region_names,
        "region_details": {r["region"]: r for r in available_regions},
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
    }
    
    with open("available_regions.json", "w") as f:
        json.dump(output_data, f, indent=2)
    
    _get_console().print(f"Found {len(available_regions)} regions with suitable spot instances")
    
    # Get Ubuntu AMIs (use cached data where available)
    _get_console().print("3. Getting Ubuntu AMIs...")
    ami_info = {}
    architectures = ["x86_64", "arm64"]
    
    # Try to get cached AMI data first
    cached_amis = cache.get_cached_amis()
    
    for region in region_names[:10]:  # Top 10 regions
        ami_info[region] = {}
        
        # Use cached data if fresh, otherwise fetch new
        if cached_amis and region in cached_amis.get("regions", {}):
            region_amis = cached_amis["regions"][region].get("amis", {})
            for arch in architectures:
                if arch in region_amis:
                    ami_info[region][arch] = region_amis[arch]
                else:
                    # Fetch missing architecture
                    ami_data = get_latest_ubuntu_ami(region, arch)
                    if ami_data:
                        ami_info[region][arch] = ami_data
        else:
            # Fetch all AMIs for this region
            for arch in architectures:
                ami_data = get_latest_ubuntu_ami(region, arch)
                if ami_data:
                    ami_info[region][arch] = ami_data
    
    # Save AMI data
    with open("ubuntu_amis.csv", "w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["Region", "Architecture", "AMI ID"])
        for region in region_names[:10]:
            for arch in architectures:
                if region in ami_info and arch in ami_info[region]:
                    ami_data = ami_info[region][arch]
                    writer.writerow([region, arch, ami_data["image_id"]])
    
    _get_console().print(f"Retrieved AMIs for {len(ami_info)} regions")
    
    # Generate config template if it doesn't exist
    if not os.path.exists("config.yaml"):
        _get_console().print("3. Generating configuration template...")
        
        config_template = {
            "aws": {
                "total_instances": 3,
                "username": "bacalhau-runner",
                "public_ssh_key_path": "~/.ssh/id_ed25519.pub",
                "private_ssh_key_path": "~/.ssh/id_ed25519",
            },
            "bacalhau": {
                "orchestrators": ["nats://<your_orchestrator_url>:4222"],
                "token": "<your_bacalhau_network_token>",
                "tls": True,
            },
            "regions": []
        }
        
        # Add top regions
        for region in region_names[:5]:  # Top 5 regions
            region_config = {"image": "auto", "machine_type": "t3.medium", "node_count": "auto"}
            
            if region in output_data["region_details"]:
                region_detail = output_data["region_details"][region]
                if region_detail.get("available", False):
                    instance_info = region_detail.get("cheapest_instance", {})
                    if instance_info.get("vcpus", 0) >= 2:
                        region_config["machine_type"] = instance_info["instance_type"]
            
            config_template["regions"].append({region: region_config})
        
        with open("config.yaml_example", "w") as f:
            yaml.dump(config_template, f, default_flow_style=False)
        
        _get_console().print("[yellow]Created config.yaml_example - please copy to config.yaml and customize[/yellow]")
    else:
        _get_console().print("3. Configuration file already exists")
    
    _get_console().print("[bold green]Environment setup complete![/bold green]")

def verify_environment(config_path: str = "config.yaml"):
    """Verify that the environment is properly configured."""
    _get_console().print("[bold blue]Verifying environment...[/bold blue]")
    
    issues = validate_environment()
    
    if os.path.exists(config_path):
        try:
            config = Config(config_path)
            issues.extend(check_ssh_keys(config))
        except Exception as e:
            issues.append(f"Config file error: {str(e)}")
    
    if issues:
        _get_console().print("[bold red]Environment validation failed:[/bold red]")
        for issue in issues:
            _get_console().print(f"  - {issue}")
        return False
    else:
        _get_console().print("[bold green]Environment validation passed![/bold green]")
        return True

def run_validation_tests(config_path: str = "config.yaml"):
    """Run basic validation tests."""
    _get_console().print("[bold blue]Running validation tests...[/bold blue]")
    
    tests_passed = 0
    tests_total = 0
    
    # Test 1: Environment validation
    tests_total += 1
    if verify_environment(config_path):
        tests_passed += 1
        _get_console().print("[green]✓[/green] Environment validation")
    else:
        _get_console().print("[red]✗[/red] Environment validation")
    
    # Test 2: Config loading
    tests_total += 1
    try:
        config = Config(config_path)
        regions = config.get_regions()
        if regions:
            tests_passed += 1
            _get_console().print(f"[green]✓[/green] Config loading ({len(regions)} regions)")
        else:
            _get_console().print("[red]✗[/red] Config loading (no regions found)")
    except Exception as e:
        _get_console().print(f"[red]✗[/red] Config loading: {str(e)}")
    
    # Test 3: AWS connectivity
    tests_total += 1
    try:
        session = boto3.Session()
        credentials = session.get_credentials()
        if credentials:
            tests_passed += 1
            _get_console().print("[green]✓[/green] AWS connectivity")
        else:
            _get_console().print("[red]✗[/red] AWS connectivity (no credentials)")
    except Exception as e:
        _get_console().print(f"[red]✗[/red] AWS connectivity: {str(e)}")
    
    # Summary
    _get_console().print(f"\n[bold]Test Results: {tests_passed}/{tests_total} passed[/bold]")
    
    if tests_passed == tests_total:
        _get_console().print("[bold green]All tests passed! Ready for deployment.[/bold green]")
        return True
    else:
        _get_console().print("[bold yellow]Some tests failed. Please resolve issues before deployment.[/bold yellow]")
        return False

# =============================================================================
# MAIN CLI INTERFACE
# =============================================================================

def show_help_fast():
    """Show help without loading heavy dependencies (fast startup)."""
    if _verbose:
        print(f"⚡ Fast help mode (no heavy imports needed)")
    executable_name = os.path.basename(sys.argv[0])
    
    help_text = f"""AWS Spot Instance Deployment Tool for Bacalhau Clusters

USAGE:
    {executable_name} [COMMAND] [OPTIONS]

COMMANDS:
    setup      Setup environment (find regions, get AMIs, create config template)
    verify     Verify configuration and environment are ready
    validate   Run comprehensive validation tests
    create     Deploy spot instances across configured regions
    list       List all managed spot instances with status
    status     Show detailed status of deployment and instances
    destroy    Terminate all managed spot instances
    cleanup    Full cleanup (terminate instances + remove VPC resources)
    cache      Manage AWS data cache (refresh, stats, clear)
    help       Show this help message

OPTIONS:
    --config PATH    Use custom configuration file (default: config.yaml)
    -v, --verbose    Show detailed timing and import information

EXAMPLES:
    # Initial setup for new users
    {executable_name} setup
    cp config.yaml_example config.yaml
    # Edit config.yaml with your settings
    {executable_name} verify

    # Deploy instances
    {executable_name} create

    # Check status
    {executable_name} list
    {executable_name} status

    # Cleanup
    {executable_name} destroy

    # Cache management
    {executable_name} cache stats
    {executable_name} cache refresh

CONFIGURATION:
    The tool uses config.yaml for settings. Key sections:
    
    aws:
        total_instances: 3                    # Total instances to create
        username: bacalhau-runner            # SSH username for instances
        public_ssh_key_path: ~/.ssh/id_ed25519.pub
        private_ssh_key_path: ~/.ssh/id_ed25519
    
    bacalhau:
        orchestrators: 
          - nats://your-orchestrator:4222    # Bacalhau NATS endpoints
        token: your_network_token            # Authentication token
        tls: true                           # Use TLS for connections
    
    regions:
        - us-west-2:
            image: auto                      # Auto-select Ubuntu AMI
            machine_type: t3.medium         # Instance type
            node_count: auto                # Auto-distribute instances

ENVIRONMENT REQUIREMENTS:
    - AWS CLI configured with credentials (aws configure)
    - SSH key pair for instance access
    - Internet connection for API calls

TROUBLESHOOTING:
    - Check debug_deploy_spot.log for detailed logging
    - Run 'validate' command to diagnose issues
    - Ensure AWS credentials have EC2 permissions
    - Verify SSH keys exist and are accessible

SUPPORT:
    For issues and documentation:
    - GitHub: https://github.com/your-org/aws-spot-deployer
    - Documentation: See PORTABLE_DISTRIBUTION.md
"""
    print(help_text)

def show_help():
    """Show comprehensive help information with rich formatting."""
    _ensure_imports()
    # Dynamically determine the executable name
    executable_name = os.path.basename(sys.argv[0])
    
    help_text = f"""
[bold]AWS Spot Instance Deployment Tool for Bacalhau Clusters[/bold]

[yellow]USAGE:[/yellow]
    {executable_name} [COMMAND] [OPTIONS]

[yellow]COMMANDS:[/yellow]
    [green]setup[/green]      Setup environment (find regions, get AMIs, create config template)
    [green]verify[/green]     Verify configuration and environment are ready
    [green]validate[/green]   Run comprehensive validation tests
    [green]create[/green]     Deploy spot instances across configured regions
    [green]list[/green]       List all managed spot instances with status
    [green]status[/green]     Show detailed status of deployment and instances
    [green]destroy[/green]    Terminate all managed spot instances
    [green]cleanup[/green]    Full cleanup (terminate instances + remove VPC resources)
    [green]cache[/green]      Manage AWS data cache (refresh, stats, clear)
    [green]help[/green]       Show this help message

[yellow]OPTIONS:[/yellow]
    [blue]--config PATH[/blue]    Use custom configuration file (default: config.yaml)

[yellow]EXAMPLES:[/yellow]
    # Initial setup for new users
    {executable_name} setup
    cp config.yaml_example config.yaml
    # Edit config.yaml with your settings
    {executable_name} verify

    # Deploy instances
    {executable_name} create

    # Check status
    {executable_name} list
    {executable_name} status

    # Cleanup
    {executable_name} destroy

    # Cache management
    {executable_name} cache stats
    {executable_name} cache refresh

[yellow]CONFIGURATION:[/yellow]
    The tool uses config.yaml for settings. Key sections:
    
    [blue]aws:[/blue]
        total_instances: 3                    # Total instances to create
        username: bacalhau-runner            # SSH username for instances
        public_ssh_key_path: ~/.ssh/id_ed25519.pub
        private_ssh_key_path: ~/.ssh/id_ed25519
    
    [blue]bacalhau:[/blue]
        orchestrators: 
          - nats://your-orchestrator:4222    # Bacalhau NATS endpoints
        token: your_network_token            # Authentication token
        tls: true                           # Use TLS for connections
    
    [blue]regions:[/blue]
        - us-west-2:
            image: auto                      # Auto-select Ubuntu AMI
            machine_type: t3.medium         # Instance type
            node_count: auto                # Auto-distribute instances

[yellow]ENVIRONMENT REQUIREMENTS:[/yellow]
    - AWS CLI configured with credentials (aws configure)
    - SSH key pair for instance access
    - Internet connection for API calls

[yellow]TROUBLESHOOTING:[/yellow]
    - Check debug_deploy_spot.log for detailed logging
    - Run 'validate' command to diagnose issues
    - Ensure AWS credentials have EC2 permissions
    - Verify SSH keys exist and are accessible

[yellow]SUPPORT:[/yellow]
    For issues and documentation:
    - GitHub: https://github.com/your-org/aws-spot-deployer
    - Documentation: See PORTABLE_DISTRIBUTION.md
"""
    _get_console().print(help_text)

def handle_cache_command():
    """Handle cache management commands."""
    # Parse cache subcommand
    if len(sys.argv) < 3:
        _get_console().print("[bold blue]AWS Data Cache Management[/bold blue]")
        _get_console().print("\nAvailable cache commands:")
        _get_console().print("  cache refresh  - Refresh all cached data")
        _get_console().print("  cache stats    - Show cache statistics")
        _get_console().print("  cache clear    - Clear all cached data")
        _get_console().print("\nExample: ./deploy_spot.py cache stats")
        return
    
    cache_command = sys.argv[2]
    cache = AWSDataCache()
    
    if cache_command == "refresh":
        _get_console().print("[bold blue]Refreshing AWS data cache...[/bold blue]")
        cache.refresh_cache()
        _get_console().print("[green]✓ Cache refresh complete[/green]")
        
    elif cache_command == "stats":
        _get_console().print("[bold blue]Cache Statistics[/bold blue]")
        stats = cache.get_cache_stats()
        
        table = Table(title="AWS Data Cache Status")
        table.add_column("Cache Type", style="cyan")
        table.add_column("Status", style="yellow")
        table.add_column("Size", style="green")
        table.add_column("Records", style="blue")
        table.add_column("Last Updated", style="white")
        
        for cache_type, stat in stats.items():
            status = "[green]Fresh[/green]" if stat.get("is_fresh", False) else "[red]Stale[/red]"
            size = f"{stat.get('size_bytes', 0) / 1024:.1f} KB" if stat.get('size_bytes', 0) > 0 else "0 KB"
            records = str(stat.get('record_count', 0))
            last_updated = stat.get('last_updated', 'Never')[:19] if stat.get('last_updated') else 'Never'
            
            table.add_row(cache_type, status, size, records, last_updated)
        
        _get_console().print(table)
        
        # Show cache directory info
        cache_path = Path(CACHE_DIR)
        if cache_path.exists():
            total_size = sum(f.stat().st_size for f in cache_path.rglob('*') if f.is_file())
            _get_console().print(f"\nTotal cache size: {total_size / 1024:.1f} KB")
            _get_console().print(f"Cache location: {cache_path.absolute()}")
        
    elif cache_command == "clear":
        _get_console().print("[bold red]Clearing AWS data cache...[/bold red]")
        cache_path = Path(CACHE_DIR)
        if cache_path.exists():
            import shutil
            shutil.rmtree(cache_path)
            _get_console().print("[green]✓ Cache cleared[/green]")
        else:
            _get_console().print("[yellow]No cache to clear[/yellow]")
    
    else:
        _get_console().print(f"[red]Unknown cache command: {cache_command}[/red]")
        _get_console().print("Available commands: refresh, stats, clear")

def main():
    """Main CLI interface."""
    if _verbose:
        print(f"🎯 Main function started at {time.time() - _start_time:.3f}s")
    
    # Fast path for help commands - no heavy imports needed
    if len(sys.argv) < 2 or sys.argv[1] in ["-h", "--help", "help"]:
        if _verbose:
            print("📋 Help command detected - using fast path")
        show_help_fast()
        if _verbose:
            print(f"🏁 Total execution time: {time.time() - _start_time:.3f}s")
        return 0
    
    # Parse command and options
    command = sys.argv[1]
    valid_commands = ["setup", "verify", "validate", "create", "list", "status", "destroy", "cleanup", "cache", "help"]
    
    # Fast path for unknown commands - no heavy imports needed
    if command not in valid_commands:
        print(f"Unknown command: {command}")
        print(f"Valid commands: {', '.join(valid_commands)}")
        print("Run 'help' for more information.")
        return 1
    
    # Only load heavy imports when we actually need them
    _ensure_imports()
    
    # Initialize cache for lazy loading (except for setup which handles its own cache)
    # Skip cache initialization during tests
    if not getattr(sys.modules[__name__], 'DISABLE_CACHE_FOR_TESTS', False):
        cache = AWSDataCache()
        if command not in ["help", "setup"]:
            try:
                cache.ensure_cache_fresh()
            except Exception as e:
                logger.debug(f"Cache initialization failed: {e}")
                _get_console().print("[yellow]Warning: Cache initialization failed, continuing without cache[/yellow]")
    
    # Parse optional arguments
    config_path = "config.yaml"
    for i, arg in enumerate(sys.argv[2:], 2):
        if arg == "--config" and i + 1 < len(sys.argv):
            config_path = sys.argv[i + 1]
        elif arg.startswith("--config="):
            config_path = arg.split("=", 1)[1]
    
    try:
        if command == "help":
            show_help()
            return 0
        elif command == "setup":
            setup_environment()
        elif command == "verify":
            verify_environment(config_path)
        elif command == "validate":
            run_validation_tests(config_path)
        elif command == "cache":
            handle_cache_command()
        elif command in ["create", "list", "status", "destroy", "cleanup"]:
            # These require config file and async execution
            if not os.path.exists(config_path):
                _get_console().print(f"[red]Configuration file not found: {config_path}[/red]")
                _get_console().print("Run 'setup' to create a configuration template.")
                return 1
            
            # Run async operations
            return asyncio.run(run_async_command(command, config_path))
        else:
            _get_console().print(f"[red]Command not implemented: {command}[/red]")
            return 1
    
    except KeyboardInterrupt:
        _get_console().print("\n[yellow]Operation cancelled by user[/yellow]")
        return 1
    except Exception as e:
        _get_console().print(f"[red]Error: {str(e)}[/red]")
        logger.exception("Unexpected error in main")
        return 1
    
    return 0

async def run_async_command(command: str, config_path: str) -> int:
    """Run async commands that require database and AWS operations."""
    try:
        config = Config(config_path)
        db = MachineStateManager()
        
        if command == "create":
            _get_console().print("[bold blue]Creating spot instances...[/bold blue]")
            created_count = await create_spot_instances(config, db)
            _get_console().print(f"[bold green]Successfully created {created_count} instances[/bold green]")
            
        elif command == "list":
            _get_console().print("[bold blue]Listing spot instances...[/bold blue]")
            await list_instances(db)
            
        elif command == "status":
            _get_console().print("[bold blue]Checking status...[/bold blue]")
            await list_instances(db)
            # Add more status checks here
            
        elif command == "destroy":
            _get_console().print("[bold red]Destroying spot instances...[/bold red]")
            terminated_count = await destroy_instances(db)
            _get_console().print(f"[bold green]Successfully terminated {terminated_count} instances[/bold green]")
            
        elif command == "cleanup":
            _get_console().print("[bold red]Performing full cleanup...[/bold red]")
            terminated_count = await destroy_instances(db)
            _get_console().print(f"[bold green]Cleanup complete: {terminated_count} instances terminated[/bold green]")
        
        return 0
        
    except Exception as e:
        _get_console().print(f"[red]Command failed: {str(e)}[/red]")
        logger.exception(f"Error in {command} command")
        return 1

if __name__ == "__main__":
    sys.exit(main())