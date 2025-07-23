# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- Distribution method now exclusively uses Docker containers
- Removed PyInstaller and multi-platform binary builds
- Simplified CI/CD pipeline to focus on Docker image releases

## [1.0.0] - 2024-12-21

### Added
- Initial release of spot-deployer
- Support for deploying AWS EC2 spot instances across multiple regions
- Automatic AMI discovery for Ubuntu 22.04
- Cloud-init based instance configuration
- Bacalhau compute node deployment support
- Docker-based deployment option
- Comprehensive instance management (create, list, destroy)
- Real-time deployment progress tracking with Rich UI
- Support for custom VPC creation when default VPC is missing
- Bacalhau node cleanup on instance destruction
- Multi-platform binary builds (Linux, macOS, Windows)

### Features
- Simple YAML-based configuration
- JSON state management for instance tracking
- Automatic SSH key deployment
- File and script upload capabilities
- Rich terminal UI with live updates
- Concurrent instance deployment across regions
- Automatic retry on capacity issues
- Support for multiple instance types
- Environment-based configuration for Docker deployments

### Security
- SSH-based secure file transfers
- Proper AWS credential handling
- Secure Bacalhau token management
