# Deployment Workflow - Immutable Infrastructure

## The Golden Rule

**Every change requires a full teardown and redeploy. No exceptions.**

## Step-by-Step Workflow

### 1. Before Making Changes
```bash
# Always start with a clean slate
uv run -s deploy_spot.py list  # Note any existing instances
uv run -s deploy_spot.py destroy  # Destroy everything
```

### 2. Make Your Changes
Edit the appropriate files:
- `deploy_spot.py` - Main deployment logic
- `instance/scripts/deploy_services.py` - Service configuration
- `instance/scripts/*.service` - SystemD service definitions
- `instance/scripts/*.py` - Service implementations

### 3. Test Locally
```bash
# Always lint before deploying
uv run ruff check deploy_spot.py

# Run unit tests if applicable
uv run python test_simple.py
```

### 4. Deploy Fresh Instances
```bash
# Deploy new instances with your changes
uv run -s deploy_spot.py create

# Wait for deployment to complete (watch the output)
# Note the IP addresses of created instances
```

### 5. Verify Deployment
```bash
# Run comprehensive debug check
./debug_deployment.sh <instance-ip>

# Check deployment log
ssh ubuntu@<instance-ip> "cat /opt/deployment.log"

# Verify services after reboot (wait ~2 minutes)
ssh ubuntu@<instance-ip> "systemctl status bacalhau.service sensor-generator.service"
```

### 6. If Issues Found
```bash
# 1. Document the issue
# 2. Fix in source code (NOT on the instance)
# 3. Destroy all instances
uv run -s deploy_spot.py destroy

# 4. Go back to step 4
```

## What Not To Do

### ❌ Anti-Patterns (NEVER DO THESE)
```bash
# WRONG: Trying to fix a running instance
ssh ubuntu@instance "sudo vim /etc/systemd/system/some.service"
ssh ubuntu@instance "sudo systemctl restart some-service"
scp fixed-file.py ubuntu@instance:/tmp/
./quick_fix_deploy.sh instance-ip  # Only for emergency debugging

# WRONG: Partial deployments
"I'll just update this one instance to test"
"Let me keep this working instance and deploy another"
```

### ✅ Correct Patterns (ALWAYS DO THESE)
```bash
# RIGHT: Full cycle for every change
uv run -s deploy_spot.py destroy
uv run -s deploy_spot.py create
./debug_deployment.sh <new-instance-ip>

# RIGHT: Fix in code, not on instance
vim instance/scripts/some-service.py  # Fix the source
uv run -s deploy_spot.py destroy     # Remove old instances
uv run -s deploy_spot.py create      # Deploy with fix
```

## Why This Matters

1. **Reproducibility**: Every deployment is identical
2. **No State Drift**: Instances don't accumulate manual changes
3. **Clean Testing**: Each test starts from known state
4. **Documentation**: All changes are in code, not hidden on instances

## Quick Reference Card

```
┌─────────────────────────────────────────────┐
│          DEPLOYMENT QUICK REFERENCE         │
├─────────────────────────────────────────────┤
│ See existing:  uv run -s deploy_spot.py list│
│ Destroy all:   uv run -s deploy_spot.py destroy│
│ Create new:    uv run -s deploy_spot.py create│
│ Debug:         ./debug_deployment.sh <ip>   │
│                                             │
│ Remember: ALWAYS destroy before create!     │
└─────────────────────────────────────────────┘
```

## Emergency Debugging

If you absolutely must investigate a running instance:

1. Use read-only commands only
2. Document what you find
3. Fix the issue in source code
4. Destroy the instance
5. Deploy fresh with the fix

```bash
# OK for investigation only
ssh ubuntu@<ip> "cat /opt/deployment.log"
ssh ubuntu@<ip> "systemctl status some.service"
ssh ubuntu@<ip> "ls -la /opt/uploaded_files/"

# After investigation
uv run -s deploy_spot.py destroy
# Fix issue in source
uv run -s deploy_spot.py create
```

## The Deployment Cycle

```
     ┌─────────┐
     │  CODE   │
     │ CHANGES │
     └────┬────┘
          │
          ▼
     ┌─────────┐
     │ DESTROY │ ← Always destroy first!
     │   ALL   │
     └────┬────┘
          │
          ▼
     ┌─────────┐
     │ CREATE  │
     │  FRESH  │
     └────┬────┘
          │
          ▼
     ┌─────────┐
     │  TEST   │
     │ VERIFY  │
     └────┬────┘
          │
    ┌─────┴─────┐
    │           │
    ▼           ▼
 ┌──────┐   ┌──────┐
 │ PASS │   │ FAIL │
 └──────┘   └───┬──┘
                │
                └──→ Back to CODE CHANGES
```

This is the way.