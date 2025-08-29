# Portable Spot Deployer Rearchitecture Plan

## Philosophy & Vision

### Core Philosophy
Transform the spot deployer from a Bacalhau-specific tool into a **universal AWS spot instance deployment framework** that works for ANY project with zero code changes. Users should be able to deploy their applications using a single command, regardless of the application type, language, or infrastructure requirements.

### Design Principles
1. **Convention Over Configuration** - Work out-of-the-box with sensible defaults
2. **Progressive Enhancement** - Simple projects need minimal setup, complex projects can add more control
3. **Zero Lock-in** - No requirement to modify user's code or project structure
4. **Universal Command** - Same `uvx` command works for everyone
5. **Explicit is Better** - When conventions aren't enough, use explicit manifests
6. **Fail Gracefully** - Clear error messages and helpful suggestions

### Final End User Experience

#### Simplest Case (Convention-based)
```bash
# User has this structure:
my-app/
├── deployment/
│   └── setup.sh       # Their setup script
└── .spot/
    └── config.yaml    # AWS regions and instance types

# They run:
uvx --from github.com/sst/opencode spot-deployer create

# Done! Their app is deployed.
```

#### Advanced Case (Manifest-based)
```bash
# User has complex requirements:
my-app/
├── .spot/
│   ├── config.yaml       # AWS settings
│   └── deployment.yaml   # Explicit deployment instructions
├── deployment/
│   ├── scripts/
│   ├── configs/
│   └── services/
└── secrets/              # Sensitive files

# Same command:
uvx --from github.com/sst/opencode spot-deployer create

# The manifest controls everything.
```

#### External Tarball Case
```bash
# User references external deployment package:
my-app/
└── .spot/
    ├── config.yaml
    └── deployment.yaml   # Points to tarball URL

# Same command works:
uvx --from github.com/sst/opencode spot-deployer create
```

## Detailed Implementation Todolist

### Phase 1: Foundation - Deployment Discovery System

1. **Create deployment discovery module** (`spot_deployer/core/deployment_discovery.py`)
   - Define DeploymentDiscovery class
   - Add method to detect deployment mode (portable/convention/legacy)
   - Add method to find project root (looks for .spot/ or deployment/)
   - Add method to validate discovered structure
   - Return deployment configuration object

2. **Define deployment configuration schema** (`spot_deployer/core/deployment_schema.py`)
   - Create DeploymentConfig dataclass
   - Define fields: packages, files, scripts, services, tarball
   - Add validation methods for each field
   - Add method to merge with AWS config
   - Add serialization/deserialization methods

3. **Create manifest parser** (`spot_deployer/core/manifest_parser.py`)
   - Add YAML manifest parser for .spot/deployment.yaml
   - Support version field for future compatibility
   - Parse packages list
   - Parse upload mappings (source -> dest with permissions)
   - Parse scripts (command + working_dir)
   - Parse services list
   - Parse tarball configuration (URL or local path)
   - Add schema validation with helpful errors

4. **Implement convention scanner** (`spot_deployer/core/convention_scanner.py`)
   - Scan for deployment/ directory
   - Auto-detect scripts in deployment/scripts/
   - Auto-detect configs in deployment/configs/
   - Auto-detect *.service files
   - Auto-detect setup.sh or init.sh as main script
   - Build DeploymentConfig from discovered files
   - Add logging for what was auto-discovered

### Phase 2: Cloud-Init Generation Refactor

5. **Create portable cloud-init generator** (`spot_deployer/utils/portable_cloud_init.py`)
   - Accept DeploymentConfig as input
   - Generate package installation section
   - Generate file upload preparation
   - Generate script execution commands
   - Support both inline scripts and script files
   - Add proper error handling and logging
   - Generate systemd service installation

6. **Create cloud-init template system** (`spot_deployer/templates/`)
   - Create base cloud-init template
   - Add injection points for packages
   - Add injection points for scripts
   - Add injection points for files
   - Support user overrides via .spot/cloud-init.yaml
   - Add template validation

7. **Implement tarball handler** (`spot_deployer/utils/tarball_handler.py`)
   - Add method to validate tarball URL/path
   - Generate wget/curl commands for URL
   - Generate extraction commands
   - Add integrity check support (optional checksums)
   - Handle local tarball upload
   - Add progress tracking for large tarballs

