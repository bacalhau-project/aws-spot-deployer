# Intent-Driven Development Guide

## Overview

This project follows an Intent-Driven Development (IDD) approach inspired by SpecFlow and Behavior-Driven Development (BDD). We define the system's behavior through feature files before implementing the actual functionality.

## Philosophy

### 1. Start with Intent
Before writing any code, we define **what** the system should do, not **how** it should do it. This is captured in our Gherkin feature files.

### 2. User-Centric Scenarios
Every feature is written from the perspective of a user or stakeholder:
- **DevOps Engineer**: Deploying and managing clusters
- **Cluster Operator**: Monitoring health and performance
- **Sensor Node Operator**: Managing node identities
- **Cluster Administrator**: Managing configurations

### 3. Executable Specifications
Our feature files serve as:
- **Living documentation** of system behavior
- **Acceptance criteria** for implementation
- **Automated tests** to verify functionality
- **Communication tool** between technical and non-technical stakeholders

## Feature File Structure

```gherkin
Feature: [High-level capability]
  As a [role]
  I want [goal/desire]
  So that [benefit/value]

  Background:
    Given [common preconditions]

  @tag
  Scenario: [Specific situation]
    Given [preconditions]
    When [action/trigger]
    Then [expected outcome]
```

## Our Feature Hierarchy

### 1. Core Deployment (`deploy_bacalhau_cluster.feature`)
Primary functionality for deploying Bacalhau compute nodes to cloud infrastructure.

**Key Scenarios:**
- Single node deployment
- Multi-node cluster creation
- Spot instance recovery
- Graceful degradation without credentials

### 2. Identity Management (`node_identity_generation.feature`)
Deterministic identity generation for sensor nodes.

**Key Scenarios:**
- Deterministic ID generation
- Location assignment
- Sensor metadata creation
- Idempotent operations

### 3. Configuration (`configuration_management.feature`)
Central management of node configurations and credentials.

**Key Scenarios:**
- Bacalhau config generation
- Credential handling
- Configuration updates
- Secret management

### 4. Monitoring (`health_monitoring.feature`)
Continuous health monitoring of clusters and services.

**Key Scenarios:**
- Health dashboard display
- Service failure detection
- Performance metrics collection
- Alert threshold management

### 5. Lifecycle (`lifecycle_management.feature`)
Complete cluster lifecycle from creation to destruction.

**Key Scenarios:**
- Initial deployment
- Scaling operations
- Rolling updates
- Disaster recovery

## Implementation Workflow

### Step 1: Define Intent
```bash
# Create a new feature file
cat > features/new_capability.feature << EOF
Feature: New Capability
  As a user role
  I want to achieve something
  So that I get value

  Scenario: Happy path
    Given precondition
    When I perform action
    Then expected result
EOF
```

### Step 2: Generate Step Definitions
```python
#!/usr/bin/env -S uv run -s
# /// script
# dependencies = ["behave"]
# ///

# Run behave to generate missing steps
behave features/new_capability.feature
```

### Step 3: Implement Steps
```python
@given('precondition')
def step_impl(context):
    """Set up the precondition."""
    # Implementation here
    pass

@when('I perform action')
def step_impl(context):
    """Perform the action."""
    # Implementation here
    pass

@then('expected result')
def step_impl(context):
    """Verify the result."""
    # Implementation here
    assert condition, "Explanation"
```

### Step 4: Implement Functionality
Only after steps are defined, implement the actual functionality that makes the tests pass.

## Running Tests

### Run All Features
```bash
#!/usr/bin/env -S uv run -s
# /// script
# dependencies = ["behave", "rich"]
# ///

behave features/
```

### Run Specific Feature
```bash
behave features/deploy_bacalhau_cluster.feature
```

### Run by Tag
```bash
# Critical tests only
behave --tags=@critical

# Exclude slow tests
behave --tags=~@slow

# Smoke tests
behave --tags=@smoke
```

