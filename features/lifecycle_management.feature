# language: en
Feature: Manage Cluster Lifecycle
  As a DevOps engineer
  I want to manage the complete lifecycle of Bacalhau clusters
  So that I can efficiently deploy, update, and teardown resources

  Background:
    Given I have SkyPilot configured
    And I have the sky-deploy.py CLI tool

  @deployment
  Scenario: Initial cluster deployment
    Given I have no existing cluster
    When I run "./sky-cli/sky-deploy.py create --nodes 3"
    Then SkyPilot should provision 3 spot instances
    And wait for instances to be ready
    And install all dependencies via setup commands
    And start all services via run commands
    And report successful deployment

  @scaling-up
  Scenario: Scale cluster up
    Given I have a 3-node cluster running
    When I update the configuration to 5 nodes
    And I run "./sky-cli/sky-deploy.py update"
    Then 2 additional nodes should be created
    And new nodes should be configured identically
    And they should join the existing cluster
    And total capacity should increase

  @scaling-down
  Scenario: Scale cluster down
    Given I have a 5-node cluster running
    When I update the configuration to 3 nodes
    And I run "./sky-cli/sky-deploy.py update"
    Then 2 nodes should be terminated gracefully
    And workloads should be redistributed
    And remaining nodes should stay healthy
    And cost should decrease

  @rolling-update
  Scenario: Perform rolling update
    Given I have a running cluster
    When I update the Bacalhau version
    And I run "./sky-cli/sky-deploy.py rolling-update"
    Then nodes should be updated one at a time
    And each node should drain before update
    And services should remain available
    And all nodes should run the new version

  @pause-resume
  Scenario: Pause and resume cluster
    Given I have a running cluster
    When I run "./sky-cli/sky-deploy.py pause"
    Then all instances should be stopped
    And persistent data should be preserved
    When I run "./sky-cli/sky-deploy.py resume"
    Then instances should restart
    And services should resume automatically
    And state should be restored

  @backup-restore
  Scenario: Backup and restore cluster state
    Given I have a cluster with data
    When I run "./sky-cli/sky-deploy.py backup"
    Then configuration should be backed up
    And persistent volumes should be snapshotted
    And credentials should be secured
    When I run "./sky-cli/sky-deploy.py restore"
    Then cluster should be recreated from backup
    And data should be intact

  @emergency-shutdown
  Scenario: Emergency cluster shutdown
    Given a critical issue requires immediate shutdown
    When I run "./sky-cli/sky-deploy.py emergency-stop"
    Then all services should stop immediately
    And instances should be terminated
    And resources should be released
    And a report should be generated

  @cost-tracking
  Scenario: Track cluster costs
    Given I have a long-running cluster
    When I run "./sky-cli/sky-deploy.py costs"
    Then I should see hourly spot instance costs
    And data transfer costs
    And storage costs
    And total cost to date
    And projected monthly cost

  @maintenance-window
  Scenario: Schedule maintenance window
    Given I need to perform maintenance
    When I schedule a maintenance window
    Then the cluster should enter maintenance mode
    And new jobs should be queued
    And running jobs should complete
    And maintenance tasks should execute
    And normal operation should resume after

  @disaster-recovery
  Scenario: Recover from disaster
    Given the cluster has catastrophically failed
    When I run "./sky-cli/sky-deploy.py disaster-recovery"
    Then it should detect the failure type
    And attempt automatic recovery
    And restore from last known good state
    And validate cluster health
    And report unrecoverable data loss

  @migration
  Scenario: Migrate to different region
    Given I have a cluster in us-west-2
    When I run "./sky-cli/sky-deploy.py migrate --to us-east-1"
    Then data should be replicated to new region
    And new cluster should be created in us-east-1
    And traffic should be redirected
    And old cluster should be terminated
    And migration should complete without data loss

  @versioning
  Scenario: Manage configuration versions
    Given I have made configuration changes
    When I run "./sky-cli/sky-deploy.py config save --version v2"
    Then configuration should be versioned
    And I should be able to list versions
    And rollback to previous versions
    And diff between versions
    And tag stable versions
