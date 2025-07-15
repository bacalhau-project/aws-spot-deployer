# Cloud-Init Debug Commands

Run these commands on your EC2 instance to debug cloud-init issues:

## 1. Check cloud-init status
```bash
cloud-init status --wait --long
```

## 2. Check cloud-init output log (most important)
```bash
sudo cat /var/log/cloud-init-output.log | tail -100
```

## 3. Check if user-data was received
```bash
sudo cat /var/lib/cloud/instance/user-data.txt | head -50
```

## 4. Check for our custom directories
```bash
ls -la /opt/uploaded_files/
ls -la /tmp/exs/
ls -la /var/log/startup-progress.log
```

## 5. Check systemd services
```bash
systemctl list-units --all | grep -E "(bacalhau|sensor|setup)"
```

## 6. Check cloud-init journal
```bash
sudo journalctl -u cloud-init --no-pager | tail -50
```

## 7. Check if Docker was installed
```bash
docker --version
docker compose version
```

## 8. Check for any cloud-init errors
```bash
sudo grep -i error /var/log/cloud-init.log | tail -20
```

## Common Issues and Solutions

### Issue: User-data not found or empty
This means the cloud-init script wasn't passed correctly to the instance. Check:
- The base64 encoding in deploy_spot.py
- AWS IAM permissions for passing user-data

### Issue: Commands in runcmd not executing
Check if cloud-init is using the correct interpreter:
- Look for bash syntax errors in the output log
- Check if the YAML formatting is correct

### Issue: Directories not created
Could be permission issues or the runcmd section not executing:
- Check if the ubuntu user exists
- Check if sudo commands are working

### Issue: Status file not created
The echo commands might be failing:
- Check if /tmp is writable
- Look for any filesystem issues