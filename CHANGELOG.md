# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-07-08

### Added

- `vmf` CLI with `discover`, `assess`, `migrate`, and `report` subcommands.
- vSphere discovery client (`VSphereDiscovery`) wrapping pyVmomi, with an
  offline-testable parsing layer that maps raw records to domain models.
- Right-sizing `Assessor` mapping VM specs onto AWS/Azure/GCP instance families
  with monthly cost estimates and 6 Rs dispositions.
- `MigrationOrchestrator` enforcing the discovered -> assessed -> replicating ->
  cutover -> validated -> complete lifecycle.
- pydantic-settings configuration, structured logging, and pydantic domain models.
- Terraform landing-zone scaffold (S3 staging bucket + IAM role module) with
  dev/prod environments.
- Documentation, CI pipeline, pre-commit hooks, and open-source project files.
