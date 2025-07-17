def create_deployment_bundle(config: SimpleConfig) -> str:
    """Create a tar.gz bundle of all deployment files."""
    import tarfile
    import tempfile
    
    bundle_file = os.path.join(tempfile.gettempdir(), "deployment-bundle.tar.gz")
    
    with tarfile.open(bundle_file, "w:gz") as tar:
        # Add scripts
        scripts_dir = config.scripts_directory()
        if os.path.exists(scripts_dir):
            for file in os.listdir(scripts_dir):
                filepath = os.path.join(scripts_dir, file)
                if os.path.isfile(filepath):
                    tar.add(filepath, arcname=f"scripts/{file}")
        
        # Add configs
        config_dir = "instance/config"
        if os.path.exists(config_dir):
            for file in os.listdir(config_dir):
                filepath = os.path.join(config_dir, file)
                if os.path.isfile(filepath):
                    tar.add(filepath, arcname=f"config/{file}")
        
        # Add other files (except credentials)
        files_dir = config.files_directory()
        if os.path.exists(files_dir):
            for file in os.listdir(files_dir):
                if file in ["orchestrator_endpoint", "orchestrator_token"]:
                    continue
                filepath = os.path.join(files_dir, file)
                if os.path.isfile(filepath):
                    tar.add(filepath, arcname=f"files/{file}")
    
    return bundle_file


def upload_deployment_bundle(hostname: str, username: str, private_key_path: str, bundle_file: str, logger=None) -> bool:
    """Upload deployment bundle to instance."""
    
    remote_path = "/opt/deployment-bundle.tar.gz"
    
    scp_command = [
        "scp",
        "-i", private_key_path,
        "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=/dev/null",
        "-o", "ConnectTimeout=10",
        bundle_file,
        f"{username}@{hostname}:{remote_path}"
    ]
    
    try:
        result = subprocess.run(scp_command, capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            if logger:
                logger.info(f"Successfully uploaded bundle to {hostname}")
            return True
        else:
            if logger:
                logger.error(f"Failed to upload bundle: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        if logger:
            logger.error("Upload timed out after 60 seconds")
        return False
    except Exception as e:
        if logger:
            logger.error(f"Upload failed: {e}")
        return False