### Phase 3: File Transfer Refactor

8. **Create generic file uploader** (`spot_deployer/utils/file_uploader.py`)
   - Accept DeploymentConfig upload mappings
   - Handle directory recursion
   - Preserve permissions from manifest
   - Support exclude patterns
   - Add progress bars for multiple files
   - Batch uploads for efficiency
   - Add retry logic for failed uploads

9. **Implement deployment bundler** (`spot_deployer/utils/deployment_bundler.py`)
   - Create tar.gz of user's deployment files
   - Support include/exclude patterns
   - Add compression options
   - Generate manifest of included files
   - Add size validation
   - Support incremental updates (future)

10. **Create secrets handler** (`spot_deployer/utils/secrets_handler.py`)
    - Detect secrets/ or credentials/ directory
    - Add special handling for sensitive files
    - Set restrictive permissions (0600)
    - Support environment variable files
    - Add encryption support (future)
    - Never log secret file contents

### Phase 4: Service Management Refactor

11. **Create service installer** (`spot_deployer/utils/service_installer.py`)
    - Auto-detect systemd service files
    - Generate service installation commands
    - Handle service dependencies
    - Support service templates with variable substitution
    - Add service validation
    - Generate enable/start commands

12. **Implement service orchestrator** (`spot_deployer/utils/service_orchestrator.py`)
    - Define service startup order
    - Handle service dependencies
    - Add health check support
    - Generate status check commands
    - Support docker-compose files
    - Add restart policies

### Phase 5: Configuration Management

13. **Refactor config loader** (`spot_deployer/core/config_v2.py`)
    - Keep backward compatibility with existing config
    - Add deployment-specific configuration
    - Support .spot/config.yaml for AWS settings
    - Support .spot/deployment.yaml for deployment settings
    - Add config inheritance/merging
    - Add environment variable support

14. **Create config validator** (`spot_deployer/utils/config_validator_v2.py`)
    - Validate AWS configuration separately
    - Validate deployment configuration
    - Check for required files/directories
    - Provide helpful error messages
    - Suggest fixes for common issues
    - Add --validate-only flag

15. **Implement config generator** (`spot_deployer/utils/config_generator.py`)
    - Interactive setup for .spot/config.yaml
    - Auto-generate deployment.yaml from discovered files
    - Add templates for common scenarios
    - Support config migration from v1
    - Add config diff tool

### Phase 6: Command Refactor

16. **Update create command** (`spot_deployer/commands/create_v2.py`)
    - Detect deployment mode first
    - Use appropriate generator based on mode
    - Support --deployment-dir flag
    - Support --manifest flag
    - Add --dry-run support
    - Show what will be deployed

17. **Add validate command** (`spot_deployer/commands/validate.py`)
    - Validate project structure
    - Check deployment configuration
    - Verify file permissions
    - Test tarball accessibility
    - Validate service files
    - Show deployment plan

18. **Add init command** (`spot_deployer/commands/init.py`)
    - Create .spot/ directory
    - Generate config.yaml template
    - Generate deployment.yaml template
    - Create example deployment/ structure
    - Add .gitignore entries
    - Show next steps

### Phase 7: Legacy Support & Migration

19. **Create legacy mode detector** (`spot_deployer/core/legacy_detector.py`)
    - Check for instance/scripts directory
    - Check for Bacalhau configuration
    - Check for sensor configuration
    - Return legacy mode flag
    - Log deprecation warnings

20. **Implement legacy adapter** (`spot_deployer/adapters/legacy_adapter.py`)
    - Convert legacy structure to DeploymentConfig
    - Map old paths to new structure
    - Handle backward compatibility
    - Generate migration suggestions
    - Support gradual migration

21. **Create migration tool** (`spot_deployer/utils/migrator.py`)
    - Analyze existing project
    - Generate new structure
    - Copy files to new locations
    - Update configuration
    - Create migration report
    - Add rollback support

### Phase 8: Testing Infrastructure

22. **Create test fixtures** (`tests/fixtures/`)
    - Simple deployment example
    - Complex deployment example
    - Manifest-based example
    - Tarball-based example
    - Legacy structure example
    - Mixed mode example

