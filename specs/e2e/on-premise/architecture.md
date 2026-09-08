# Localized Laboratory Platform Architecture

## Administration plane

G1-ONPREM-001 is implemented on a dedicated management VLAN behind an mTLS reverse proxy. A network allowlist and administrator RBAC protect the local control plane, which is reachable through 堡垒机访问.

## Offline update plane

G1-ONPREM-002 uses a detached package signature, a pinned offline trust store, a package checksum, an anti-rollback counter, and an SBOM manifest before installation.

## Directory identity plane

G1-ONPREM-003 uses LDAPS certificate validation, a read-only LDAP bind account, explicit directory group mapping, and scheduled directory synchronization.
