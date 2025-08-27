# language: en
Feature: Monitor Cluster Health
  As a cluster operator
  I want to monitor the health of all services
  So that I can detect and resolve issues quickly

  Background:
    Given I have a running Bacalhau cluster
    And I have the health_monitor.py script installed

  @dashboard
  Scenario: Display health dashboard
    When I run "./sky-cli/sky-deploy.py health"
    Then I should see a formatted health dashboard
    And it should show Docker container status
    And it should display CPU usage percentage
    And it should display memory usage
    And it should display disk usage
    And it should show network connections count

  @container-health
  Scenario: Check Docker container health
    When I check container health
    Then all containers should be in "running" state
    And Bacalhau container should pass health checks
    And sensor container should pass health checks
    And containers should have been up for more than 30 seconds
    And restart count should be 0 for healthy containers

  @service-connectivity
  Scenario: Verify service connectivity
    When I test service endpoints
    Then Bacalhau API should respond on port 1234
    And Bacalhau should connect to orchestrator
    And sensor service should be generating data
    And all services should be reachable internally

  @resource-monitoring
  Scenario: Monitor system resources
    When I check system resources
    Then CPU usage should be below 80%
    And memory usage should be below 90%
    And disk usage should be below 85%
    And there should be no zombie processes
    And swap usage should be minimal

  @automated-checks
  Scenario: Schedule recurring health checks
    Given health monitoring is configured
    When the cron job runs every 5 minutes
    Then health status should be written to /var/log/health-check.json
    And metrics should be collected consistently
    And alerts should trigger on failures
    And historical data should be retained for 7 days

  @failure-detection
  Scenario Outline: Detect service failures
    Given the <service> service has failed
    When the health check runs
    Then it should detect the failure
    And report status as "unhealthy"
    And log detailed error information
    And attempt automatic recovery if configured

    Examples:
      | service  |
      | bacalhau |
      | sensor   |
      | docker   |

  @performance-metrics
  Scenario: Collect performance metrics
    When I request performance metrics
    Then I should see container CPU usage
    And container memory consumption
    And network I/O statistics
    And disk I/O statistics
    And job processing metrics from Bacalhau

  @log-aggregation
  Scenario: Aggregate logs from all services
    When I run "./sky-cli/sky-deploy.py logs all"
    Then I should see recent logs from Bacalhau
    And recent logs from sensor service
    And logs should include timestamps
    And error messages should be highlighted
    And logs should be limited to last 50 lines

  @alert-thresholds
  Scenario: Alert on threshold breaches
    Given alert thresholds are configured
    When CPU usage exceeds 90% for 5 minutes
    Then an alert should be triggered
    And the alert should include resource details
    And suggested remediation steps should be provided
    And the alert should be logged

  @cluster-wide-health
  Scenario: Check health across multiple nodes
    Given I have a 3-node cluster
    When I run cluster-wide health check
    Then I should see health status for each node
    And nodes should be able to communicate
    And load should be balanced across nodes
    And no node should be significantly unhealthier than others
