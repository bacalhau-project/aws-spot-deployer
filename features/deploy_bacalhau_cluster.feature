# language: en
Feature: Deploy Bacalhau Compute Cluster
  As a DevOps engineer
  I want to deploy Bacalhau compute nodes to AWS spot instances
  So that I can run distributed compute workloads cost-effectively

  Background:
    Given I have AWS credentials configured
    And I have SkyPilot installed with uv
    And I have orchestrator credentials in deployment-new/etc/bacalhau/
    And I have Docker Compose files prepared

  @smoke @critical
  Scenario: Deploy single Bacalhau node
    Given I have a valid SkyPilot task configuration
    When I run "./sky-cli/sky-deploy.py create --nodes 1"
    Then a single AWS spot instance should be created
    And Docker should be installed on the instance
    And Bacalhau container should be running
    And the node should connect to the orchestrator
    And the sensor service should be generating data

  @scaling
  Scenario: Deploy multi-node cluster
    Given I have a valid SkyPilot task configuration
    When I run "./sky-cli/sky-deploy.py create --nodes 3"
    Then 3 AWS spot instances should be created
    And all nodes should have Docker installed
    And all nodes should be running Bacalhau containers
    And all nodes should connect to the orchestrator
    And all nodes should be visible in "bacalhau node list"

  @spot-recovery
  Scenario: Recover from spot instance preemption
    Given I have a running Bacalhau cluster
    When a spot instance is preempted by AWS
    Then SkyPilot should detect the preemption
    And a new spot instance should be launched automatically
    And the new node should be configured with the same settings
    And the cluster should return to full capacity

  @credentials
  Scenario: Deploy without orchestrator credentials
    Given I have no orchestrator credential files
    When I run "./sky-cli/sky-deploy.py create --nodes 1"
    Then the deployment should complete with warnings
    And Bacalhau container should start in standalone mode
    And the sensor service should still generate data
    But the node should not join any orchestrator

  @monitoring
  Scenario: Health monitoring activation
    Given I have a running Bacalhau cluster
    When I run "./sky-cli/sky-deploy.py health"
    Then I should see Docker container status
    And I should see Bacalhau version information
    And I should see system resource usage
    And I should see network connectivity status
    And health checks should be scheduled every 5 minutes

  @cleanup
  Scenario: Destroy cluster completely
    Given I have a running Bacalhau cluster with 3 nodes
    When I run "./sky-cli/sky-deploy.py destroy"
    And I confirm the destruction
    Then all AWS spot instances should be terminated
    And all associated security groups should be deleted
    And all associated volumes should be deleted
    And no resources should remain in AWS

  @file-sync
  Scenario: Update configuration on running cluster
    Given I have a running Bacalhau cluster
    When I modify the sensor configuration locally
    And I run "sky exec bacalhau-cluster --file-mounts"
    Then the new configuration should be synced to all nodes
    And the sensor service should reload with new settings
    And no service interruption should occur

  @cost-optimization
  Scenario Outline: Deploy to cheapest region
    Given I want to deploy <nodes> nodes
    When I run deployment without specifying a region
    Then SkyPilot should scan multiple AWS regions
    And select the region with lowest spot prices
    And deploy all nodes to that region
    And show cost savings compared to on-demand

    Examples:
      | nodes |
      | 1     |
      | 3     |
      | 10    |

  @docker-compose
  Scenario: Validate Docker Compose services
    Given I have deployed a Bacalhau node
    When I SSH into the node
    Then "docker compose ls" should show 2 projects
    And "bacalhau" project should be running
    And "sensor" project should be running
    And both should have restart policies set
    And both should have health checks configured

  @s3-integration
  Scenario: S3 access from containers
    Given I have AWS credentials mounted to nodes
    When the sensor service attempts to upload data
    Then it should authenticate with AWS successfully
    And data should be uploaded to the configured S3 bucket
    And Bacalhau jobs should be able to read from S3
    And proper IAM permissions should be validated
