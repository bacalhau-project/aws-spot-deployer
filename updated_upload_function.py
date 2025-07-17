def upload_deployment_bundle(hostname: str, username: str, private_key_path: str, bundle_file: str, logger=None) -> bool:
    """Upload deployment bundle to instance and create completion marker."""
    
    # Upload bundle to /tmp
    bundle_temp_path = "/tmp/deployment-bundle.tar.gz"
    marker_path = "/tmp/UPLOAD_COMPLETE"
    
    scp_command = [
        "scp",
        "-i", private_key_path,
        "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=/dev/null",
        "-o", "ConnectTimeout=10",
        bundle_file,
        f"{username}@{hostname}:{bundle_temp_path}"
    ]
    
    try:
        # Upload bundle
        result = subprocess.run(scp_command, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            if logger:
                logger.error(f"Failed to upload bundle: {result.stderr}")
            return False
        
        # Create completion marker
        ssh_command = [
            "ssh",
            "-i", private_key_path,
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            f"{username}@{hostname}",
            f"touch {marker_path}"
        ]
        
        result = subprocess.run(ssh_command, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            if logger:
                logger.info(f"Successfully uploaded bundle to {hostname}")
            return True
        else:
            if logger:
                logger.error(f"Failed to create upload marker: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        if logger:
            logger.error("Upload timed out after 60 seconds")
        return False
    except Exception as e:
        if logger:
            logger.error(f"Upload failed: {e}")
        return False