23. **Add discovery tests** (`tests/test_deployment_discovery.py`)
    - Test convention detection
    - Test manifest detection
    - Test legacy detection
    - Test invalid structures
    - Test edge cases
    - Test error messages

24. **Add generator tests** (`tests/test_cloud_init_generator.py`)
    - Test package installation
    - Test script execution
    - Test file uploads
    - Test service installation
    - Test tarball handling
    - Test template rendering

25. **Add integration tests** (`tests/integration/`)
    - Test full deployment flow
    - Test with real AWS (optional)
    - Test file uploads
    - Test service startup
    - Test rollback scenarios
    - Test migration paths

### Phase 9: Documentation

26. **Create user guide** (`docs/USER_GUIDE.md`)
    - Quick start section
    - Convention-based deployment
    - Manifest-based deployment
    - Tarball deployment
    - Migration from v1
    - Troubleshooting guide

27. **Create examples** (`examples/`)
    - Node.js app example
    - Python app example
    - Docker-based example
    - Multi-service example
    - External tarball example
    - Legacy migration example

28. **Update README.md**
    - Add portable deployment section
    - Update command examples
    - Add migration notes
    - Update architecture diagram
    - Add compatibility matrix
    - Add FAQ section

### Phase 10: Error Handling & UX

29. **Enhance error messages** (`spot_deployer/utils/errors.py`)
    - Create custom exception classes
    - Add error codes
    - Provide fix suggestions
    - Add documentation links
    - Support verbose error mode
    - Add error recovery suggestions

30. **Add deployment preview** (`spot_deployer/utils/preview.py`)
    - Show what will be deployed
    - List files to be uploaded
    - Show services to be installed
    - Display estimated deployment time
    - Add cost estimation
    - Support --json output

31. **Implement progress tracking** (`spot_deployer/utils/progress_v2.py`)
    - Track deployment phases
    - Show file upload progress
    - Display service startup status
    - Add time estimates
    - Support quiet mode
    - Add detailed logging

### Phase 11: Advanced Features

32. **Add deployment templates** (`spot_deployer/templates/deployments/`)
    - Create common deployment templates
    - Support template parameters
    - Add template marketplace (future)
    - Support custom templates
    - Add template validation
    - Generate from existing deployments

33. **Implement hooks system** (`spot_deployer/core/hooks.py`)
    - Pre-deployment hooks
    - Post-deployment hooks
    - Error hooks
    - Cleanup hooks
    - Support script and Python hooks
    - Add hook context passing

34. **Add plugin support** (`spot_deployer/plugins/`)
    - Define plugin interface
    - Support custom cloud-init generators
    - Support custom file handlers
    - Add plugin discovery
    - Support plugin configuration
    - Add plugin marketplace (future)

### Phase 12: Performance & Optimization

35. **Optimize file transfers** (`spot_deployer/utils/transfer_optimizer.py`)
    - Implement parallel uploads
    - Add compression for transfers
    - Support incremental updates
    - Add caching layer
    - Optimize large file handling
    - Add bandwidth throttling

36. **Add deployment caching** (`spot_deployer/core/cache.py`)
    - Cache deployment bundles
    - Cache cloud-init scripts
    - Support cache invalidation
    - Add cache size limits
    - Support offline mode
    - Add cache statistics

### Phase 13: Final Integration

37. **Update main entry point** (`spot_deployer/main.py`)
    - Add deployment mode detection
    - Route to appropriate handlers
    - Maintain backward compatibility
    - Add feature flags
    - Support multiple modes simultaneously

38. **Update CLI interface** (`spot_deployer/__main__.py`)
    - Add new commands
    - Update help text
    - Add command aliases
    - Support global flags
    - Add shell completion

39. **Add version management** (`spot_deployer/version_check.py`)
    - Check for updates
    - Show changelog
    - Support version pinning
    - Add compatibility checks
    - Support beta features

40. **Final testing and validation**
    - Run all test suites
    - Test with real projects
    - Validate documentation
    - Check backward compatibility
    - Performance testing
    - Security audit

## Implementation Order

### Priority 1 (Core Functionality)
- Items 1-4: Discovery system
- Items 5-7: Cloud-init generation
- Items 16-18: Command updates