### Generate Reports
```bash
behave -f json -o test-results.json
behave -f junit -o test-results.xml
```

## Tags and Organization

### Priority Tags
- `@critical` - Must-have functionality
- `@important` - Should-have functionality
- `@nice-to-have` - Could-have functionality

### Type Tags
- `@smoke` - Quick validation tests
- `@regression` - Full regression suite
- `@integration` - Integration tests
- `@performance` - Performance tests

### Speed Tags
- `@fast` - < 1 second
- `@slow` - > 10 seconds
- `@very-slow` - > 60 seconds

## Context Management

The `context` object carries state between steps:

```python
# In Given step
context.cluster_name = "test-cluster"
context.node_count = 3

# In When step
context.result = deploy_cluster(context.cluster_name, context.node_count)

# In Then step
assert context.result.success, "Deployment failed"
```

## Best Practices

### 1. Keep Scenarios Independent
Each scenario should be runnable in isolation without depending on other scenarios.

### 2. Use Background Wisely
Only include steps in Background that are truly needed by ALL scenarios.

### 3. Avoid Implementation Details
```gherkin
# Bad - Implementation detail
When I execute "INSERT INTO users VALUES ('John')"

# Good - Business language
When I create a new user "John"
```

### 4. One Assertion Per Then
```gherkin
# Bad - Multiple assertions
Then the user exists AND is active AND has admin role

# Good - Separate assertions
Then the user should exist
And the user should be active
And the user should have admin role
```

### 5. Use Scenario Outlines for Data Variations
```gherkin
Scenario Outline: Deploy to different regions
  Given I want to deploy to <region>
  When I create a cluster
  Then it should be in <region>

  Examples:
    | region    |
    | us-west-2 |
    | us-east-1 |
    | eu-west-1 |
```

## CI/CD Integration

### GitHub Actions Example
```yaml
name: BDD Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Install uv
        run: curl -LsSf https://astral.sh/uv/install.sh | sh

      - name: Run BDD tests
        run: |
          uv run behave features/ \
            --tags=@smoke \
            --format=junit \
            --outfile=test-results.xml

      - name: Upload test results
        uses: actions/upload-artifact@v2
        with:
          name: test-results
          path: test-results.xml
```

## Debugging Features

### Enable Verbose Output
```bash
behave -v features/
```

### Stop on First Failure
```bash
behave --stop features/
```

### Run with Python Debugger
```python
@when('I need to debug')
def step_impl(context):
    import pdb; pdb.set_trace()
    # Debugging session starts here
```

## Feature Coverage Matrix

| Component | Feature File | Scenarios | Steps | Coverage |
|-----------|-------------|-----------|-------|----------|
| Deployment | deploy_bacalhau_cluster.feature | 11 | 45 | 85% |
| Identity | node_identity_generation.feature | 8 | 32 | 90% |
| Config | configuration_management.feature | 10 | 40 | 80% |
| Health | health_monitoring.feature | 11 | 44 | 75% |
| Lifecycle | lifecycle_management.feature | 13 | 52 | 70% |

## Next Steps

1. **Implement missing step definitions** in `features/step_definitions/`
2. **Create test fixtures** for common setup/teardown
3. **Add performance scenarios** for load testing
4. **Create security scenarios** for penetration testing
5. **Build reporting dashboard** for test results

## Resources

- [Behave Documentation](https://behave.readthedocs.io/)
- [Gherkin Reference](https://cucumber.io/docs/gherkin/reference/)
- [SpecFlow Best Practices](https://specflow.org/learn/best-practices/)
- [BDD Guidelines](https://cucumber.io/docs/bdd/)

## Summary

Intent-Driven Development ensures we:
1. **Build the right thing** - Features match user needs
2. **Build it right** - Implementation passes acceptance criteria
3. **Keep it right** - Automated tests prevent regression
4. **Document it right** - Features serve as living documentation

By following this approach, we create a system that is well-tested, well-documented, and aligned with stakeholder expectations.
