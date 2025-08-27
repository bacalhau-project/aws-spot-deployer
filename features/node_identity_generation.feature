# language: en
Feature: Generate Deterministic Node Identity
  As a sensor node operator
  I want each node to have a unique, deterministic identity
  So that sensor data can be properly attributed and traced

  Background:
    Given I have the generate_node_identity.py script
    And I have access to EC2 instance metadata

  @deterministic
  Scenario: Generate identity based on instance ID
    Given the EC2 instance ID is "i-0a1b2c3d4e5f67890"
    When I run the identity generator with this instance ID
    Then a node identity JSON should be created
    And the node_id should be "sensor-0a1b2c3d"
    And running the generator again should produce identical output
    And the location should be deterministically selected

  @location
  Scenario Outline: Assign US city location
    Given the EC2 instance ID is "<instance_id>"
    When I generate the node identity
    Then the location city should be "<city>"
    And the location state should be "<state>"
    And GPS coordinates should be <lat> and <lon>

    Examples:
      | instance_id          | city        | state | lat     | lon       |
      | i-newyork1234567890  | New York    | NY    | 40.7128 | -74.0060  |
      | i-losang9876543210   | Los Angeles | CA    | 34.0522 | -118.2437 |
      | i-chicago1111111111  | Chicago     | IL    | 41.8781 | -87.6298  |

  @sensor-metadata
  Scenario: Generate sensor manufacturer details
    Given I am generating a node identity
    When the sensor metadata is created
    Then the sensor type should be "environmental"
    And the manufacturer should be one of "Bosch", "Honeywell", or "Siemens"
    And the model should match pattern "ENV-[0-9]{4}"
    And these values should be deterministic per instance

  @fallback
  Scenario: Handle missing instance ID
    Given the INSTANCE_ID environment variable is not set
    When I run the identity generator
    Then it should use "local-dev" as the instance ID
    And generate a valid identity file
    And log a warning about missing instance metadata

  @file-output
  Scenario: Write identity to correct location
    Given I run the identity generator
    When the identity is generated
    Then the file should be written to /opt/sensor/config/node_identity.json
    And the directory should be created if it doesn't exist
    And the file should be valid JSON
    And the file should be readable by the sensor service

  @idempotency
  Scenario: Ensure idempotent generation
    Given an instance with ID "i-test1234567890"
    When I generate the identity 5 times
    Then all 5 generated files should be identical
    And the node_id should always be "sensor-test1234"
    And the location should never change
    And the sensor details should remain constant

  @validation
  Scenario: Validate generated identity format
    Given I have generated a node identity
    When I validate the JSON structure
    Then it should have a "node_id" field of type string
    And it should have a "location" object with city, state, lat, lon
    And it should have a "sensor" object with type, manufacturer, model
    And all coordinates should be valid numbers
    And all string fields should be non-empty
