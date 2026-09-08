# Localized Laboratory Platform Data Model

## AdministratorAuditEvent

- actor directory identifier
- administrator role
- privileged operation
- target configuration
- immutable timestamp and result

## OfflinePackageRecord

- package version and checksum
- signer certificate fingerprint
- anti-rollback counter
- SBOM digest
- validation result

## DirectoryRoleMapping

- directory group identifier
- least-privilege application role
- synchronization timestamp
