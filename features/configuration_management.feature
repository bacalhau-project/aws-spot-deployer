# language: en
Feature: Manage Bacalhau and Sensor Configuration
  As a cluster administrator
  I want to manage node configurations centrally
  So that all nodes have consistent settings and credentials

  Background:
    Given I have configuration files in deployment-new/
    And I have the generate_bacalhau_config.py script

  @bacalhau-config
  Scenario: Generate Bacalhau configuration from credentials
    Given I have orchestrator_endpoint file containing "nats://orchestrator.example.com:4222"
    And I have orchestrator_token file containing "secret-token-123"
    When I run generate_bacalhau_config.py
    Then a config.yaml should be created at /etc/bacalhau/config.yaml
    And it should contain the orchestrator endpoint
    And it should contain the orchestrator token
    And it should enable compute mode
    And it should enable Docker engine

  @missing-credentials
  Scenario: Handle missing credential files gracefully
    Given the orchestrator_endpoint file does not exist
    When I run generate_bacalhau_config.py
    Then it should log a warning message
    And it should return a non-zero exit code
    And no config file should be created
    But the script should not crash

  @sensor-config
  Scenario: Deploy sensor configuration
    Given I have a sensor-config.yaml file
    When files are mounted to the node
    Then the config should be at /opt/sensor/config/sensor-config.yaml
    And it should be readable by the sensor container
    And it should contain data export settings
    And it should specify sampling intervals

  @aws-credentials
  Scenario: Configure AWS credentials for S3 access
    Given I have AWS credentials in deployment-new/etc/aws/
    When the node is deployed
    Then credentials should be copied to /root/.aws/credentials
    And permissions should be set to 600
    And they should be mounted into Docker containers
    And S3 operations should authenticate successfully

  @environment-variables
  Scenario: Set environment variables for services
    Given I have environment variables defined in the task
    When services are started
    Then BACALHAU_DISABLEANALYTICS should be "true"
    And LOG_LEVEL should be "info"
    And containers should inherit these variables
    And they should be visible in container logs

  @config-update
  Scenario: Update configuration on running nodes
    Given I have a running cluster
    When I modify the sensor-config.yaml locally
    And I run "sky exec" with file mounts
    Then the new config should be uploaded to all nodes
    And the sensor service should detect the change
    And it should reload without full restart
    And new settings should take effect immediately

  @config-validation
  Scenario: Validate configuration before deployment
    Given I have configuration files ready
    When I run the validation script
    Then it should check YAML syntax
    And verify required fields are present
    And validate credential file formats
    And ensure no sensitive data is exposed
    And report any issues before deployment

  @multi-region
  Scenario Outline: Region-specific configuration
    Given I am deploying to <region>
    When the configuration is generated
    Then the S3 endpoint should use <s3_region>
    And the orchestrator endpoint should remain unchanged
    And region-specific settings should apply

    Examples:
      | region      | s3_region      |
      | us-west-2   | us-west-2      |
      | us-east-1   | us-east-1      |
      | eu-west-1   | eu-west-1      |

  @secrets-management
  Scenario: Secure handling of secrets
    Given I have sensitive credentials
    When they are deployed to nodes
    Then files should have restricted permissions (600)
    And they should not appear in logs
    And they should be excluded from git
    And containers should access them read-only
    And they should be cleaned up on node termination