### Priority 2 (Essential Features)
- Items 8-10: File handling
- Items 11-12: Service management
- Items 13-15: Configuration

### Priority 3 (Migration & Compatibility)
- Items 19-21: Legacy support
- Items 26-28: Documentation

### Priority 4 (Quality & Polish)
- Items 22-25: Testing
- Items 29-31: UX improvements
- Items 37-40: Final integration

### Priority 5 (Advanced Features)
- Items 32-34: Templates and plugins
- Items 35-36: Performance optimization

## Success Criteria

1. **Zero Configuration**: User can deploy with just a `deployment/setup.sh` file
2. **Universal Command**: Same command works for all project types
3. **Backward Compatible**: Existing Bacalhau deployments still work
4. **Clear Errors**: Users understand what went wrong and how to fix it
5. **Progressive Enhancement**: Can start simple and add complexity as needed
6. **Well Documented**: Clear examples for common use cases
7. **Extensible**: Easy to add new deployment types via plugins
8. **Performant**: Fast deployment with progress tracking
9. **Reliable**: Robust error handling and recovery
10. **Maintainable**: Clean, modular, testable code

## Migration Strategy

1. **Parallel Development**: Build v2 alongside v1
2. **Feature Flag**: Use --portable flag initially
3. **Gradual Rollout**: Beta -> GA over 2-3 releases
4. **Documentation First**: Document before releasing
5. **Community Feedback**: Get user input during beta
6. **Automated Migration**: Provide tools to convert v1 -> v2
7. **Long Support Window**: Support v1 for 6+ months after v2 GA

## Example Directory Structures

### Minimal Python App
```
my-python-app/
├── .spot/
│   └── config.yaml         # AWS regions only
├── deployment/
│   └── setup.sh           # pip install -r requirements.txt && python app.py
├── requirements.txt
└── app.py
```

### Complex Microservices
```
my-platform/
├── .spot/
│   ├── config.yaml
│   └── deployment.yaml    # Explicit control
├── deployment/
│   ├── scripts/
│   │   ├── install-deps.sh
│   │   └── configure-networking.sh
│   ├── services/
│   │   ├── api.service
│   │   ├── worker.service
│   │   └── monitor.service
│   └── configs/
│       ├── nginx.conf
│       └── prometheus.yml
├── secrets/
│   ├── api-keys.env
│   └── certificates/
└── docker-compose.yml
```

### External Deployment
```
my-app/
└── .spot/
    ├── config.yaml
    └── deployment.yaml

# deployment.yaml:
version: 1
deployment:
  tarball:
    url: "https://releases.myapp.com/latest/deployment.tar.gz"
    checksum: "sha256:..."
    extract_to: "/opt/myapp"
  scripts:
    - "/opt/myapp/install.sh"
```

## Technical Decisions

1. **YAML over JSON**: More human-friendly for manifests
2. **Convention Locations**: `.spot/` for config, `deployment/` for assets
3. **Explicit Manifests**: When conventions aren't enough
4. **Progressive Disclosure**: Simple cases stay simple
5. **Fail Fast**: Validate everything before AWS calls
6. **Idempotent Operations**: Can re-run safely
7. **Atomic Deployments**: All or nothing
8. **Clear Separation**: AWS config vs deployment config

## Future Enhancements (Post-v2)

1. **Multi-cloud Support**: Beyond AWS
2. **Deployment Profiles**: Dev/staging/prod
3. **Blue-green Deployments**: Zero-downtime updates
4. **Secrets Management**: HashiCorp Vault integration
5. **Monitoring Integration**: DataDog, New Relic, etc.
6. **CI/CD Integration**: GitHub Actions, Jenkins
7. **Terraform Integration**: For complex infrastructure
8. **Kubernetes Support**: Deploy to EKS
9. **Cost Optimization**: Spot instance bidding strategies
10. **Compliance Features**: HIPAA, SOC2 helpers

## Notes for Implementation

- Start with the simplest case and build up
- Keep backward compatibility at every step
- Write tests as you go, not after
- Document as you implement, not after
- Get user feedback early and often
- Make the common case fast
- Make the complex case possible
- Error messages should teach, not just inform
- Every feature should have an example
- Performance matters, but correctness matters more
