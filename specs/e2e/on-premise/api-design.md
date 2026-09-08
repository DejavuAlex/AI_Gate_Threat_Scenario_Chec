# Localized Laboratory Platform API Design

## Administration API

The administration API accepts only mTLS-authenticated requests from the management VLAN. MFA establishes an administrator session, and each route enforces fine-grained RBAC.

## Package import API

The import endpoint accepts a package only after detached-signature, checksum, version, anti-rollback, and SBOM validation complete successfully.

## Directory adapter

The adapter requires LDAPS hostname and certificate validation, uses a read-only bind identity, and maps approved directory groups to application roles.
