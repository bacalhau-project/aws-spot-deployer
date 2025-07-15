# Project Deployment Standards

## Core Principle: Always Fresh Deployments

**IMPORTANT**: This project follows a strict "immutable infrastructure" approach. Any changes to the deployment system require a full teardown and fresh deployment. Do not attempt to patch or update existing instances.

## Development Workflow

### 1. Making Changes
When modifying any deployment-related files:
- Edit the files in the repository
- Test locally with linting: `uv run ruff check deploy_spot.py`
- Commit changes to version control

### 2. Testing Changes
**ALWAYS follow this sequence:**
```bash
# 1. Destroy ALL existing instances
uv run -s deploy_spot.py destroy

# 2. Verify cleanup is complete
uv run -s deploy_spot.py list  # Should show no instances

# 3. Deploy fresh instances with new code
uv run -s deploy_spot.py create

# 4. Test the deployment
./debug_deployment.sh <new-instance-ip>
```

### 3. Never Do This
- ❌ SSH into instances to manually fix issues
- ❌ Upload patches or fixes to running instances
- ❌ Use "quick fix" scripts on production deployments
- ❌ Attempt to update services on existing instances

### 4. Always Do This
- ✅ Destroy all instances before testing changes
- ✅ Deploy fresh instances from scratch
- ✅ Treat instances as disposable
- ✅ Fix issues in the deployment code, not on instances

## Why This Approach?

1. **Reproducibility**: Every deployment is identical
2. **Reliability**: No accumulated state or configuration drift
3. **Simplicity**: One deployment path to maintain
4. **Testing**: Changes are always tested in clean environments

## File Organization

### Deployment Scripts
- `deploy_spot.py` - Main deployment orchestrator
- `instance/scripts/deploy_services.py` - Post-upload configuration script
- `instance/scripts/*.service` - SystemD service definitions
- `instance/scripts/*.py` - Service implementation scripts

### Testing Scripts
- `debug_deployment.sh` - Comprehensive deployment verification
- `test_*.py` - Unit tests for deployment components
- `delete_vpcs.py` - VPC cleanup utility

### When Making Changes

1. **To deployment logic**: Edit `deploy_spot.py`
2. **To service configuration**: Edit `instance/scripts/deploy_services.py`
3. **To service definitions**: Edit `instance/scripts/*.service`
4. **To cloud-init**: Edit `generate_minimal_cloud_init()` in `deploy_spot.py`

## Deployment Architecture

```
┌─────────────────┐
│  deploy_spot.py │ (Orchestrator)
└────────┬────────┘
         │
         ├─── 1. Create EC2 instances with cloud-init
         │        (Basic setup: packages, users, Docker)
         │
         ├─── 2. Upload files to /tmp/exs/ and /tmp/uploaded_files/
         │
         └─── 3. Execute deploy_services.py via SSH
                  │
                  ├─── Wait for cloud-init completion
                  ├─── Move files to final locations
                  ├─── Install SystemD services
                  ├─── Enable services
                  └─── Schedule reboot
```

## Testing Checklist

After any deployment change:
- [ ] All instances destroyed (`uv run -s deploy_spot.py destroy`)
- [ ] No instances remain (`uv run -s deploy_spot.py list`)
- [ ] Fresh deployment started (`uv run -s deploy_spot.py create`)
- [ ] Services are enabled (`systemctl list-unit-files | grep -E "(bacalhau|sensor)"`)
- [ ] Files in correct locations (`ls /opt/uploaded_files/scripts/`)
- [ ] Services start after reboot
- [ ] No errors in deployment log (`cat /opt/deployment.log`)

## Emergency Debugging

If you must debug a running instance:
1. Use `./debug_deployment.sh <ip>` to collect diagnostics
2. Fix the issue in the source code
3. Destroy all instances
4. Deploy fresh instances
5. Verify the fix works on clean deployments

Remember: The goal is a reliable, repeatable deployment process. Every instance should be identical and disposable.